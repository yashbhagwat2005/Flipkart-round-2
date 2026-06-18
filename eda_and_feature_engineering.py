import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
import json

def run_eda_cleaning_feature_engineering():
    # ------------------ STEP 1: LOAD DATA ------------------
    csv_filename = "Astram event data_anonymized - Astram event data_anonymizedb40ac87.csv"
    print(f"=== [STEP 1] Loading Dataset: {csv_filename} ===")
    df = pd.read_csv(csv_filename, low_memory=False)
    print(f"Original Dataset Shape: {df.shape[0]} rows, {df.shape[1]} columns\n")

    # ------------------ STEP 2: DATA CLEANING ------------------
    print("=== [STEP 2] Data Cleaning & Parsing ===")
    
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
    df_clean = df[(df['closure_min'] >= 0) & (df['closure_min'] <= 43200)].dropna(subset=['latitude', 'longitude'])
    cleaned_valid_durations = df_clean['closure_min'].notnull().sum()
    
    print(f"Total rows with valid closure timestamps: {initial_valid_durations}")
    print(f"Rows retained after removing outliers/null coordinates: {len(df_clean)} (Cleaned shape)")
    print(f"Data Cleaning complete.\n")

    # ------------------ STEP 3: EXPLORATORY DATA ANALYSIS (EDA) ------------------
    print("=== [STEP 3] Exploratory Data Analysis (EDA) ===")
    
    print("--- Distribution of Event Causes ---")
    cause_dist = df_clean['event_cause'].value_counts()
    for cause, count in cause_dist.items():
        print(f"  * {cause:<20} : {count} events ({count/len(df_clean)*100:.1f}%)")
        
    print("\n--- Average & Median Congestion Duration (Minutes) by Cause ---")
    duration_stats = df_clean.groupby('event_cause')['closure_min'].agg(['count', 'mean', 'median']).sort_values(by='count', ascending=False)
    print(duration_stats)

    print("\n--- Distribution of Incident Priority Levels ---")
    prio_dist = df_clean['priority'].value_counts()
    for prio, count in prio_dist.items():
        print(f"  * {prio:<10} : {count} events ({count/len(df_clean)*100:.1f}%)")
        
    print(f"\nCoordinates Boundary box: Lat ({df_clean['latitude'].min():.4f} to {df_clean['latitude'].max():.4f}), Lon ({df_clean['longitude'].min():.4f} to {df_clean['longitude'].max():.4f})\n")

    # ------------------ STEP 4: FEATURE ENGINEERING ------------------
    print("=== [STEP 4] Feature Engineering ===")
    
    # Extract temporal features
    df_clean['hour'] = df_clean['start_datetime'].dt.hour
    df_clean['dow'] = df_clean['start_datetime'].dt.dayofweek
    print("  * Extracted temporal features: 'hour' of day, 'dow' (day of week)")
    
    # Create target variable: severity binned as:
    # Low (0 to 60 mins), Medium (60 to 300 mins), High (over 300 mins)
    df_clean['severity'] = pd.cut(df_clean['closure_min'], bins=[-1, 60, 300, 1000000], labels=[0, 1, 2]).astype(int)
    print("  * Engineered Target variable: 'severity' (0 = Low < 1h, 1 = Med 1-5h, 2 = High > 5h)")
    print("    Severity Distribution:")
    sev_counts = df_clean['severity'].value_counts()
    print(f"      - Low (0)    : {sev_counts.get(0, 0)} events ({sev_counts.get(0,0)/len(df_clean)*100:.1f}%)")
    print(f"      - Medium (1) : {sev_counts.get(1, 0)} events ({sev_counts.get(1,0)/len(df_clean)*100:.1f}%)")
    print(f"      - High (2)   : {sev_counts.get(2, 0)} events ({sev_counts.get(2,0)/len(df_clean)*100:.1f}%)")

    # Categorical Label Encodings
    categorical_cols = ['event_cause', 'corridor', 'zone', 'priority']
    encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        unique_vals = list(df_clean[col].unique())
        if 'Unknown' not in unique_vals:
            unique_vals.append('Unknown')
        le.fit(unique_vals)
        df_clean[col + '_enc'] = le.transform(df_clean[col])
        encoders[col] = le
        print(f"  * Encoded categorical variable: '{col}' -> '{col}_enc'")

    df_clean['priority_enc'] = encoders['priority'].transform(df_clean['priority'])

    # Final feature matrix definition
    features = [
        'event_cause_enc', 'corridor_enc', 'zone_enc',
        'requires_road_closure_bool', 'hour', 'dow',
        'latitude', 'longitude', 'priority_enc'
    ]
    
    feature_matrix = df_clean[features + ['closure_min', 'severity']]
    print(f"\nFinal Engineered Feature Matrix Shape: {feature_matrix.shape}")
    print("\nSample of Engineered Features:")
    print(feature_matrix.head(5).to_string())
    
    # Save the feature matrix for modeling
    feature_matrix.to_csv("engineered_features.csv", index=False)
    print("\nSaved preprocessed feature matrix to 'engineered_features.csv'")

if __name__ == "__main__":
    run_eda_cleaning_feature_engineering()
