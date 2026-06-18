#!/usr/bin/env python3
"""
Diversion Route Planner with Cascade Awareness
Bengaluru Traffic Management — ASTRAM Dataset

Pipeline:
  1. Load ASTRAM events → compute per-corridor event density
  2. DBSCAN on recent events → identify live congestion hotspots
  3. Weighted corridor graph → edge weight = distance × (1 + density_factor)
  4. Yen's k-shortest paths, filtered by cascade-awareness check
  5. Folium map → red (blocked), green (primary), amber (secondary)
  5. One-sentence officer instruction
"""

import pandas as pd
import numpy as np
import networkx as nx
from sklearn.cluster import DBSCAN
from itertools import islice

# ──────────────────────────────────────────────────────────
# 1.  BENGALURU ROAD NETWORK DEFINITION
# ──────────────────────────────────────────────────────────

from graph_config import NODES, CORRIDOR_EDGES

# ──────────────────────────────────────────────────────────
# 2.  GRAPH CONSTRUCTION
# ──────────────────────────────────────────────────────────

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def build_graph():
    """
    Build bidirectional weighted corridor graph.
    Edge weight = distance_km × (1 + normalized_event_density)
    Higher density → heavier edge → Dijkstra naturally prefers cleaner roads.
    """
    G = nx.MultiDiGraph()

    for node_id, attrs in NODES.items():
        G.add_node(node_id, **attrs)

    max_events = max(e[3] for e in CORRIDOR_EDGES)

    for (u, v, corridor, events) in CORRIDOR_EDGES:
        dist = haversine_km(NODES[u]["lat"], NODES[u]["lon"], NODES[v]["lat"], NODES[v]["lon"])
        density_factor = events / max_events
        weight = dist * (1.0 + density_factor)

        attrs = dict(corridor=corridor, events=events, distance_km=dist, weight=weight)
        G.add_edge(u, v, **attrs)
        G.add_edge(v, u, **attrs)

    return G


# ──────────────────────────────────────────────────────────
# 3.  DBSCAN HOTSPOT DETECTION
# ──────────────────────────────────────────────────────────

def cluster_hotspots(df, eps_km=0.8, min_samples=4):
    """
    Run DBSCAN on event coordinates to find live congestion clusters.

    eps_km controls the neighbourhood radius (~800m default).
    Returns a list of dicts: {lat, lon, count, corridors, label}
    """
    coords = df[["latitude", "longitude"]].dropna().values
    if len(coords) < min_samples:
        return []

    # Sample if very large for speed
    if len(coords) > 3000:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(coords), 3000, replace=False)
        coords_sample = coords[idx]
        df_sample = df.iloc[idx]
    else:
        coords_sample = coords
        df_sample = df

    eps_rad = eps_km / 6371.0
    labels = DBSCAN(
        eps=eps_rad, min_samples=min_samples,
        algorithm="ball_tree", metric="haversine"
    ).fit_predict(np.radians(coords_sample))

    hotspots = []
    for label in set(labels):
        if label == -1:
            continue
        mask = labels == label
        cluster_coords = coords_sample[mask]
        cluster_df = df_sample.iloc[np.where(mask)[0]]

        hotspots.append({
            "label": int(label),
            "lat": float(cluster_coords[:, 0].mean()),
            "lon": float(cluster_coords[:, 1].mean()),
            "count": int(mask.sum()),
            "corridors": set(cluster_df["corridor"].dropna().unique()),
        })

    return sorted(hotspots, key=lambda h: -h["count"])


# ──────────────────────────────────────────────────────────
# 4.  CASCADE-AWARE DIVERSION ROUTING
# ──────────────────────────────────────────────────────────

def _path_in_hotspot(G, path, hotspots, radius_km=1.2, density_thresh=8):
    """
    Returns True if any node in `path` sits inside a significant hotspot.
    A hotspot is significant if it has ≥ density_thresh events.
    """
    for node in path:
        nlat = G.nodes[node]["lat"]
        nlon = G.nodes[node]["lon"]
        for h in hotspots:
            if h["count"] >= density_thresh:
                if haversine_km(nlat, nlon, h["lat"], h["lon"]) < radius_km:
                    return True
    return False


def _path_weight(G, path):
    """Sum of minimum-weight edges along path in MultiDiGraph."""
    total = 0.0
    for u, v in zip(path, path[1:]):
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            # pick min-weight key among parallel edges
            min_w = min(d["weight"] for d in edge_data.values())
            total += min_w
    return total


def find_diversion_routes(G, blocked_corridor, origin, destination, hotspots, k=8):
    """
    Return (primary_path, secondary_path) avoiding `blocked_corridor`
    and cascade-overloaded segments.

    Uses Yen's algorithm (networkx.shortest_simple_paths) on a simple
    projection of the MultiDiGraph (keeping min-weight edge per pair).
    """
    # Project to simple DiGraph using minimum edge weight per (u,v)
    simple = nx.DiGraph()
    for node, data in G.nodes(data=True):
        simple.add_node(node, **data)
    for u, v, data in G.edges(data=True):
        if data.get("corridor") == blocked_corridor:
            continue  # remove blocked corridor entirely
        existing = simple.get_edge_data(u, v)
        if existing is None or data["weight"] < existing["weight"]:
            simple.add_edge(u, v, **data)

    if not nx.has_path(simple.to_undirected(), origin, destination):
        print(f"  [!] No path exists from {origin} to {destination} after blocking {blocked_corridor}")
        return [], []

    try:
        candidates = list(islice(
            nx.shortest_simple_paths(simple, origin, destination, weight="weight"),
            k * 3,
        ))
    except nx.NetworkXNoPath:
        return [], []

    # Apply cascade awareness filter
    valid, rejected = [], []
    for path in candidates:
        if _path_in_hotspot(G, path, hotspots):
            rejected.append(path)
        else:
            valid.append(path)
        if len(valid) >= 2:
            break

    if len(valid) < 2:
        valid += rejected[: 2 - len(valid)]

    primary   = valid[0] if len(valid) > 0 else []
    secondary = valid[1] if len(valid) > 1 else []
    return primary, secondary


