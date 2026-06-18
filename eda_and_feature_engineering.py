import pandas as pd
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CBD_LAT = 12.9716
CBD_LON = 77.5946
MAX_CLOSURE_MINUTES = 43200  # 30 days

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the great-circle distance between two points on the Earth surface."""
    R = 6371.0  # Earth radius in kilometers
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
    return 2 * R * np.arcsin(np.sqrt(a))

def load_data(csv_filename: str) -> pd.DataFrame:
    """Loads the raw CSV dataset."""
    logger.info(f"Loading Dataset: {csv_filename}")
    df = pd.read_csv(csv_filename, low_memory=False)
    logger.info(f"Original Dataset Shape: {df.shape[0]} rows, {df.shape[1]} columns")
    return df

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans data by parsing dates, calculating durations, handling missing values and outliers."""
    logger.info("Starting Data Cleaning & Parsing...")
    
    # Parse datetimes
    df['start_datetime'] = pd.to_datetime(df['start_datetime'], errors='coerce', format='mixed')
    df['closed_datetime'] = pd.to_datetime(df['closed_datetime'], errors='coerce', format='mixed')
    df['resolved_datetime'] = pd.to_datetime(df['resolved_datetime'], errors='coerce', format='mixed')
    
    # Calculate duration (closure_min) in minutes
    df['closure_min'] = (df['closed_datetime'] - df['start_datetime']).dt.total_seconds() / 60.0
    
    # Handle missing values in key fields
    df['event_cause'] = df['event_cause'].fillna('others').astype(str)
    df['corridor'] = df['corridor'].fillna('Non-corridor').astype(str)
    df['zone'] = df['zone'].fillna('Unknown').astype(str)
    df['priority'] = df['priority'].fillna('Low').astype(str)
    df['requires_road_closure_bool'] = df['requires_road_closure'].astype(str).str.upper().map({'TRUE': 1, 'FALSE': 0, '1': 1, '0': 0}).fillna(0).astype(int)
    
    # Clean coordinates
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

    # Remove outlier durations (e.g. negative durations or longer than 30 days)
    initial_valid_durations = df['closure_min'].notnull().sum()
    df_clean = df[(df['closure_min'] >= 0) & (df['closure_min'] <= MAX_CLOSURE_MINUTES)].dropna(subset=['latitude', 'longitude'])
    
    logger.info(f"Total rows with valid closure timestamps: {initial_valid_durations}")
    logger.info(f"Rows retained after removing outliers/null coordinates: {len(df_clean)} (Cleaned shape)")
    return df_clean

def engineer_features(df_clean: pd.DataFrame) -> pd.DataFrame:
    """Engineers cyclical features and defines the target severity without data leakage."""
    logger.info("Starting Feature Engineering...")
    
    # Extract temporal features
    df_clean['hour'] = df_clean['start_datetime'].dt.hour
    df_clean['dow'] = df_clean['start_datetime'].dt.dayofweek
    
    # Create cyclical features for hour and dow
    df_clean['hour_sin'] = np.sin(2 * np.pi * df_clean['hour'] / 24.0)
    df_clean['hour_cos'] = np.cos(2 * np.pi * df_clean['hour'] / 24.0)
    
    df_clean['dow_sin'] = np.sin(2 * np.pi * df_clean['dow'] / 7.0)
    df_clean['dow_cos'] = np.cos(2 * np.pi * df_clean['dow'] / 7.0)
    
    # Weekend indicator
    df_clean['is_weekend'] = df_clean['dow'].isin([5, 6]).astype(int)
    
    # Distance to CBD
    df_clean['distance_to_cbd'] = haversine_km(
        df_clean['latitude'].values, 
        df_clean['longitude'].values, 
        CBD_LAT, 
        CBD_LON
    )
    
    logger.info("Extracted temporal cyclical features and spatial features ('is_weekend', 'distance_to_cbd')")
    
    # Create target variable: severity binned as:
    # Low (0 to 60 mins), Medium (60 to 300 mins), High (over 300 mins)
    df_clean['severity'] = pd.cut(df_clean['closure_min'], bins=[-1, 60, 300, 1000000], labels=[0, 1, 2]).astype(int)
    logger.info("Engineered Target variable: 'severity' (0 = Low < 1h, 1 = Med 1-5h, 2 = High > 5h)")

    # Final feature matrix definition (leaving categorical columns as strings to prevent leakage)
    features = [
        'event_cause', 'corridor', 'zone', 'priority',
        'requires_road_closure_bool', 'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos',
        'is_weekend', 'latitude', 'longitude', 'distance_to_cbd'
    ]
    
    feature_matrix = df_clean[features + ['closure_min', 'severity']]
    logger.info(f"Final Engineered Feature Matrix Shape: {feature_matrix.shape}")
    return feature_matrix

def main():
    csv_filename = "Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"
    
    df = load_data(csv_filename)
    df_clean = clean_data(df)
    
    # Simple EDA logging
    logger.info("--- Distribution of Event Causes ---")
    cause_dist = df_clean['event_cause'].value_counts()
    for cause, count in cause_dist.items():
        logger.info(f"  * {cause:<20} : {count} events ({count/len(df_clean)*100:.1f}%)")
    
    feature_matrix = engineer_features(df_clean)
    
    output_filename = "engineered_features.csv"
    feature_matrix.to_csv(output_filename, index=False)
    logger.info(f"Saved preprocessed feature matrix to '{output_filename}'")

if __name__ == "__main__":
    main()
