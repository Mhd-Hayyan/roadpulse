"""
ROADPULSE — Feature Extraction Pipeline
========================================
Segments preprocessed time-series sensor data into fixed-size overlapping
windows and computes statistical and physical features for each window.

Pipeline Highlights:
--------------------
1. Independent Windowing per Pass:
   Processes each bus pass separately to prevent cross-pass window leakage.
2. 0.5-Second Windows with 50% Overlap:
   At 50 Hz, each window covers 25 samples (~0.48 s duration) with a step size
   of 12 samples (~0.24 s), ensuring road anomaly peaks spanning window boundaries
   are not missed or bisected.
3. Multi-Axis Physical Features:
   - Vertical (accel_z_dynamic): describes road shock severity, bounce energy,
     and peak vertical disturbance.
   - Longitudinal (accel_y_smooth): captures braking and acceleration maneuvers.
   - Lateral (accel_x_smooth): captures body roll and turning maneuvers.
   - Gyroscope (gyro_x, gyro_y, gyro_z, magnitude): captures rotational rate dynamics.
   - GPS: spatial coordinates and displacement over the window.
4. Strict Ground Truth Isolation:
   Ground-truth labels (ground_truth_event, ground_truth_type) are strictly
   excluded from feature extraction and do not appear in the feature dataset.
"""

from pathlib import Path
import numpy as np
import pandas as pd

# Default project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "preprocessed_sensor_data.csv"
OUTPUT_FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"

# Windowing parameters at 50 Hz (~0.02 s sampling interval)
WINDOW_SIZE = 25       # 25 samples ≈ 0.50 s window duration
STEP_SIZE = 12         # 12 samples ≈ 0.24 s step (52% overlap)


