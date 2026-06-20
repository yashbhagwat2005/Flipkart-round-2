from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from graph_config import CORRIDOR_EDGES

_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# CORRIDOR_MULT — officer count multiplier per corridor, derived from the
# historical event counts in CORRIDOR_EDGES.  Formula: 1.0 + 0.5 * (events /
# max_events), giving 1.0 (quietest corridor) → 1.5 (busiest corridor).
# Every corridor in the routing graph gets a sensible value automatically;
# unknown corridors still fall back to 1.0 in compute_officers().
#
# "CBD 2" was in the old hardcoded dict but does not exist in CORRIDOR_EDGES
# (it is a dataset-only corridor name with no corresponding routing graph
# entry).  It is intentionally omitted here.
# ---------------------------------------------------------------------------
def _build_corridor_mult() -> dict:
    max_events = max(events for *_, events in CORRIDOR_EDGES)
    seen: dict[str, int] = {}
    for _u, _v, corridor, events in CORRIDOR_EDGES:
        # keep max event count if a corridor spans multiple edges
        if events > seen.get(corridor, 0):
            seen[corridor] = events
    return {
        corridor: round(1.0 + 0.5 * (events / max_events), 2)
        for corridor, events in seen.items()
    }

CORRIDOR_MULT: dict[str, float] = _build_corridor_mult()

CAUSE_BONUS = {
    "vip_movement": 4,
    "procession": 3,
    "public_event": 3,
    "protest": 2,
}

# ---------------------------------------------------------------------------
# CLOSURE_RATE — base probability of road closure per event_cause, derived
# from the dataset.  Populated at server startup via init_manpower_data(df).
# A sensible default is provided so tests and imports work without the CSV.
# ---------------------------------------------------------------------------
CLOSURE_RATE: dict[str, float] = {
    "vip_movement": 0.800,
    "public_event": 0.464,
    "protest": 0.400,
    "tree_fall": 0.394,
    "construction": 0.265,
    "procession": 0.264,
}


def init_manpower_data(df: pd.DataFrame) -> None:
    """
    Compute data-driven CLOSURE_RATE from the events dataframe and update the
    module-level dict in place.  Call once at server startup after loading the
    dataset.  Covers every event_cause with ≥5 events; rarer causes keep the
    module default of 0.08 (used in the heuristic fallback only).
    """
    global CLOSURE_RATE
    closure_bool = (
        df["requires_road_closure"].astype(str).str.lower() == "true"
    ).astype(int)
    cause_col = df["event_cause"].fillna("others").str.lower().str.strip()
    rates = (
        pd.DataFrame({"cause": cause_col, "closure": closure_bool})
        .groupby("cause")["closure"]
        .agg(["mean", "count"])
    )
    CLOSURE_RATE = {
        row.Index: round(float(row.mean), 3)
        for row in rates.itertuples()
        if row.count >= 5
    }

# Load trained barricade classifier (logistic regression on event_cause + severity_score).
# Falls back gracefully to the heuristic if the file is missing.
_BARRICADE_PIPELINE = None
try:
    _BARRICADE_PIPELINE = joblib.load(_ROOT / "barricade_pipeline.pkl")
except Exception:
    pass


def build_station_coords(df: pd.DataFrame) -> dict:
    """Derive every station's coordinates as the mean of its event coordinates."""
    coords = (
        df.dropna(subset=["police_station", "latitude", "longitude"])
        .groupby("police_station")[["latitude", "longitude"]]
        .mean()
    )
    return {s: (r.latitude, r.longitude) for s, r in coords.iterrows()}


def primary_station_per_corridor(df: pd.DataFrame) -> dict:
    valid = df.dropna(subset=["corridor", "police_station"])
    counts = (
        valid.groupby(["corridor", "police_station"]).size().reset_index(name="n")
    )
    if counts.empty:
        return {}
    idx = counts.groupby("corridor")["n"].idxmax()
    return dict(zip(counts.loc[idx, "corridor"], counts.loc[idx, "police_station"]))


def compute_officers(
    severity_score: int, corridor: str, crowd_size: int, event_cause: str
) -> int:
    base = 2 if severity_score < 40 else 6 if severity_score < 70 else 12
    corridor_multiplier = CORRIDOR_MULT.get(corridor, 1.0)
    crowd_bonus = max(0, crowd_size) // 10000
    cause_add = CAUSE_BONUS.get(event_cause, 0)
    return int(base * corridor_multiplier) + crowd_bonus + cause_add


