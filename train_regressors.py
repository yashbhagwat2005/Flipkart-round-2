import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def train_and_evaluate_regressors():
    # ------------------ STEP 1: LOAD & PREPARE DATA ------------------
    csv_filename = "engineered_features.csv"
    print(f"Loading preprocessed features from {csv_filename}...")
    df = pd.read_csv(csv_filename)
    
    # Rename target closure_min to congestion_score as requested
    df = df.rename(columns={'closure_min': 'congestion_score'})
    
    # Define features and target
    feature_cols = [
        'event_cause_enc', 'corridor_enc', 'zone_enc',
        'requires_road_closure_bool', 'hour', 'dow',
        'latitude', 'longitude', 'priority_enc'
    ]
    
    X = df[feature_cols]
    y = df['congestion_score']
    
    print(f"Dataset prepared. Features: {feature_cols}")
    print(f"Target: congestion_score")
    print(f"Data shape: {X.shape}\n")
    
    # ------------------ STEP 2: TRAIN-TEST SPLIT ------------------
    # 80-20 train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Train shape: {X_train.shape}, Test shape: {X_test.shape}\n")
    
    # ------------------ STEP 3: INITIALIZE MODELS ------------------
    models = {
        "Linear Regression": LinearRegression(),
        "Random Forest Regressor": RandomForestRegressor(n_estimators=100, random_state=42, max_depth=12, n_jobs=-1),
        "XGBoost Regressor": XGBRegressor(n_estimators=100, random_state=42, max_depth=6, learning_rate=0.1, n_jobs=-1)
    }
    
    results = {}
    predictions = {}
    
    # ------------------ STEP 4: TRAIN & EVALUATE ------------------
    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train, y_train)
        
        # Predict on test set
        y_pred = model.predict(X_test)
        predictions[name] = y_pred
        
        # Calculate metrics
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)
        
        results[name] = {
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2,
            "ModelObject": model
        }
        
        print(f"  * MAE:  {mae:.2f} mins")
        print(f"  * RMSE: {rmse:.2f} mins")
        print(f"  * R2:   {r2:.4f}\n")
        
    # ------------------ STEP 5: COMPARISON & FIND BEST MODEL ------------------
    print("=== MODEL COMPARISON SUMMARY ===")
    results_df = pd.DataFrame(results).T.drop(columns=["ModelObject"])
    print(results_df.to_markdown())
    print("\n")
    
    # Select best model based on R2 score (highest is best)
    best_model_name = max(results, key=lambda k: results[k]["R2"])
    best_model_info = results[best_model_name]
    best_model = best_model_info["ModelObject"]
    
    print(f"Best Performing Model: {best_model_name}")
    print(f"  - MAE:  {best_model_info['MAE']:.2f}")
    print(f"  - RMSE: {best_model_info['RMSE']:.2f}")
    print(f"  - R2:   {best_model_info['R2']:.4f}\n")
    
    # Save the best model using joblib
    model_filename = "best_congestion_model.pkl"
    joblib.dump(best_model, model_filename)
    print(f"Saved best performing model ({best_model_name}) to '{model_filename}' using joblib.\n")
    
    # ------------------ STEP 6: GENERATE EVALUATION PLOTS ------------------
    sns.set_theme(style="darkgrid")
    
    # 1. Feature Importance Plot
    if hasattr(best_model, 'feature_importances_'):
        print("Generating Feature Importance Plot...")
        importances = best_model.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        plt.figure(figsize=(10, 6))
        sns.barplot(
            x=importances[indices],
            y=np.array(feature_cols)[indices],
            palette="viridis"
        )
        plt.title(f"Feature Importance - {best_model_name}", fontsize=14, fontweight='bold')
        plt.xlabel("Relative Importance Score", fontsize=12)
        plt.ylabel("Features", fontsize=12)
        plt.tight_layout()
        plt.savefig("feature_importance.png", dpi=300)
        plt.close()
        print("Saved feature importance plot to 'feature_importance.png'\n")
    else:
        print("Best model does not support feature importances (e.g. Linear Regression).\n")
        
    # 2. Prediction vs. Actual Plot
    print("Generating Prediction vs. Actual Plot...")
    y_pred_best = predictions[best_model_name]
    
    plt.figure(figsize=(8, 8))
    sns.scatterplot(x=y_test, y=y_pred_best, alpha=0.6, color="#2563eb")
    
    # Add identity reference line
    min_val = min(y_test.min(), y_pred_best.min())
    max_val = max(y_test.max(), y_pred_best.max())
    plt.plot([min_val, max_val], [min_val, max_val], color='red', linestyle='--', lw=2, label="Perfect Forecast")
    
    plt.title(f"Predictions vs. Actuals ({best_model_name})", fontsize=14, fontweight='bold')
    plt.xlabel("Actual Congestion Score (Minutes)", fontsize=12)
    plt.ylabel("Predicted Congestion Score (Minutes)", fontsize=12)
    plt.legend()
    plt.tight_layout()
    plt.savefig("predictions_vs_actual.png", dpi=300)
    plt.close()
    print("Saved predictions vs. actual plot to 'predictions_vs_actual.png'\n")

if __name__ == "__main__":
    train_and_evaluate_regressors()
