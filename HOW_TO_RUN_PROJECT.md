# ASTRAM Traffic Manager - Project Setup & Execution Guide

This document outlines the step-by-step process for setting up the environment, training the machine learning models, and running the full-stack web application (FastAPI + React).

---

## 1. Project Architecture

* **Backend Engine (Python)**: Handles data engineering, ML inference, shortest-path graph algorithms (NetworkX), and DBSCAN hotspot clustering. Exposed via FastAPI.
* **Frontend Web App (React + Vite)**: A dynamic single-page dashboard with glassmorphism/Material styling, communicating with the Python backend to render live `react-leaflet` maps.

---

## 2. Environment Setup

### Install Python Backend Dependencies
Ensure you have Python 3.10+ installed. Open a terminal in the root directory (`Flipkart-round-2`) and install the required machine learning and web server packages:

```bash
pip install -r requirements.txt
```

### Install Frontend Dependencies
The React app uses Node.js. Make sure you have Node.js installed, then navigate to the `frontend` folder to install the `node_modules`:

```bash
cd frontend
npm install
```

---

## 3. Execution Order

### Step A: Data Engineering & Model Training (Optional/One-Time)
If you need to re-train the models or re-process the data from the raw CSV, run these scripts in order. *(Note: We already have `best_congestion_pipeline.pkl` and `engineered_features.csv` generated, so this step can be skipped if you just want to run the app).*

1. **Feature Engineering**: Cleans raw data and engineers cyclic temporal features and geospatial distances.
   ```bash
   python eda_and_feature_engineering.py
   ```
2. **Train Regressors**: Trains Random Forest, XGBoost, and LightGBM wrapped in Log-Transformers. Auto-selects the best model and saves it.
   ```bash
   python train_regressors.py
   ```

### Step B: Start the FastAPI Backend
The backend must be running for the frontend to receive graph data, scenarios, and routing logic. Open a terminal in the root folder:

```bash
python server.py
```
*The server will start on `http://127.0.0.1:8000`.*

### Step C: Start the React Frontend
Open a **new, separate terminal**, navigate to the `frontend` folder, and launch the Vite development server:

```bash
cd frontend
npm run dev
```
*Vite will provide a localhost URL (usually `http://localhost:5173`). Open this link in your web browser to view the ASTRAM Traffic Manager dashboard!*
