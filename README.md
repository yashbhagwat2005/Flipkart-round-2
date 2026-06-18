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
We split the dataset into an **80-20 train-test split** to train three baseline models predicting the continuous `congestion_score` (resolution duration in minutes):

| Model Name | Mean Absolute Error (MAE) | Root Mean Squared Error (RMSE) | $R^2$ Score |
| :--- | :--- | :--- | :--- |
| **Linear Regression** | 3,352.23 mins | 5,792.49 mins | 0.0981 |
| **XGBoost Regressor** | 2,750.26 mins | 5,674.75 mins | 0.1344 |
| **Random Forest Regressor** | **2,539.41 mins** | **5,427.29 mins** | **0.2083** |

* **Winner**: The **Random Forest Regressor** yielded the best scores, reducing prediction error by over **812 minutes** compared to Linear Regression.
* **Serialization**: Saved the best-performing model as `best_congestion_model.pkl` using `joblib`.
* **Plots**: Saved feature importances as `feature_importance.png` and prediction scatter plot as `predictions_vs_actual.png`.

---

## 📁 Project Directory Structure
* `Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv` — Raw dataset.
* `eda_and_feature_engineering.py` — Pipeline script for cleaning, EDA, and feature matrix extraction.
* `engineered_features.csv` — Engineered dataset matrix ready for ML models.
* `train_regressors.py` — Script to train, evaluate, and output the model comparison and plots.
* `best_congestion_model.pkl` — The saved Random Forest regressor model.
* `feature_importance.png` — Visualization showing Latitude, Longitude, and Hour as the top factors.
* `predictions_vs_actual.png` — Scatter plot of predicted values vs actual values.
* `README.md` — Project description and setup instructions.

---

## 🚀 How to Run the Project

### Prerequisites:
Install the required machine learning and plotting dependencies:
```bash
pip install pandas numpy scikit-learn xgboost matplotlib seaborn joblib tabulate
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
This trains the models, displays the comparison table, saves the best model as `best_congestion_model.pkl`, and exports the evaluation charts.
