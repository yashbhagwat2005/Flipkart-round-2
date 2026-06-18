import pandas as pd


CORRIDOR_MULT = {
    "Mysore Road": 1.4,
    "Bellary Road 1": 1.3,
    "Tumkur Road": 1.2,
    "CBD 2": 1.5,
    "ORR East 1": 1.2,
    "Hosur Road": 1.2,
}
CAUSE_BONUS = {
    "vip_movement": 4,
    "procession": 3,
    "public_event": 3,
    "protest": 2,
}
CLOSURE_RATE = {
    "vip_movement": 0.80,
    "public_event": 0.464,
    "protest": 0.40,
    "tree_fall": 0.394,
    "construction": 0.265,
    "procession": 0.264,
}


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


def predict_barricade(event_cause: str, severity_score: int) -> dict:
    base_rate = CLOSURE_RATE.get(event_cause, 0.08)
    confidence = min(0.97, base_rate + (severity_score / 100) * 0.2)
    needed = confidence >= 0.4
    points = 1 if not needed else (2 if severity_score < 70 else 3)
    return {
        "barricade_needed": needed,
        "barricade_confidence": round(confidence, 2),
        "estimated_barricade_points": points,
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
