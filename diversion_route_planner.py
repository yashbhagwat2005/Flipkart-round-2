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
  6. One-sentence officer instruction
"""

import pandas as pd
import numpy as np
import networkx as nx
from sklearn.cluster import DBSCAN
import folium
import json
from itertools import islice

# ──────────────────────────────────────────────────────────
# 1.  BENGALURU ROAD NETWORK DEFINITION
# ──────────────────────────────────────────────────────────

NODES = {
    "CBD":             {"lat": 12.9716, "lon": 77.5946, "name": "City Center (MG Road)"},
    "Mekhri_Circle":   {"lat": 13.0053, "lon": 77.5809, "name": "Mekhri Circle"},
    "Hebbal":          {"lat": 13.0356, "lon": 77.5971, "name": "Hebbal Flyover"},
    "Yeshwanthpura":   {"lat": 13.0209, "lon": 77.5503, "name": "Yeshwanthpura Circle"},
    "Jalahalli":       {"lat": 13.0375, "lon": 77.5177, "name": "Jalahalli Cross (SM Circle)"},
    "Kengeri":         {"lat": 12.9063, "lon": 77.4853, "name": "Kengeri"},
    "Vijayanagar":     {"lat": 12.9617, "lon": 77.5213, "name": "Vijayanagar"},
    "Jayanagar":       {"lat": 12.9299, "lon": 77.5826, "name": "Jayanagar"},
    "Silk_Board":      {"lat": 12.9173, "lon": 77.6234, "name": "Silk Board Junction"},
    "Koramangala":     {"lat": 12.9352, "lon": 77.6245, "name": "Koramangala"},
    "KR_Puram":        {"lat": 13.0068, "lon": 77.6938, "name": "KR Puram"},
    "Nagavara":        {"lat": 13.0462, "lon": 77.6173, "name": "Nagavara-ORR Junction"},
    "Yelahanka":       {"lat": 13.1006, "lon": 77.5949, "name": "Yelahanka Circle"},
    "Electronic_City": {"lat": 12.8459, "lon": 77.6601, "name": "Electronic City"},
    "Whitefield":      {"lat": 12.9698, "lon": 77.7500, "name": "Whitefield"},
    "Bannerghatta":    {"lat": 12.8663, "lon": 77.5965, "name": "Bannerghatta Junction"},
}

# (from, to, corridor_name, historical_event_count)
# Added in both directions inside build_graph()
CORRIDOR_EDGES = [
    # Mysore Road — highest density (743 events)
    ("Kengeri",       "Vijayanagar",    "Mysore Road",         743),
    ("Vijayanagar",   "CBD",            "Mysore Road",         743),

    # Magadi Road — parallel to Mysore Road, spillover absorber (245)
    ("Kengeri",       "Jayanagar",      "Magadi Road",         245),
    ("Jayanagar",     "CBD",            "Magadi Road",         245),

    # Bellary Road 1 — CBD to Hebbal (610)
    ("CBD",           "Mekhri_Circle",  "Bellary Road 1",      610),
    ("Mekhri_Circle", "Hebbal",         "Bellary Road 1",      610),

    # Bellary Road 2 — Hebbal northward to airport (379)
    ("Hebbal",        "Yelahanka",      "Bellary Road 2",      379),

    # Tumkur Road — NW corridor (458)
    ("Jalahalli",     "Yeshwanthpura",  "Tumkur Road",         458),
    ("Yeshwanthpura", "CBD",            "Tumkur Road",         458),

    # Hosur Road — SE corridor (298)
    ("CBD",           "Silk_Board",     "Hosur Road",          298),
    ("Silk_Board",    "Electronic_City","Hosur Road",          298),

    # Old Madras Road — East corridor (263)
    ("CBD",           "KR_Puram",       "Old Madras Road",     263),

    # ORR East 1 — Silk Board → KR Puram (244)
    ("Silk_Board",    "Koramangala",    "ORR East 1",          244),
    ("Koramangala",   "KR_Puram",       "ORR East 1",          244),

    # ORR East 2 — KR Puram → Nagavara (187)
    ("KR_Puram",      "Nagavara",       "ORR East 2",          187),

    # ORR North 1 — Nagavara → Hebbal (275)
    ("Nagavara",      "Hebbal",         "ORR North 1",         275),

    # ORR North 2 — Hebbal → Yelahanka via ORR (235)
    ("Hebbal",        "Yelahanka",      "ORR North 2",         235),

    # ORR West 1 — Kengeri → Yeshwanthpura (168)
    ("Kengeri",       "Yeshwanthpura",  "ORR West 1",          168),

    # West of Chord Road — inner west bypass (174)
    ("Yeshwanthpura", "Vijayanagar",    "West of Chord Road",  174),

    # Bannerghatta Road — south corridor (209)
    ("CBD",           "Jayanagar",      "Bannerghatta Road",   209),
    ("Jayanagar",     "Bannerghatta",   "Bannerghatta Road",   209),

    # Hennur Main Road — north connector (96)
    ("Nagavara",      "Yelahanka",      "Hennur Main Road",    96),

    # Varthur Road — east tech corridor (77)
    ("KR_Puram",      "Whitefield",     "Varthur Road",        77),

    # IRR Thanisandra — inner north ring (95)
    ("Nagavara",      "KR_Puram",       "IRR Thanisandra",     95),

    # Connectivity links (approximate inner-city connectors)
    ("Mekhri_Circle", "Yeshwanthpura",  "Inner Ring Road",     150),
    ("Koramangala",   "Jayanagar",      "Inner Ring Road",     100),
    ("Silk_Board",    "Jayanagar",      "Inner Ring Road",     100),
    ("Jalahalli",     "Yeshwanthpura",  "Inner Ring Road",     120),
    ("Hebbal",        "Mekhri_Circle",  "Inner Ring Road",     130),
    ("Nagavara",      "Yeshwanthpura",  "Inner Ring Road",     110),
]

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
# 6.  FOLIUM MAP GENERATION
# ──────────────────────────────────────────────────────────

def generate_map(G, blocked_corridor, primary, secondary, hotspots, output="diversion_map.html"):
    """
    Generate an interactive Folium map with two routing modes:
      - Straight Lines (default, instant): junction-to-junction straight polylines
      - Road Routing (on demand): actual road shapes fetched from OSRM in the browser

    The toggle button in the top-right switches between modes.
    OSRM calls happen client-side (browser), bypassing Python's SSL limitations.
    """
    m = folium.Map(
        location=[12.9716, 77.5946],
        zoom_start=12,
        tiles="CartoDB dark_matter",
    )

    # ── Always-on: background corridors + blocked corridor ────
    drawn = set()
    for u, v, data in G.edges(data=True):
        key = tuple(sorted([u, v])) + (data["corridor"],)
        if key in drawn:
            continue
        drawn.add(key)
        is_blocked = data["corridor"] == blocked_corridor
        pts = [
            [G.nodes[u]["lat"], G.nodes[u]["lon"]],
            [G.nodes[v]["lat"], G.nodes[v]["lon"]],
        ]
        folium.PolyLine(
            pts,
            color="#CC2222" if is_blocked else "#444444",
            weight=6 if is_blocked else 2,
            opacity=0.95 if is_blocked else 0.45,
            tooltip=(f"⛔ BLOCKED: {data['corridor']} ({data['events']} events)"
                     if is_blocked else data["corridor"]),
            dash_array="12" if is_blocked else None,
        ).add_to(m)

    # ── Always-on: DBSCAN hotspot circles ────────────────────
    for h in hotspots:
        radius = max(300, min(h["count"] * 60, 1500))
        folium.Circle(
            location=[h["lat"], h["lon"]],
            radius=radius,
            color="#9933FF",
            fill=True,
            fill_opacity=0.25,
            tooltip=f"🔴 Hotspot #{h['label']}: {h['count']} events — "
                    f"{', '.join(list(h['corridors'])[:2])}",
        ).add_to(m)

    # ── Always-on: junction markers ───────────────────────────
    primary_nodes   = set(primary)
    secondary_nodes = set(secondary)
    for nid, attrs in G.nodes(data=True):
        if nid in primary_nodes:
            color, r = "#00DD55", 7
        elif nid in secondary_nodes:
            color, r = "#FFAA00", 6
        else:
            color, r = "#888888", 4
        folium.CircleMarker(
            location=[attrs["lat"], attrs["lon"]],
            radius=r, color=color, fill=True,
            fill_color=color, fill_opacity=0.9,
            tooltip=attrs["name"],
        ).add_to(m)

    # ── Straight-lines FeatureGroup (shown by default) ────────
    straight_fg = folium.FeatureGroup(name="📏 Straight Lines", show=True)
    if primary:
        folium.PolyLine(
            [[G.nodes[n]["lat"], G.nodes[n]["lon"]] for n in primary],
            color="#00DD55", weight=6, opacity=0.95,
            tooltip="✅ Primary Diversion",
        ).add_to(straight_fg)
    if secondary:
        folium.PolyLine(
            [[G.nodes[n]["lat"], G.nodes[n]["lon"]] for n in secondary],
            color="#FFAA00", weight=5, opacity=0.85,
            dash_array="8", tooltip="⚠️ Secondary Diversion",
        ).add_to(straight_fg)
    straight_fg.add_to(m)

    # ── Grab Folium JS variable names for the toggle script ───
    map_var      = m.get_name()
    straight_var = straight_fg.get_name()

    # ── Waypoint data passed to JS (junction lat/lons) ────────
    primary_wpts   = [[G.nodes[n]["lat"], G.nodes[n]["lon"]] for n in primary]   if primary   else []
    secondary_wpts = [[G.nodes[n]["lat"], G.nodes[n]["lon"]] for n in secondary] if secondary else []

    # ── Embedded JS: OSRM routing + toggle button logic ───────
    road_js = f"""
