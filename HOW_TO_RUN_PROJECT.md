# How to run ASTRAM Traffic Manager

## Prerequisites

- Python 3.11+
- Node.js 18+
- The ASTRAM CSV file in the repo root directory

## First-time setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Build the feature matrix and train the model
```bash
python eda_and_feature_engineering.py
python train_regressors.py
```
This creates `engineered_features.csv`, `best_congestion_pipeline.pkl`,
and `model_metadata.json`. Check the printed MAE and R² before continuing.

### 3. Install frontend dependencies
```bash
cd frontend
npm install
```

## Running the app

### Terminal 1 — backend
```bash
python server.py
```
API is live at http://127.0.0.1:8000

### Terminal 2 — frontend
```bash
cd frontend
npm run dev
```
App is live at http://localhost:5173

## Demo flow

1. Open the app. The three quick-demo scenario cards pre-fill the form.
2. Click any scenario card or fill the form manually and click Analyze.
3. Switch to Diversion Map to see the route visualisation.
4. Switch to Learning Dashboard to see model accuracy and error patterns.
5. Click Retrain to re-run the full pipeline against the latest data.

## Resetting station load between demo runs

Between demo runs, station load counters accumulate. Reset them:
```bash
curl -X POST http://127.0.0.1:8000/api/reset-load
```
Or add a reset button call at the start of each demo run.

## Troubleshooting

**Backend won't start:** make sure `best_congestion_pipeline.pkl` exists.
Run `python train_regressors.py` if it's missing.

**Frontend shows "Backend unreachable":** confirm the backend is running
on port 8000 and CORS is open (it is by default).

**Severity score is always 100:** the model may be trained on unfiltered
data with extreme outliers. Re-run `eda_and_feature_engineering.py` and
`train_regressors.py` to regenerate the model.
