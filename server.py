import json
import subprocess
import sys
from pathlib import Path

import joblib
import networkx as nx
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import severity as severity_module
from config import DATA_FILE
from diversion_route_planner import (
    SCENARIOS,
    build_graph,
    cluster_hotspots,
    find_diversion_routes,
    haversine_km,
    officer_instruction,
    run_diversion,
)
from graph_config import CORRIDOR_EDGES, NODES
from manpower import (
    build_station_coords,
    compute_officers,
    predict_barricade,
    primary_station_per_corridor,
    recommend_stations,
)


ROOT = Path(__file__).resolve().parent
FEATURE_COLS = [
    "event_cause",
    "corridor",
    "zone",
    "priority",
    "requires_road_closure_bool",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "is_weekend",
    "latitude",
    "longitude",
    "distance_to_cbd",
]

app = FastAPI(title="ASTRAM Traffic Manager API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.active_load = {}


def _load_model_metadata():
    metadata_path = ROOT / "model_metadata.json"
    if not metadata_path.exists():
        return {}
    with metadata_path.open(encoding="utf-8") as metadata_file:
        return json.load(metadata_file)


def _prepare_data():
    raw = pd.read_csv(ROOT / DATA_FILE, low_memory=False)
    raw["latitude"] = pd.to_numeric(raw["latitude"], errors="coerce")
    raw["longitude"] = pd.to_numeric(raw["longitude"], errors="coerce")
    raw["corridor"] = raw["corridor"].fillna("Non-corridor")
    raw["event_cause"] = raw["event_cause"].fillna("others")
    raw["start_datetime"] = pd.to_datetime(
        raw["start_datetime"], errors="coerce", format="mixed"
    )
    raw["closed_datetime"] = pd.to_datetime(
        raw["closed_datetime"], errors="coerce", format="mixed"
    )
    raw["closure_min"] = (
        raw["closed_datetime"] - raw["start_datetime"]
    ).dt.total_seconds() / 60

    geo = raw.dropna(subset=["latitude", "longitude"]).copy()
    geo = geo[
        (geo["latitude"] > 12.7)
        & (geo["latitude"] < 13.2)
        & (geo["longitude"] > 77.3)
        & (geo["longitude"] < 77.9)
    ]

    engineered = pd.read_csv(ROOT / "engineered_features.csv")
    engineered = engineered.dropna(subset=FEATURE_COLS + ["closure_min"]).copy()
    return raw, geo, engineered


def _build_learning_cache():
    overview = {
        "total_events": int(len(df_full)),
        "closed_events": int(df_full["closed_datetime"].notna().sum()),
        "avg_resolution_min": round(float(df_closed["closure_min"].mean()), 1),
        "high_severity_events": int((df_closed["closure_min"] > 300).sum()),
    }

    predictions = PIPELINE.predict(df_closed[FEATURE_COLS])
    error_frame = df_closed.assign(
        error_min=df_closed["closure_min"].values - predictions
    )
    grouped = error_frame.groupby("corridor")["error_min"].mean().sort_values()
    error_cache = {
        "corridors": grouped.index.tolist(),
        "mean_error_min": grouped.round(1).tolist(),
    }

    cause_stats = (
        df_full.groupby("event_cause", dropna=False)["closure_min"]
        .agg(["median", "count"])
        .reset_index()
    )
    cause_stats = cause_stats[cause_stats["count"] >= 10]
    cause_stats["median"] = cause_stats["median"].round(1)
    cause_cache = cause_stats.replace({np.nan: None}).to_dict(orient="records")

    time_frame = df_full.dropna(subset=["start_datetime"]).copy()
    time_frame["hour"] = time_frame["start_datetime"].dt.hour
    time_frame["dow"] = time_frame["start_datetime"].dt.dayofweek
    pivot = (
        time_frame.groupby(["dow", "hour"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=range(7), columns=range(24), fill_value=0)
    )
    heatmap_cache = {
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "hours": pivot.columns.tolist(),
        "counts": pivot.values.tolist(),
    }
    return overview, error_cache, cause_cache, heatmap_cache


df_full, df, df_closed = _prepare_data()
PIPELINE = severity_module.PIPELINE
MODEL_METADATA = _load_model_metadata()
STATION_COORDS = build_station_coords(df)
PRIMARY_STATION = primary_station_per_corridor(df)
HOTSPOTS = cluster_hotspots(df, eps_km=0.8, min_samples=4)
G = build_graph()
NODES_DICT = {node: details for node, details in G.nodes(data=True)}
(
    LEARNING_OVERVIEW,
    ERROR_BY_CORRIDOR,
    CAUSE_VOLUME,
    TIME_HEATMAP,
) = _build_learning_cache()


def get_path_metrics(graph, path):
    if not path:
        return {"distance": 0, "path": []}

    distance = 0
    route_details = []
    for start, end in zip(path, path[1:]):
        edge_data = graph.get_edge_data(start, end)
        if edge_data:
            shortest_edge = min(
                edge_data.values(), key=lambda edge: edge["distance_km"]
            )
            distance += shortest_edge["distance_km"]
            route_details.append(
                {
                    "from": start,
                    "to": end,
                    "corridor": shortest_edge["corridor"],
                    "distance": shortest_edge["distance_km"],
                }
            )
    return {"distance": round(distance, 1), "path": route_details}


class EventInput(BaseModel):
    event_cause: str = "others"
    corridor: str = "Non-corridor"
    zone: str = "Unknown"
    priority: str = "Low"
    requires_road_closure_bool: int = Field(default=0, ge=0, le=1)
    hour: int = Field(default=12, ge=0, le=23)
    dow: int = Field(default=0, ge=0, le=6)
    latitude: float = 12.9716
    longitude: float = 77.5946
    crowd_size: int = Field(default=0, ge=0)
    junction: str | None = None
    blocked_corridor: str | None = None
    origin: str | None = None
    destination: str | None = None


@app.get("/api/state")
def get_state():
    return {
        "nodes": NODES_DICT,
        "scenarios": SCENARIOS,
        "hotspots": [
            {"lat": hotspot["lat"], "lon": hotspot["lon"], "size": hotspot["count"]}
            for hotspot in HOTSPOTS
        ],
        "edges": [
            {
                "from": start,
                "to": end,
                "corridor": data["corridor"],
                "distance": data["distance_km"],
            }
            for start, end, data in G.edges(data=True)
        ],
    }


@app.get("/api/scenario/{index}")
def run_scenario(index: int):
    if index < 0 or index >= len(SCENARIOS):
        return {"error": "Invalid scenario index"}

    scenario = SCENARIOS[index]
    primary, secondary = find_diversion_routes(
        G, scenario["blocked"], scenario["origin"], scenario["dest"], HOTSPOTS
    )
    instruction = officer_instruction(
        G, scenario["blocked"], scenario["origin"], scenario["dest"], primary
    )
    return {
        "scenario": scenario,
        "primary": get_path_metrics(G, primary),
        "secondary": get_path_metrics(G, secondary),
        "instruction": instruction,
    }


@app.get("/api/corridors")
def get_corridors():
    return {"corridors": sorted({edge[2] for edge in CORRIDOR_EDGES})}


@app.get("/api/nodes")
def get_nodes():
    return {"nodes": {key: value["name"] for key, value in NODES.items()}}


@app.post("/api/event")
def analyze_event(payload: EventInput):
    severity = severity_module.predict_severity(payload.model_dump())
    barricade = predict_barricade(
        payload.event_cause, severity["severity_score"]
    )
    officers = compute_officers(
        severity["severity_score"],
        payload.corridor,
        payload.crowd_size,
        payload.event_cause,
    )
    stations = recommend_stations(
        payload.latitude,
        payload.longitude,
        STATION_COORDS,
        PRIMARY_STATION.get(payload.corridor),
        app.state.active_load,
        haversine_km,
    )

    result = {
        **severity,
        "officers_needed": officers,
        **barricade,
        "recommended_stations": stations,
    }

    if (
        severity["requires_diversion"]
        and payload.blocked_corridor
        and payload.origin
        and payload.destination
    ):
        if payload.origin not in NODES or payload.destination not in NODES:
            raise HTTPException(status_code=400, detail="Unknown origin or destination")
        result["diversion"] = run_diversion(
            payload.blocked_corridor,
            payload.origin,
            payload.destination,
            df_recent=df.tail(500),
            return_map_html=True,
        )
    else:
        result["diversion"] = None

    arrive_by = f"{(payload.hour - 1) % 24:02d}:30"
    if stations:
        station_names = " PS and ".join(
            station["name"] for station in stations
        ) + " PS"
    else:
        station_names = "the nearest station"
    barricade_clause = (
        f"Set barricades at {barricade['estimated_barricade_points']} approach "
        f"points on {payload.corridor}. "
        if barricade["barricade_needed"]
        else ""
    )
    result["human_instruction"] = (
        f"Deploy {officers} officers from {station_names} to "
        f"{payload.junction or payload.corridor}. {barricade_clause}"
        f"Officers should arrive by {arrive_by}."
    )

    for station in stations:
        name = station["name"]
        app.state.active_load[name] = app.state.active_load.get(name, 0) + 1

    return result


@app.post("/api/reset-load")
def reset_load():
    app.state.active_load = {}
    return {"status": "reset"}


@app.get("/api/learning/overview")
def learning_overview():
    return {
        **LEARNING_OVERVIEW,
        "model_trained_on": MODEL_METADATA.get("trained_at", "unknown"),
        "model_mae": MODEL_METADATA.get("mae"),
        "model_r2": MODEL_METADATA.get("r2"),
    }


@app.get("/api/learning/error-by-corridor")
def error_by_corridor():
    return ERROR_BY_CORRIDOR


@app.get("/api/learning/cause-volume")
def cause_volume():
    return CAUSE_VOLUME


@app.get("/api/learning/time-heatmap")
def time_heatmap():
    return TIME_HEATMAP


@app.post("/api/retrain")
def retrain():
    global PIPELINE, MODEL_METADATA, ERROR_BY_CORRIDOR

    feature_run = subprocess.run(
        [sys.executable, "eda_and_feature_engineering.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if feature_run.returncode != 0:
        return {
            "status": "error",
            "stage": "feature_engineering",
            "stderr": feature_run.stderr[-500:],
        }

    training_run = subprocess.run(
        [sys.executable, "train_regressors.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if training_run.returncode != 0:
        return {
            "status": "error",
            "stage": "training",
            "stderr": training_run.stderr[-500:],
        }

    MODEL_METADATA = _load_model_metadata()
    PIPELINE = joblib.load(ROOT / "best_congestion_pipeline.pkl")
    severity_module.PIPELINE = PIPELINE
    predictions = PIPELINE.predict(df_closed[FEATURE_COLS])
    error_frame = df_closed.assign(
        error_min=df_closed["closure_min"].values - predictions
    )
    grouped = error_frame.groupby("corridor")["error_min"].mean().sort_values()
    ERROR_BY_CORRIDOR = {
        "corridors": grouped.index.tolist(),
        "mean_error_min": grouped.round(1).tolist(),
    }
    return {"status": "ok", "metadata": MODEL_METADATA}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