def load_preprocessed_data(csv_path=INPUT_DATA_PATH):
    """
    Load preprocessed sensor data from CSV.

    Parameters
    ----------
    csv_path : str or Path
        Path to preprocessed sensor CSV.

    Returns
    -------
    pd.DataFrame
        Loaded preprocessed sensor data.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Preprocessed sensor data not found at: {path}")
    return pd.read_csv(path)


def calculate_gps_displacement(lat1, lon1, lat2, lon2):
    """
    Calculate approximate surface distance (meters) between two GPS points
    using the equirectangular projection approximation.
    """
    earth_radius = 6371000.0  # meters
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    mean_phi = (phi1 + phi2) / 2.0

    x = delta_lambda * np.cos(mean_phi)
    y = delta_phi
    return float(earth_radius * np.sqrt(x**2 + y**2))


def extract_window_features(window_df, pass_id):
    """
    Compute statistical and physical features for a single analysis window.
    Strictly ignores ground_truth columns.

    Parameters
    ----------
    window_df : pd.DataFrame
        Subset of samples within the current window.
    pass_id : int
        The identifier of the active pass.

    Returns
    -------
    dict
        Dictionary of calculated features for this window.
    """
    t_start = float(window_df["timestamp"].iloc[0])
    t_end = float(window_df["timestamp"].iloc[-1])
    duration = float(t_end - t_start)

    # ── Vertical Features (accel_z_dynamic) ─────────────────────────
    az = window_df["accel_z_dynamic"].to_numpy(dtype=float)
    az_mean = float(np.mean(az))
    az_std = float(np.std(az, ddof=0))
    az_min = float(np.min(az))
    az_max = float(np.max(az))
    az_peak_to_peak = float(az_max - az_min)
    az_rms = float(np.sqrt(np.mean(az**2)))
    az_energy = float(np.sum(az**2))
    az_max_abs = float(np.max(np.abs(az)))
    az_diff = np.diff(az)
    az_max_abs_diff = float(np.max(np.abs(az_diff))) if len(az_diff) > 0 else 0.0

    # ── Longitudinal Features (accel_y_smooth) ──────────────────────
    ay = window_df["accel_y_smooth"].to_numpy(dtype=float)
    ay_mean = float(np.mean(ay))
    ay_std = float(np.std(ay, ddof=0))
    ay_min = float(np.min(ay))
    ay_max = float(np.max(ay))
    ay_rms = float(np.sqrt(np.mean(ay**2)))
    ay_max_abs = float(np.max(np.abs(ay)))

    # ── Lateral Features (accel_x_smooth) ───────────────────────────
    ax = window_df["accel_x_smooth"].to_numpy(dtype=float)
    ax_mean = float(np.mean(ax))
    ax_std = float(np.std(ax, ddof=0))
    ax_min = float(np.min(ax))
    ax_max = float(np.max(ax))
    ax_rms = float(np.sqrt(np.mean(ax**2)))
    ax_max_abs = float(np.max(np.abs(ax)))

    # ── Gyroscope Features (smoothed gyro channels) ──────────────────
    gx = window_df["gyro_x_smooth"].to_numpy(dtype=float)
    gy = window_df["gyro_y_smooth"].to_numpy(dtype=float)
    gz = window_df["gyro_z_smooth"].to_numpy(dtype=float)

    gx_mean = float(np.mean(gx))
    gx_std = float(np.std(gx, ddof=0))
    gx_max_abs = float(np.max(np.abs(gx)))

    gy_mean = float(np.mean(gy))
    gy_std = float(np.std(gy, ddof=0))
    gy_max_abs = float(np.max(np.abs(gy)))

    gz_mean = float(np.mean(gz))
    gz_std = float(np.std(gz, ddof=0))
    gz_max_abs = float(np.max(np.abs(gz)))

    # Combined 3D angular velocity magnitude
    gyro_mag = np.sqrt(gx**2 + gy**2 + gz**2)
    gyro_mag_mean = float(np.mean(gyro_mag))
    gyro_mag_max = float(np.max(gyro_mag))

    # ── GPS Features ────────────────────────────────────────────────
    lat_start = float(window_df["latitude"].iloc[0])
    lon_start = float(window_df["longitude"].iloc[0])
    lat_end = float(window_df["latitude"].iloc[-1])
    lon_end = float(window_df["longitude"].iloc[-1])
    displacement = calculate_gps_displacement(lat_start, lon_start, lat_end, lon_end)

    return {
        # Window identification
        "pass_id": int(pass_id),
        "window_start": round(t_start, 4),
        "window_end": round(t_end, 4),
        "window_duration": round(duration, 4),
        # Vertical features
        "accel_z_mean": round(az_mean, 5),
        "accel_z_std": round(az_std, 5),
        "accel_z_min": round(az_min, 5),
        "accel_z_max": round(az_max, 5),
        "accel_z_peak_to_peak": round(az_peak_to_peak, 5),
        "accel_z_rms": round(az_rms, 5),
        "accel_z_energy": round(az_energy, 5),
        "accel_z_max_abs": round(az_max_abs, 5),
        "accel_z_max_abs_diff": round(az_max_abs_diff, 5),
        # Longitudinal features
        "accel_y_mean": round(ay_mean, 5),
        "accel_y_std": round(ay_std, 5),
        "accel_y_min": round(ay_min, 5),
        "accel_y_max": round(ay_max, 5),
        "accel_y_rms": round(ay_rms, 5),
        "accel_y_max_abs": round(ay_max_abs, 5),
        # Lateral features
        "accel_x_mean": round(ax_mean, 5),
        "accel_x_std": round(ax_std, 5),
        "accel_x_min": round(ax_min, 5),
        "accel_x_max": round(ax_max, 5),
        "accel_x_rms": round(ax_rms, 5),
        "accel_x_max_abs": round(ax_max_abs, 5),
        # Gyroscope features
        "gyro_x_mean": round(gx_mean, 6),
        "gyro_x_std": round(gx_std, 6),
        "gyro_x_max_abs": round(gx_max_abs, 6),
        "gyro_y_mean": round(gy_mean, 6),
        "gyro_y_std": round(gy_std, 6),
        "gyro_y_max_abs": round(gy_max_abs, 6),
        "gyro_z_mean": round(gz_mean, 6),
        "gyro_z_std": round(gz_std, 6),
        "gyro_z_max_abs": round(gz_max_abs, 6),
        "gyro_mag_mean": round(gyro_mag_mean, 6),
        "gyro_mag_max": round(gyro_mag_max, 6),
        # GPS features
        "gps_lat_start": round(lat_start, 6),
        "gps_lon_start": round(lon_start, 6),
        "gps_lat_end": round(lat_end, 6),
        "gps_lon_end": round(lon_end, 6),
        "gps_displacement": round(displacement, 3),
    }


def extract_pass_features(pass_df, window_size=WINDOW_SIZE, step_size=STEP_SIZE):
    """
    Extract features for all overlapping windows in a single pass.
    Never crosses into other passes.

    Parameters
    ----------
    pass_df : pd.DataFrame
        Data subset belonging to one pass_id.
    window_size : int
        Number of samples in each window.
    step_size : int
        Number of samples to advance between consecutive windows.

    Returns
    -------
    list of dict
        Extracted feature dictionaries for all windows in this pass.
    """
    pass_id = int(pass_df["pass_id"].iloc[0])
    n_samples = len(pass_df)
    features_list = []

    start_idx = 0
    while start_idx + window_size <= n_samples:
        window_df = pass_df.iloc[start_idx : start_idx + window_size]
        feat = extract_window_features(window_df, pass_id=pass_id)
        features_list.append(feat)
        start_idx += step_size

    return features_list


def extract_dataset_features(df, window_size=WINDOW_SIZE, step_size=STEP_SIZE):
    """
    Extract features across all passes in the dataset independently.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed sensor dataset.
    window_size : int
        Window size in samples.
    step_size : int
        Step size in samples.

    Returns
    -------
    pd.DataFrame
        Extracted features DataFrame.
    """
    all_features = []

    for pass_id, pass_df in df.groupby("pass_id", sort=True):
        pass_features = extract_pass_features(
            pass_df=pass_df,
            window_size=window_size,
            step_size=step_size,
        )
        all_features.extend(pass_features)

    return pd.DataFrame(all_features)


def save_features(features_df, output_path=OUTPUT_FEATURES_PATH):
    """
    Save the extracted features DataFrame to CSV.

    Parameters
    ----------
    features_df : pd.DataFrame
        Extracted features dataset.
    output_path : str or Path
        Destination CSV file path.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    features_df.to_csv(out, index=False)

    print("==================================================")
    print("  ROADPULSE -- Feature Extraction Complete")
    print("==================================================")
    print(f"  Saved to          : {out}")
    print(f"  Total Windows     : {len(features_df):,}")
    print(f"  Passes            : {features_df['pass_id'].nunique()}")
    print(f"  Feature Columns   : {len(features_df.columns)}")
    print(f"  File Size         : {out.stat().st_size / 1024:.1f} KB")
    print("==================================================")


def run_pipeline(input_csv=INPUT_DATA_PATH, output_csv=OUTPUT_FEATURES_PATH):
    """Convenience function to run the full feature extraction pipeline."""
    df_preprocessed = load_preprocessed_data(input_csv)
    features_df = extract_dataset_features(df_preprocessed)
    save_features(features_df, output_csv)
    return features_df


if __name__ == "__main__":
    run_pipeline()