# ──────────────────────────────────────────────────────────
# 5.  UTILITIES
# ──────────────────────────────────────────────────────────

def path_corridors(G, path, exclude_corridor=None):
    """
    Return ordered list of corridor names used in a path (deduplicated).
    For parallel edges, picks the minimum-weight corridor that is not excluded
    (so the blocked corridor never appears in a diversion report).
    """
    seen, corridors = set(), []
    for u, v in zip(path, path[1:]):
        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            continue
        candidates = [
            d for d in edge_data.values()
            if d.get("corridor") != exclude_corridor
        ]
        if not candidates:
            candidates = list(edge_data.values())
        best = min(candidates, key=lambda d: d["weight"])
        c = best["corridor"]
        if c not in seen:
            seen.add(c)
            corridors.append(c)
    return corridors


def officer_instruction(G, blocked, origin, destination, primary):
    """One-sentence routing instruction for field officers."""
    if not primary:
        return f"No clear diversion for {blocked} — deploy manual traffic control at all access points."
    via = " → ".join(path_corridors(G, primary, exclude_corridor=blocked))
    src = G.nodes[origin]["name"]
    dst = G.nodes[destination]["name"]
    return f"Divert {blocked} traffic via {via} from {src} to {dst}."


def path_summary(G, path):
    dist = sum(
        min(d["distance_km"] for d in G.get_edge_data(u, v).values())
        for u, v in zip(path, path[1:])
        if G.get_edge_data(u, v)
    )
    return f"{' → '.join(path)}  [{dist:.1f} km]"


# ──────────────────────────────────────────────────────────
# 6.  MAIN DEMO
# ──────────────────────────────────────────────────────────

SCENARIOS = [
    {
        "desc":    "Major vehicle breakdown on Mysore Road → route CBD-bound traffic",
        "blocked": "Mysore Road",
        "origin":  "Kengeri",
        "dest":    "CBD",
    },
    {
        "desc":    "VIP movement on Bellary Road 1 → divert to Hebbal",
        "blocked": "Bellary Road 1",
        "origin":  "CBD",
        "dest":    "Hebbal",
    },
    {
        "desc":    "Public procession on ORR East 1 → alternate Silk Board → KR Puram",
        "blocked": "ORR East 1",
        "origin":  "Silk_Board",
        "dest":    "KR_Puram",
    },
]


def main():
    banner = "=" * 62
    print(f"\n{banner}")
    print("  BENGALURU DIVERSION ROUTE PLANNER  (Cascade-Aware)")
    print(f"{banner}\n")

    # ── Load ASTRAM data ──────────────────────────────────────
    data_file = "Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"
    print("Loading ASTRAM dataset...")
    df = pd.read_csv(data_file, low_memory=False)
    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["corridor"]  = df["corridor"].fillna("Non-corridor")
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[(df["latitude"] > 12.7) & (df["latitude"] < 13.2)
          & (df["longitude"] > 77.3) & (df["longitude"] < 77.9)]
    print(f"  {len(df):,} events loaded (within Bengaluru bounds)\n")

    # ── Build graph ───────────────────────────────────────────
    print("Building Bengaluru corridor graph...")
    G = build_graph()
    print(f"  {G.number_of_nodes()} junctions  |  {G.number_of_edges()} directed edges\n")

    # ── DBSCAN hotspot detection ──────────────────────────────
    print("Running DBSCAN to identify live congestion hotspots...")
    hotspots = cluster_hotspots(df, eps_km=0.8, min_samples=4)
    print(f"  {len(hotspots)} clusters detected")
    for h in hotspots[:5]:
        top_corr = list(h["corridors"])[:2]
        print(f"  • Cluster {h['label']:2d}: {h['count']:3d} events  "
              f"({h['lat']:.4f}, {h['lon']:.4f})  corridors: {top_corr}")

    # ── Run each scenario ─────────────────────────────────────
    for i, s in enumerate(SCENARIOS, 1):
        print(f"\n{'─'*62}")
        print(f"SCENARIO {i}: {s['desc']}")
        print(f"  Blocked : {s['blocked']}")
        print(f"  Route   : {s['origin']} → {s['dest']}")

        primary, secondary = find_diversion_routes(
            G, s["blocked"], s["origin"], s["dest"], hotspots
        )

        if primary:
            print(f"\n  PRIMARY   : {path_summary(G, primary)}")
            print(f"  Via       : {' → '.join(path_corridors(G, primary, exclude_corridor=s['blocked']))}")
        else:
            print("  PRIMARY   : ⚠️  No viable route found")

        if secondary:
            print(f"  SECONDARY : {path_summary(G, secondary)}")
            print(f"  Via       : {' → '.join(path_corridors(G, secondary, exclude_corridor=s['blocked']))}")

        instr = officer_instruction(G, s["blocked"], s["origin"], s["dest"], primary)
        print(f"\n  📢 OFFICER INSTRUCTION:\n     {instr}")

    print(f"\n{banner}")
    print("  Done.  Simulation complete.")
    print(f"{banner}\n")


if __name__ == "__main__":
    main()
