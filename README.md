# ASTRAM Traffic Manager - Event-Driven Congestion Control

## 🚦 Operational Challenge & Problem Statement
Political rallies, festivals, sports events, construction activities, and sudden gatherings create localized traffic breakdowns.

### Why It’s Hard Today:
* **Event impact** is not quantified in advance.
* **Resource deployment** is experience-driven.
* **No post-event learning system** exists.

### Problem Statement Direction:
How can historical and real-time data be used to forecast event-related traffic impact and recommend optimal manpower, barricading, and diversion plans?

---

## 🛠️ Work Done So Far

### 1. Exploratory Data Analysis & Data Cleaning
**Script**: `eda_and_feature_engineering.py`
* **Parsed Timestamps**: Converted event start, end, and resolution datetimes.
* **Target Variable**: Calculated congestion duration in minutes (`closure_min`) using the difference between closed timestamps and start timestamps.
* **Retained Dataset**: Filtered down to high-quality closed traffic incidents inside Bengaluru.

### 2. Feature Engineering
* **Temporal Features**: Extracted cyclic `hour` and `dow` (day of week) encodings.
* **Geographical Hotspots**: Mapped and clustered GPS coordinates.
* **Categorical Encodings**: Built label encoders for incident metadata (`event_cause`, `priority`, etc).
* **Saved Outputs**: Saved the final matrix as `engineered_features.csv`.

### 3. Machine Learning Forecasting
**Script**: `train_regressors.py`
We predict the continuous `congestion_score` (resolution duration in minutes).
* **Models**: Evaluated Random Forest, XGBoost, and LightGBM.
* **Log-Transformation**: All regressors are wrapped in a `TransformedTargetRegressor` using `np.log1p` and `np.expm1`. This ensures the models predict the "log" of the time, penalizing percentage errors and making the models incredibly robust against long-duration outliers.
* **Hyperparameter Tuning**: Extended grid search via `RandomizedSearchCV`.
* **Winner**: The script automatically serializes the highest-scoring model and preprocessor pipeline into `best_congestion_pipeline.pkl`.

### 4. Routing Engine API
**Script**: `diversion_route_planner.py` & `server.py`
When a corridor is blocked (crash, VIP movement, procession), this module finds the **optimal alternate route** while avoiding cascading congestion.
1. **Bengaluru Corridor Graph** — Key junctions modeled as a weighted `networkx` graph.
2. **DBSCAN Hotspot Detection** — Clusters all historical/live events geospatially to identify high-risk congestion zones.
3. **Cascade-Aware Routing** — Runs Yen's k-shortest paths, penalizing routes that pass near active hotspots.
4. **FastAPI Engine** — `server.py` exposes the stateless routing engine as REST API endpoints (`/api/scenario/{id}`).

### 5. Web App Dashboard
**Directory**: `/frontend`
A custom single-page React application built with Vite.
* **Google Maps Styling**: Clean, modern layout using CartoDB Voyager tiles.
* **Live Integration**: Fetches dynamic scenario states from the FastAPI backend and instantly renders the primary route (blue), secondary backup (yellow), and blocked segments (red).
* **Metric Cards**: Auto-updates incident clearance times based on ML inferences.

---

## 📁 Project Directory Structure
* `eda_and_feature_engineering.py` — Pipeline script for cleaning, EDA, and feature matrix extraction.
* `train_regressors.py` — Script to train, evaluate, and tune the regression models.
* `best_congestion_pipeline.pkl` — The serialized Scikit-Learn model pipeline.
* `diversion_route_planner.py` — Headless cascade-aware routing engine (NetworkX).
* `server.py` — FastAPI application wrapping the routing engine.
* `frontend/` — React/Vite single-page application dashboard.
* `requirements.txt` — Python dependencies.
* `HOW_TO_RUN_PROJECT.md` — Detailed instructions on starting the servers.

---

## 🚀 How to Run the Project

For a comprehensive step-by-step guide on installing dependencies, training models, and starting both the API and Web App servers, please refer to the **[HOW_TO_RUN_PROJECT.md](./HOW_TO_RUN_PROJECT.md)** file!
