import joblib
import numpy as np
import pandas as pd

from config import CBD_LAT, CBD_LON


PIPELINE = joblib.load("best_congestion_pipeline.pkl")
SCORE_CAP_MIN = 600


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dlmb = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def minutes_to_score(predicted_min: float) -> int:
    score = 100 * (1 - np.exp(-predicted_min / (SCORE_CAP_MIN / 3)))
    return int(np.clip(round(score), 0, 100))


def score_to_label(score: int) -> str:
    return "Low" if score < 35 else "Medium" if score < 70 else "High"


def predict_severity(payload: dict) -> dict:
    hour, dow = payload["hour"], payload["dow"]
    row = pd.DataFrame(
        [
            {
                "event_cause": payload.get("event_cause", "others"),
                "corridor": payload.get("corridor", "Non-corridor"),
                "zone": payload.get("zone", "Unknown"),
                "priority": payload.get("priority", "Low"),
                "requires_road_closure_bool": int(
                    payload.get("requires_road_closure_bool", 0)
                ),
                "hour_sin": np.sin(2 * np.pi * hour / 24),
                "hour_cos": np.cos(2 * np.pi * hour / 24),
                "dow_sin": np.sin(2 * np.pi * dow / 7),
                "dow_cos": np.cos(2 * np.pi * dow / 7),
                "is_weekend": int(dow in (5, 6)),
                "latitude": payload["latitude"],
                "longitude": payload["longitude"],
                "distance_to_cbd": _haversine(
                    payload["latitude"], payload["longitude"], CBD_LAT, CBD_LON
                ),
            }
        ]
    )
    predicted_min = max(0.0, float(PIPELINE.predict(row)[0]))
    score = minutes_to_score(predicted_min)
    return {
        "predicted_closure_min": round(predicted_min, 1),
        "severity_score": score,
        "severity_label": score_to_label(score),
        "requires_diversion": score >= 40,
    }
