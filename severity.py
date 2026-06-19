import json
import joblib
import numpy as np
import pandas as pd

from config import CBD_LAT, CBD_LON


PIPELINE = joblib.load("best_congestion_pipeline.pkl")
SCORE_CAP_MIN = 600

try:
    with open("density_mappings.json", "r") as f:
        DENSITY_MAPPINGS = json.load(f)
except Exception:
    DENSITY_MAPPINGS = {"corridor": {}, "zone": {}}


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
    return "Low" if score < 35 else "Medium" if score < 70 else "High" if score < 90 else "Critical"


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
                "historical_corridor_density": DENSITY_MAPPINGS["corridor"].get(payload.get("corridor", ""), 0),
                "historical_zone_density": DENSITY_MAPPINGS["zone"].get(payload.get("zone", ""), 0),
            }
        ]
    )
    predicted_min = max(0.0, float(PIPELINE.predict(row)[0]))
    
    # Calculate confidence score
    confidence = "Medium"
    try:
        model = PIPELINE.named_steps['model'].regressor_
        if hasattr(model, 'estimators_'):
            # Random Forest
            X_transformed = PIPELINE.named_steps['preprocessor'].transform(row)
            preds = np.array([tree.predict(X_transformed) for tree in model.estimators_])
            preds = np.expm1(preds)
            std = np.std(preds, axis=0)[0]
            mean = np.mean(preds, axis=0)[0]
            cov = std / mean if mean > 0 else 0
            if cov < 0.35: confidence = "High"
            elif cov < 0.7: confidence = "Medium"
            else: confidence = "Low"
    except Exception:
        pass
    score = minutes_to_score(predicted_min)
    return {
        "predicted_closure_min": round(predicted_min, 1),
        "severity_score": score,
        "severity_label": score_to_label(score),
        "requires_diversion": score >= 40,
        "confidence": confidence,
    }