<script>
(function() {{
  var mapObj      = null;
  var straightLyr = null;
  var roadLyr     = null;
  var isRoadMode  = false;
  var isLoading   = false;

  var primaryWpts   = {json.dumps(primary_wpts)};
  var secondaryWpts = {json.dumps(secondary_wpts)};

  /* ── OSRM public API (called from browser — has proper SSL) ── */
  async function fetchOSRM(lat1, lon1, lat2, lon2) {{
    var url = 'https://router.project-osrm.org/route/v1/driving/'
            + lon1 + ',' + lat1 + ';' + lon2 + ',' + lat2
            + '?overview=full&geometries=geojson';
    try {{
      var resp = await fetch(url);
      var data = await resp.json();
      if (data.code === 'Ok' && data.routes.length > 0) {{
        return data.routes[0].geometry.coordinates.map(function(c) {{
          return [c[1], c[0]];
        }});
      }}
    }} catch(e) {{ console.warn('OSRM failed, using straight line', e); }}
    return [[lat1, lon1], [lat2, lon2]];
  }}

  async function buildRoute(waypoints) {{
    var all = [];
    for (var i = 0; i < waypoints.length - 1; i++) {{
      var seg = await fetchOSRM(
        waypoints[i][0], waypoints[i][1],
        waypoints[i+1][0], waypoints[i+1][1]
      );
      all = all.concat(i === 0 ? seg : seg.slice(1));
    }}
    return all;
  }}

  async function buildRoadLayer() {{
    var btn = document.getElementById('btn-road');
    var status = document.getElementById('road-status');
    btn.textContent = '🔄 Loading...';
    btn.disabled = true;
    if (status) status.textContent = 'Fetching road geometry from OSRM…';

    roadLyr = L.featureGroup();

    if (primaryWpts.length > 1) {{
      var coords = await buildRoute(primaryWpts);
      L.polyline(coords, {{ color:'#00DD55', weight:6, opacity:0.95 }})
       .bindTooltip('✅ Primary Diversion (Road Routing)')
       .addTo(roadLyr);
    }}
    if (secondaryWpts.length > 1) {{
      var coords2 = await buildRoute(secondaryWpts);
      L.polyline(coords2, {{ color:'#FFAA00', weight:5, opacity:0.85, dashArray:'8' }})
       .bindTooltip('⚠️ Secondary Diversion (Road Routing)')
       .addTo(roadLyr);
    }}

    btn.textContent = '🛣️ Roads';
    btn.disabled = false;
    if (status) status.textContent = 'Showing actual road geometry';
  }}

  function setButtonState(mode) {{
    var btnS = document.getElementById('btn-straight');
    var btnR = document.getElementById('btn-road');
    var status = document.getElementById('road-status');
    if (mode === 'straight') {{
      btnS.style.background='#3b82f6'; btnS.style.color='#fff';
      btnR.style.background='#1f2937'; btnR.style.color='#9ca3af';
      if (status) status.textContent = 'Click 🛣️ to load road routing';
    }} else {{
      btnR.style.background='#3b82f6'; btnR.style.color='#fff';
      btnS.style.background='#1f2937'; btnS.style.color='#9ca3af';
    }}
  }}

  window.showRoad = async function() {{
    if (isRoadMode || isLoading) return;
    isRoadMode = true; isLoading = true;
    setButtonState('road');
    mapObj.removeLayer(straightLyr);
    if (!roadLyr) await buildRoadLayer();
    mapObj.addLayer(roadLyr);
    isLoading = false;
  }};

  window.showStraight = function() {{
    if (!isRoadMode) return;
    isRoadMode = false;
    setButtonState('straight');
    if (roadLyr) mapObj.removeLayer(roadLyr);
    mapObj.addLayer(straightLyr);
  }};

  /* Resolve Folium's generated variables after page loads */
  document.addEventListener('DOMContentLoaded', function() {{
    setTimeout(function() {{
      mapObj      = window.{map_var};
      straightLyr = window.{straight_var};
    }}, 300);
  }});
}})();
</script>

