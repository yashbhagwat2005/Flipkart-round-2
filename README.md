# ASTRAM Traffic Manager

Event-driven congestion control for Bengaluru Traffic Police.
Built for the Flipkart × BTP Hackathon 2024.

## What it does

One FastAPI backend + one React frontend. Submit any traffic event and get:
- **Severity score** (0–100) predicted from a trained ML regressor
- **Officer count** and **station recommendation** based on corridor history
- **Barricade assessment** with confidence level
- **Diversion route** (cascade-aware, hotspot-penalised) when severity ≥ 40
- **Learning dashboard** showing model error by corridor, cause volume,
  time-of-day heatmap, and one-click retraining

## Stack

Backend: Python 3.11, FastAPI, scikit-learn, LightGBM, NetworkX, Folium
Frontend: React 18, Vite, Recharts, Framer Motion, Leaflet

## How to run

See HOW_TO_RUN_PROJECT.md for full setup steps.

## Files

| File | Purpose |
|---|---|
| `eda_and_feature_engineering.py` | Cleans CSV, engineers features, writes `engineered_features.csv` |
| `train_regressors.py` | Trains RF/LightGBM regressors, saves `best_congestion_pipeline.pkl` and `model_metadata.json` |
| `severity.py` | Loads pipeline, exposes `predict_severity()` |
| `manpower.py` | Officer formula, barricade heuristic, station recommendation |
| `diversion_route_planner.py` | Graph, DBSCAN hotspots, Yen's k-shortest-paths, `run_diversion()` |
| `server.py` | FastAPI app, all endpoints |
| `config.py` | Shared constants (CSV filename, CBD coordinates) |
| `graph_config.py` | Junction coordinates and corridor edges |
| `frontend/` | React/Vite SPA |

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/state` | Full graph state for initial map load |
| GET | `/api/scenario/{index}` | One of 3 pre-built demo scenarios (0, 1, 2) |
| GET | `/api/corridors` | List of all corridors for dropdowns |
| GET | `/api/nodes` | Junction id→name map for dropdowns |
| POST | `/api/event` | Full event analysis (severity + manpower + diversion) |
| POST | `/api/reset-load` | Reset in-memory station load counters |
| GET | `/api/learning/overview` | Model metrics and dataset stats |
| GET | `/api/learning/error-by-corridor` | Mean prediction error per corridor |
| GET | `/api/learning/cause-volume` | Cause count vs median closure duration |
| GET | `/api/learning/time-heatmap` | Event volume by day-of-week × hour |
| POST | `/api/retrain` | Re-run feature engineering + training, hot-reload model |