def _barricade_locations(blocked_corridor, nodes_dict, severity_score) -> list:
    """
    Compute concrete lat/lon placements for barricade points.

    Rules:
    - Always place at the two distinct endpoint nodes that bound the blocked corridor.
    - At severity ≥70 (High/Critical), also find the nearest node that is NOT an
      endpoint of the blocked corridor (a cross-street approach point).
    Returns a list of {lat, lon, description} dicts.
    """
    if not blocked_corridor or not nodes_dict:
        return []

    from graph_config import CORRIDOR_EDGES

    # Collect all (u, v) node pairs that belong to the blocked corridor
    endpoint_ids: set = set()
    for u, v, corridor, _ in CORRIDOR_EDGES:
        if corridor == blocked_corridor:
            endpoint_ids.add(u)
            endpoint_ids.add(v)

    locations = []
    for nid in sorted(endpoint_ids):
        node = nodes_dict.get(nid)
        if node:
            locations.append({
                "lat": node["lat"],
                "lon": node["lon"],
                "description": f"Barricade at {node.get('name', nid)} (corridor endpoint)",
            })

    if severity_score >= 70 and locations:
        # Find the nearest non-endpoint node as a cross-street approach point
        ref_lat = sum(loc["lat"] for loc in locations) / len(locations)
        ref_lon = sum(loc["lon"] for loc in locations) / len(locations)
        best_node, best_dist = None, float("inf")
        for nid, node in nodes_dict.items():
            if nid in endpoint_ids:
                continue
            d = ((node["lat"] - ref_lat) ** 2 + (node["lon"] - ref_lon) ** 2) ** 0.5
            if d < best_dist:
                best_dist = d
                best_node = (nid, node)
        if best_node:
            nid, node = best_node
            locations.append({
                "lat": node["lat"],
                "lon": node["lon"],
                "description": f"Approach control at {node.get('name', nid)} (cross-street)",
            })

    return locations


def predict_barricade(
    event_cause: str,
    severity_score: int,
    blocked_corridor: Optional[str] = None,
    nodes_dict: Optional[dict] = None,
) -> dict:
    """
    Predict whether road closure / barricades are needed.

    Uses a trained logistic regression (event_cause + severity_score) when the
    barricade_pipeline.pkl is available.  Falls back to the hand-tuned heuristic
    if the model file is missing, so the server always starts.

    Optional blocked_corridor + nodes_dict enable concrete lat/lon barricade
    placement (added to the response as barricade_locations).
    """
    confidence = None
    if _BARRICADE_PIPELINE is not None:
        try:
            row = pd.DataFrame([{
                "event_cause": (event_cause or "others").lower().strip(),
                "severity_score": int(severity_score),
            }])
            confidence = float(_BARRICADE_PIPELINE.predict_proba(row)[0, 1])
        except Exception:
            pass  # pkl trained on newer sklearn — fall through to heuristic

    if confidence is None:
        base_rate = CLOSURE_RATE.get(event_cause, 0.08)
        confidence = min(0.97, base_rate + (severity_score / 100) * 0.2)

    needed = confidence >= 0.4
    points = 1 if not needed else (2 if severity_score < 70 else 3)
    locations = (
        _barricade_locations(blocked_corridor, nodes_dict, severity_score)
        if needed and blocked_corridor
        else []
    )
    return {
        "barricade_needed": needed,
        "barricade_confidence": round(confidence, 2),
        "estimated_barricade_points": points,
        "barricade_locations": locations,
    }


def recommend_stations(
    junction_lat,
    junction_lon,
    station_coords,
    primary_station,
    active_load,
    haversine_fn,
    top_n=2,
):
    candidates = []
    for name, (lat, lon) in station_coords.items():
        dist = haversine_fn(junction_lat, junction_lon, lat, lon)
        if dist <= 15:
            candidates.append(
                {
                    "name": name,
                    "lat": round(lat, 6),
                    "lon": round(lon, 6),
                    "distance_km": round(dist, 1),
                    "current_load": active_load.get(name, 0),
                    "is_primary": name == primary_station,
                }
            )
    candidates.sort(
        key=lambda station: (
            station["current_load"],
            station["distance_km"],
            not station["is_primary"],
        )
    )
    return candidates[:top_n]