<div style="
    position:fixed; top:20px; right:60px; z-index:9999;
    background:#111827; border:1px solid #374151; border-radius:10px;
    padding:10px 14px; font-family:'Segoe UI',Arial; color:#f9fafb;
    box-shadow:0 4px 16px rgba(0,0,0,0.6); min-width:170px;">
  <div style="font-size:10px; color:#6b7280; text-transform:uppercase;
              letter-spacing:1.5px; margin-bottom:8px; font-weight:700;">
    Routing View
  </div>
  <div style="display:flex; border-radius:7px; overflow:hidden; border:1px solid #374151;">
    <button id="btn-straight" onclick="showStraight()" style="
        flex:1; padding:8px 0; background:#3b82f6; color:#fff; border:none;
        cursor:pointer; font-size:12px; font-weight:700; transition:all .2s;">
      📏 Straight
    </button>
    <button id="btn-road" onclick="showRoad()" style="
        flex:1; padding:8px 0; background:#1f2937; color:#9ca3af; border:none;
        cursor:pointer; font-size:12px; font-weight:700; transition:all .2s;">
      🛣️ Roads
    </button>
  </div>
  <div id="road-status" style="font-size:10px; color:#6b7280; margin-top:6px; text-align:center;">
    Click 🛣️ to load road routing
  </div>
