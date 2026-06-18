# ASTRAM Event-Driven Traffic Congestion Control

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
* **Outlier Removal**: Removed anomalies (negative durations or permanent closures exceeding 30 days) and records missing geographical coordinates.
* **Retained Dataset**: Filtered down to **2,994 high-quality closed traffic incidents** inside Bengaluru.

### 2. Feature Engineering
* **Temporal Features**: Extracted `hour` of the day and `dow` (day of week) from start times.
* **Geographical Hotspots**: Mapped and clustered GPS coordinates (`latitude`, `longitude`).
* **Categorical Encodings**: Built label encoders for `event_cause`, `corridor`, `zone`, and `priority`.
* **Classification Target**: Engineered a 3-class binned `severity` variable (0 = Low < 1h, 1 = Med 1-5h, 2 = High > 5h).
* **Saved Outputs**: Saved the final feature matrix as `engineered_features.csv`.

### 3. Baseline Regressor Modeling & Evaluation
**Script**: `train_regressors.py`
We split the dataset into an **80-20 train-test split** to train three baseline models predicting the continuous `congestion_score` (resolution duration in minutes). The features are processed through a Scikit-Learn `Pipeline` with `ColumnTransformer` to prevent data leakage.

| Model Name | Mean Absolute Error (MAE) | Root Mean Squared Error (RMSE) | $R^2$ Score |
| :--- | :--- | :--- | :--- |
| **Linear Regression** | 3,331.16 mins | 5,779.42 mins | 0.1022 |
| **Random Forest Regressor** | 2,585.52 mins | 5,415.32 mins | 0.2117 |
| **XGBoost Regressor** | **2,391.58 mins** | **5,408.10 mins** | **0.2139** |

* **Winner**: The **XGBoost Regressor** yielded the best scores after hyperparameter tuning with `RandomizedSearchCV`.
* **Serialization**: Saved the full preprocessor and regressor pipeline as `best_congestion_pipeline.pkl` using `joblib`.
* **Plots**: Saved feature importances as `feature_importance.png` and prediction scatter plot as `predictions_vs_actual.png`.

### 4. Diversion Route Planner with Cascade Awareness
**Script**: `diversion_route_planner.py`

When a corridor is blocked (crash, VIP movement, procession), this module finds the **optimal alternate route** while avoiding cascading congestion onto already-busy secondary roads.

**How it works:**
1. **Bengaluru Corridor Graph** — 16 key junctions and all ASTRAM corridors modelled as a weighted `networkx` graph. Edge weight = distance × (1 + historical event density), so high-incident roads cost more and are naturally deprioritised.
2. **DBSCAN Hotspot Detection** — Clusters all events geospatially (haversine metric, eps = 800m) to identify live congestion zones in the city.
3. **Cascade-Aware Routing** — Runs Yen's k-shortest paths (blocking the impacted corridor), then filters out any candidate route whose path nodes fall within 1.2 km of a significant hotspot — preventing spillover jams on the diversion road itself.
4. **Output** — Primary route (green) + secondary backup (amber) on an interactive Folium dark-map, plus a **one-sentence officer instruction** ready for radio dispatch.

**Sample output:**
> *"Divert Mysore Road traffic via Magadi Road → Bannerghatta Road from Kengeri to City Center (MG Road)."*

---

## 📁 Project Directory Structure
* `Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv` — Raw dataset.
* `eda_and_feature_engineering.py` — Pipeline script for cleaning, EDA, and feature matrix extraction.
* `engineered_features.csv` — Engineered dataset matrix ready for ML models.
* `train_regressors.py` — Script to train, evaluate, tune (via RandomizedSearchCV), and output the model comparison and plots.
* `best_congestion_pipeline.pkl` — The saved Scikit-Learn pipeline (contains both the ordinal encoders and the XGBoost regressor).
* `diversion_route_planner.py` — Cascade-aware diversion routing engine (DBSCAN + Dijkstra/Yen's algorithm + Folium map).
* `feature_importance.png` — Visualization of feature impact on the model.
* `predictions_vs_actual.png` — Scatter plot of predicted values vs actual values.
* `README.md` — Project description and setup instructions.

---

## 🚀 How to Run the Project

### Prerequisites:
Install the required machine learning and plotting dependencies:
```bash
pip install pandas numpy scikit-learn xgboost matplotlib seaborn joblib tabulate networkx folium
```

### 1. Run Data Preprocessing & Feature Engineering:
```bash
python eda_and_feature_engineering.py
```
This prints the dataset cleaning statistics, distributions of incident categories, and saves `engineered_features.csv`.

### 2. Train and Evaluate Regressors:
```bash
python train_regressors.py
```
This trains the models, displays the comparison table, saves the best model as `best_congestion_pipeline.pkl`, and exports the evaluation charts.

### 3. Run the Diversion Route Planner:
```bash
python diversion_route_planner.py
```
This detects live hotspot clusters, runs 3 demo blocking scenarios, prints officer instructions, and saves interactive maps as `diversion_map_s1.html`, `diversion_map_s2.html`, `diversion_map_s3.html`.
