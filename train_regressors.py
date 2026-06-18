import pandas as pd
import numpy as np
import joblib
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.linear_model import LinearRegression
from sklearn.compose import TransformedTargetRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

def load_and_prepare_data(csv_filename: str):
    """Loads feature matrix, defines features and target."""
    logger.info(f"Loading preprocessed features from {csv_filename}...")
    df = pd.read_csv(csv_filename)
    
    # Rename target closure_min to congestion_score
    df = df.rename(columns={'closure_min': 'congestion_score'})
    
    # Define features
    categorical_cols = ['event_cause', 'corridor', 'zone', 'priority']
    numeric_cols = ['requires_road_closure_bool', 'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos', 'latitude', 'longitude']
    
    feature_cols = categorical_cols + numeric_cols
    
    X = df[feature_cols]
    y = df['congestion_score']
    
    logger.info(f"Dataset prepared. Features: {len(feature_cols)} total")
    logger.info(f"Target: congestion_score")
    logger.info(f"Data shape: {X.shape}")
    
    return X, y, categorical_cols, numeric_cols

def build_pipeline(model, categorical_cols):
    """Builds an sklearn pipeline with categorical encoding and the given model."""
    # Use OrdinalEncoder with handle_unknown='use_encoded_value' for unseen categories
    categorical_transformer = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', categorical_transformer, categorical_cols)
        ],
        remainder='passthrough'  # Keep numeric columns as they are
    )
    
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('model', model)
    ])
    
    return pipeline

def train_and_evaluate_models(X_train, X_test, y_train, y_test, categorical_cols):
    """Trains models, performs hyperparameter tuning, and evaluates them."""
    
    # Initialize base models
    rf_base = RandomForestRegressor(random_state=42, n_jobs=-1)
    xgb_base = XGBRegressor(random_state=42, n_jobs=-1)
    lr_base = LinearRegression()
    
    # Define models and their hyperparameter grids
    models_to_train = {
        "Linear Regression": {
            "model": lr_base,
            "params": {} # No hyperparameters to tune
        },
        "Random Forest Regressor": {
            "model": rf_base,
            "params": {
                'model__n_estimators': [100, 200, 300],
                'model__max_depth': [None, 10, 20, 30],
                'model__min_samples_split': [2, 5, 10]
            }
        },
        "XGBoost Regressor": {
            "model": xgb_base,
            "params": {
                'model__n_estimators': [100, 200, 300],
                'model__max_depth': [3, 6, 9],
                'model__learning_rate': [0.01, 0.1, 0.2]
            }
        }
    }
    
    results = {}
    predictions = {}
    best_pipelines = {}
    
    for name, config in models_to_train.items():
        logger.info(f"Training and Tuning {name}...")
        pipeline = build_pipeline(config['model'], categorical_cols)
        
        if config['params']:
            search = RandomizedSearchCV(
                pipeline, 
                param_distributions=config['params'], 
                n_iter=5, # Keep it small for quicker execution
                cv=3, 
                scoring='neg_mean_absolute_error',
                random_state=42,
                n_jobs=-1
            )
            search.fit(X_train, y_train)
            best_model = search.best_estimator_
            logger.info(f"  * Best parameters found: {search.best_params_}")
        else:
            pipeline.fit(X_train, y_train)
            best_model = pipeline
            
        best_pipelines[name] = best_model
        
        # Predict on test set
        y_pred = best_model.predict(X_test)
        predictions[name] = y_pred
        
        # Calculate metrics
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)
        
        results[name] = {
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2
        }
        
        logger.info(f"  * Test MAE:  {mae:.2f} mins")
        logger.info(f"  * Test RMSE: {rmse:.2f} mins")
        logger.info(f"  * Test R2:   {r2:.4f}")
        
    return results, predictions, best_pipelines

def generate_plots(y_test, y_pred_best, best_model_name, best_pipeline, X_train_columns, categorical_cols):
    """Generates evaluation plots."""
    sns.set_theme(style="darkgrid")
    
    # 1. Prediction vs. Actual Plot
    logger.info("Generating Prediction vs. Actual Plot...")
    plt.figure(figsize=(8, 8))
    sns.scatterplot(x=y_test, y=y_pred_best, alpha=0.6, color="#2563eb")
    
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
    logger.info("Saved predictions vs. actual plot to 'predictions_vs_actual.png'")
    
    # 2. Feature Importance Plot (if applicable)
    final_regressor = best_pipeline.named_steps['model']
    if hasattr(final_regressor, 'feature_importances_'):
        logger.info("Generating Feature Importance Plot...")
        
        # Get feature names after column transformer
        preprocessor = best_pipeline.named_steps['preprocessor']
        numeric_cols = [col for col in X_train_columns if col not in categorical_cols]
        feature_names = categorical_cols + numeric_cols # ColumnTransformer order
        
        importances = final_regressor.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        plt.figure(figsize=(10, 6))
        sns.barplot(
            x=importances[indices],
            y=np.array(feature_names)[indices],
            palette="viridis"
        )
        plt.title(f"Feature Importance - {best_model_name}", fontsize=14, fontweight='bold')
        plt.xlabel("Relative Importance Score", fontsize=12)
        plt.ylabel("Features", fontsize=12)
        plt.tight_layout()
        plt.savefig("feature_importance.png", dpi=300)
        plt.close()
        logger.info("Saved feature importance plot to 'feature_importance.png'")
    else:
        logger.info("Best model does not support feature importances.")

def main():
    csv_filename = "engineered_features.csv"
    X, y, categorical_cols, numeric_cols = load_and_prepare_data(csv_filename)
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    logger.info(f"Train shape: {X_train.shape}, Test shape: {X_test.shape}")
    
    # Train, tune and evaluate
    results, predictions, best_pipelines = train_and_evaluate_models(X_train, X_test, y_train, y_test, categorical_cols)
    
    # Comparison summary
    logger.info("=== MODEL COMPARISON SUMMARY ===")
    results_df = pd.DataFrame(results).T
    logger.info("\n" + results_df.to_markdown())
    
    # Select best model
    best_model_name = max(results, key=lambda k: results[k]["R2"])
    best_pipeline = best_pipelines[best_model_name]
    logger.info(f"Best Performing Model: {best_model_name}")
    
    # Save the pipeline
    model_filename = "best_congestion_pipeline.pkl"
    joblib.dump(best_pipeline, model_filename)
    logger.info(f"Saved best performing pipeline ({best_model_name}) to '{model_filename}'")
    
    # Generate plots
    generate_plots(y_test, predictions[best_model_name], best_model_name, best_pipeline, X.columns.tolist(), categorical_cols)

if __name__ == "__main__":
    main()