</div>

<div style="
    position:fixed; bottom:28px; left:28px; z-index:9999;
    background:#111827; padding:14px 18px; border-radius:10px;
    border:1px solid #374151; color:#F9FAFB;
    font-family:'Segoe UI',Arial,sans-serif; font-size:13px; line-height:1.9;
    box-shadow:0 4px 12px rgba(0,0,0,0.5);">
  <b style="font-size:14px; letter-spacing:.5px;">BENGALURU TRAFFIC DIVERSION</b><br>
  <span style="color:#CC2222;">━━</span>&nbsp; Blocked Corridor<br>
  <span style="color:#00DD55;">━━</span>&nbsp; Primary Diversion<br>
  <span style="color:#FFAA00;">╌╌</span>&nbsp; Secondary Diversion<br>
  <span style="color:#9933FF;">●</span>&nbsp; Live Congestion Hotspot<br>
  <span style="color:#444444;">━━</span>&nbsp; Background Roads
</div>
"""
    m.get_root().html.add_child(folium.Element(road_js))
    m.save(output)
    return output


# ──────────────────────────────────────────────────────────
# 7.  MAIN DEMO
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

        # Save map for each scenario
        map_file = f"diversion_map_s{i}.html"
        generate_map(G, s["blocked"], primary, secondary, hotspots, map_file)
        print(f"\n  🗺  Map saved → {map_file}")

    print(f"\n{banner}")
    print("  Done.  Open diversion_map_s*.html in a browser to view maps.")
    print(f"{banner}\n")


if __name__ == "__main__":
    main()
