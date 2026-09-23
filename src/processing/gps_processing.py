import os
import argparse
import pandas as pd
import numpy as np

def is_valid_coordinate(lat, lon):
    """
    Check if coordinates are not null and within reasonable global bounds.
    """
    if pd.isna(lat) or pd.isna(lon):
        return False
    if lat < -90 or lat > 90:
        return False
    if lon < -180 or lon > 180:
        return False
    return True

def is_inside_route_area(lat, lon):
    """
    Check if coordinates are within the broad validation area.
    Latitude: 9.90 to 9.97
    Longitude: 76.23 to 76.31
    """
    if not is_valid_coordinate(lat, lon):
        return False
    
    lat_valid = 9.90 <= lat <= 9.97
    lon_valid = 76.23 <= lon <= 76.31
    return lat_valid and lon_valid

def process_gps_events(df):
    """
    Validates GPS coordinates and computes M9A mapping fields.
    """
    df_out = df.copy()
    
    # Validation fields
    df_out['gps_valid'] = df_out.apply(
        lambda row: int(is_valid_coordinate(row['center_latitude'], row['center_longitude'])), axis=1
    )
    
    df_out['inside_route_area'] = df_out.apply(
        lambda row: int(is_inside_route_area(row['center_latitude'], row['center_longitude'])), axis=1
    )
    
    def determine_quality(row):
        if not row['gps_valid']:
            return "invalid_coordinates"
        elif not row['inside_route_area']:
            return "outside_route_area"
        else:
            return "good"
            
    df_out['gps_quality'] = df_out.apply(determine_quality, axis=1)
    
    # Map Match outputs (for M9A, just set them to validated coords, or None if invalid)
    df_out['map_match_latitude'] = np.where(df_out['gps_valid'] == 1, df_out['center_latitude'], np.nan)
    df_out['map_match_longitude'] = np.where(df_out['gps_valid'] == 1, df_out['center_longitude'], np.nan)
    
    return df_out

def load_filtered_events(filepath="data/processed/filtered_events.csv"):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    return pd.read_csv(filepath)

def save_gps_processed_events(df, filepath="data/processed/gps_processed_events.csv"):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=False)
    print(f"Saved {len(df)} events to {filepath}")

def run_pipeline(input_path="data/processed/filtered_events.csv", output_path="data/processed/gps_processed_events.csv"):
    print("Running Milestone 9A: GPS Processing...")
    df = load_filtered_events(input_path)
    print(f"Loaded {len(df)} filtered events.")
    
    df_processed = process_gps_events(df)
    
    valid_count = df_processed['gps_valid'].sum()
    inside_count = df_processed['inside_route_area'].sum()
    
    print(f"Validation: {valid_count}/{len(df)} have valid coordinates.")
    print(f"Route Area: {inside_count}/{len(df)} are inside the validation bounding box.")
    
    save_gps_processed_events(df_processed, output_path)
    return df_processed

def main():
    parser = argparse.ArgumentParser(description="M9A: Process and validate GPS coordinates of filtered events.")
    parser.add_argument("--input", default="data/processed/filtered_events.csv", help="Path to input filtered events")
    parser.add_argument("--output", default="data/processed/gps_processed_events.csv", help="Path to output processed events")
    args = parser.parse_args()
    
    run_pipeline(args.input, args.output)

if __name__ == "__main__":
    main()
