"""
ROADPULSE — Sensor Preprocessing Pipeline
==========================================
Prepares raw bus IMU and GPS time-series signals for downstream
feature extraction and event detection while preserving event timing.

Pipeline Highlights:
--------------------
1. Independent Pass Processing:
   Processes each pass separately to prevent cross-pass temporal leakage.
2. Lightweight Noise Reduction:
   Applies a short symmetric rolling window (0.10 s / 5 samples at 50 Hz)
   to attenuate high-frequency sensor noise without flattening sharp pothole impacts.
3. Gravity Baseline Separation:
   Estimates the local static gravity component (~9.81 m/s²) using a wider
   rolling window (2.0 s / 101 samples) and derives accel_z_dynamic centered at 0.
4. Preserves Raw Signals & Metadata:
   All raw columns, timestamps, GPS, and ground-truth evaluation markers
   remain intact and unaltered.

Note on Phone Orientation:
--------------------------
In a real-world smartphone deployment, phone mounting orientation relative
to the bus body must be estimated (e.g., via gravity estimation during stops
and forward acceleration during departure, or a Madgwick/Mahony filter).
In this simulated dataset, the phone coordinate frame is already aligned with
the vehicle axes (X=lateral, Y=longitudinal, Z=vertical + gravity), so explicit
coordinate rotation is postponed.
"""

from pathlib import Path
import numpy as np
import pandas as pd

# Default project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sensor_data.csv"
PROCESSED_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "preprocessed_sensor_data.csv"

# Preprocessing parameters (at 50 Hz, 1 sample = 0.02 s)
SMOOTH_WINDOW = 5        # 5 samples = 0.10 s: light smoothing for jitter reduction
GRAVITY_WINDOW = 101     # 101 samples = 2.02 s: captures slow gravity/tilt changes


def load_sensor_data(csv_path=RAW_DATA_PATH):
    """
    Load raw sensor data from CSV.

    Parameters
    ----------
    csv_path : str or Path
        Path to the raw CSV file.

    Returns
    -------
    pd.DataFrame
        Loaded raw sensor data.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Raw sensor CSV not found at: {path}")
    return pd.read_csv(path)


def preprocess_pass(pass_df, smooth_window=SMOOTH_WINDOW, gravity_window=GRAVITY_WINDOW):
    """
    Preprocess IMU signals for a single bus pass.

    Parameters
    ----------
    pass_df : pd.DataFrame
        Data subset containing exactly one pass_id.
    smooth_window : int
        Window size (samples) for light smoothing.
    gravity_window : int
        Window size (samples) for slow-moving gravity estimation.

    Returns
    -------
    pd.DataFrame
        A new DataFrame with original columns preserved and processed columns added.
    """
    df = pass_df.copy()

    # 1. Lightly smooth accelerometer axes (symmetric window, no NaNs at edges)
    df["accel_x_smooth"] = (
        df["accel_x"]
        .rolling(window=smooth_window, center=True, min_periods=1)
        .mean()
        .round(5)
    )
    df["accel_y_smooth"] = (
        df["accel_y"]
        .rolling(window=smooth_window, center=True, min_periods=1)
        .mean()
        .round(5)
    )
    df["accel_z_smooth"] = (
        df["accel_z"]
        .rolling(window=smooth_window, center=True, min_periods=1)
        .mean()
        .round(5)
    )

    # 2. Gravity removal on vertical axis
    # The slow rolling mean isolates the quasi-static gravity component (~9.81 m/s²)
    # plus road grade/tilt, without being distorted by brief road events.
    df["accel_z_baseline"] = (
        df["accel_z"]
        .rolling(window=gravity_window, center=True, min_periods=1)
        .mean()
        .round(5)
    )
    # Dynamic vertical acceleration = smoothed vertical minus static gravity
    df["accel_z_dynamic"] = (df["accel_z_smooth"] - df["accel_z_baseline"]).round(5)

    # 3. Lightly smooth gyroscope axes
    df["gyro_x_smooth"] = (
        df["gyro_x"]
        .rolling(window=smooth_window, center=True, min_periods=1)
        .mean()
        .round(6)
    )
    df["gyro_y_smooth"] = (
        df["gyro_y"]
        .rolling(window=smooth_window, center=True, min_periods=1)
        .mean()
        .round(6)
    )
    df["gyro_z_smooth"] = (
        df["gyro_z"]
        .rolling(window=smooth_window, center=True, min_periods=1)
        .mean()
        .round(6)
    )

    return df


def preprocess_dataset(df, smooth_window=SMOOTH_WINDOW, gravity_window=GRAVITY_WINDOW):
    """
    Preprocess all passes in the dataset independently.

    Parameters
    ----------
    df : pd.DataFrame
        Complete raw dataset containing multiple passes.
    smooth_window : int
        Window size for smoothing.
    gravity_window : int
        Window size for gravity baseline.

    Returns
    -------
    pd.DataFrame
        Combined preprocessed dataset.
    """
    preprocessed_passes = []

    for pass_id, pass_df in df.groupby("pass_id", sort=True):
        processed_pass = preprocess_pass(
            pass_df=pass_df,
            smooth_window=smooth_window,
            gravity_window=gravity_window,
        )
        preprocessed_passes.append(processed_pass)

    return pd.concat(preprocessed_passes, ignore_index=True)


def save_preprocessed_data(df, output_path=PROCESSED_DATA_PATH):
    """
    Save the preprocessed DataFrame to CSV.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed dataset.
    output_path : str or Path
        Destination file path.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    print("==================================================")
    print("  ROADPULSE -- Preprocessing Complete")
    print("==================================================")
    print(f"  Saved to      : {out}")
    print(f"  Total Rows    : {len(df):,}")
    print(f"  Passes        : {df['pass_id'].nunique()}")
    print(f"  Total Columns : {len(df.columns)}")
    print(f"  File Size     : {out.stat().st_size / 1024:.1f} KB")
    print("==================================================")


def run_pipeline(raw_csv=RAW_DATA_PATH, output_csv=PROCESSED_DATA_PATH):
    """Convenience function to execute the full preprocessing pipeline."""
    df_raw = load_sensor_data(raw_csv)
    df_processed = preprocess_dataset(df_raw)
    save_preprocessed_data(df_processed, output_csv)
    return df_processed


if __name__ == "__main__":
    run_pipeline()
