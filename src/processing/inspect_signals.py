"""
ROADPULSE — Signal Inspection and Visualization
================================================
Loads raw simulated sensor data and generates visual inspections
and summary statistics for bus passes.

Note on Ground Truth:
---------------------
Ground-truth annotations are shown on inspection plots solely as a
visual reference for human engineers to understand sensor behaviour.
They are NOT used for signal filtering, thresholding, or event detection.
"""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for script/headless execution
import matplotlib.pyplot as plt
import pandas as pd

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sensor_data.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "inspection"


def load_dataset(csv_path=DATA_PATH):
    """Load raw sensor dataset from CSV."""
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"Sensor data CSV not found at: {csv_path}")
    return pd.read_csv(csv_path)


def compute_pass_summary(pass_df):
    """
    Compute a concise dictionary of numerical statistics for a single pass.
    """
    t_vals = pass_df["timestamp"].values
    t_relative = t_vals - t_vals[0]
    duration = float(t_relative[-1] - t_relative[0])
    num_samples = len(pass_df)
    dt_mean = float(duration / (num_samples - 1)) if num_samples > 1 else 0.0

    accel_cols = ["accel_x", "accel_y", "accel_z"]
    gyro_cols = ["gyro_x", "gyro_y", "gyro_z"]

    accel_stats = {
        col: {
            "min": float(pass_df[col].min()),
            "max": float(pass_df[col].max()),
            "mean": float(pass_df[col].mean()),
            "std": float(pass_df[col].std()),
        }
        for col in accel_cols
    }

    gyro_stats = {
        col: {
            "min": float(pass_df[col].min()),
            "max": float(pass_df[col].max()),
            "mean": float(pass_df[col].mean()),
            "std": float(pass_df[col].std()),
        }
        for col in gyro_cols
    }

    start_gps = (float(pass_df["latitude"].iloc[0]), float(pass_df["longitude"].iloc[0]))
    end_gps = (float(pass_df["latitude"].iloc[-1]), float(pass_df["longitude"].iloc[-1]))
    gt_type_counts = pass_df["ground_truth_type"].value_counts().to_dict()

    return {
        "pass_id": int(pass_df["pass_id"].iloc[0]),
        "num_samples": num_samples,
        "duration": duration,
        "sampling_interval": dt_mean,
        "accel_stats": accel_stats,
        "gyro_stats": gyro_stats,
        "gps_start": start_gps,
        "gps_end": end_gps,
        "gt_type_counts": gt_type_counts,
    }


def print_pass_summary(summary):
    """Print ASCII-safe formatted summary for console output."""
    pid = summary["pass_id"]
    print("==================================================")
    print(f"  ROADPULSE -- Pass {pid} Signal Summary")
    print("==================================================")
    print(f"  Samples            : {summary['num_samples']}")
    print(f"  Duration           : {summary['duration']:.2f} s")
    print(f"  Sampling Interval  : {summary['sampling_interval']:.4f} s (approx {1.0/summary['sampling_interval']:.1f} Hz)")
    print(f"  GPS Start          : ({summary['gps_start'][0]:.6f}, {summary['gps_start'][1]:.6f})")
    print(f"  GPS End            : ({summary['gps_end'][0]:.6f}, {summary['gps_end'][1]:.6f})")
    print("--------------------------------------------------")
    print("  Accelerometer Stats (m/s^2):")
    for col, st in summary["accel_stats"].items():
        print(f"    {col:7s} -> min: {st['min']:7.3f}, max: {st['max']:7.3f}, mean: {st['mean']:7.3f}, std: {st['std']:6.3f}")
    print("--------------------------------------------------")
    print("  Gyroscope Stats (rad/s):")
    for col, st in summary["gyro_stats"].items():
        print(f"    {col:7s} -> min: {st['min']:7.3f}, max: {st['max']:7.3f}, mean: {st['mean']:7.3f}, std: {st['std']:6.3f}")
    print("--------------------------------------------------")
    print("  Ground-Truth Scenario Counts (Visual Reference Only):")
    for stype, cnt in summary["gt_type_counts"].items():
        print(f"    {stype:15s} : {cnt} samples")
    print("==================================================")


def _get_event_spans(pass_df, time_col):
    """
    Extract contiguous segments where ground_truth_type != 'none'
    for visualization background shading.
    """
    spans = []
    current_label = None
    start_t = None
    prev_t = None

    for t, label in zip(time_col, pass_df["ground_truth_type"]):
        if label != current_label:
            if current_label and current_label != "none":
                spans.append((start_t, prev_t, current_label))
            current_label = label
            start_t = t
        prev_t = t

    if current_label and current_label != "none":
        spans.append((start_t, prev_t, current_label))

    return spans


# Color palette for visual inspection of scenarios
SCENARIO_COLORS = {
    "pothole": "#e74c3c",       # Red
    "speed_breaker": "#e67e22", # Orange
    "rough_road": "#f1c40f",    # Yellow
    "braking": "#9b59b6",       # Purple
    "turning": "#3498db",       # Blue
    "acceleration": "#2ecc71",  # Green
}


def plot_accelerometer(pass_df, time_rel, spans, out_dir):
    """Plot Accelerometer X, Y, Z signals over time."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 7), sharex=True)
    fig.suptitle(f"ROADPULSE -- Accelerometer Signals (Pass {pass_df['pass_id'].iloc[0]})", fontsize=14, fontweight="bold")

    axes[0].plot(time_rel, pass_df["accel_x"], label="accel_x (lateral)", color="#1f77b4", linewidth=1.0)
    axes[0].set_ylabel("Accel X (m/s²)")
    axes[0].grid(True, linestyle="--", alpha=0.6)
    axes[0].legend(loc="upper right")

    axes[1].plot(time_rel, pass_df["accel_y"], label="accel_y (longitudinal)", color="#2ca02c", linewidth=1.0)
    axes[1].set_ylabel("Accel Y (m/s²)")
    axes[1].grid(True, linestyle="--", alpha=0.6)
    axes[1].legend(loc="upper right")

    axes[2].plot(time_rel, pass_df["accel_z"], label="accel_z (vertical)", color="#d62728", linewidth=1.0)
    axes[2].set_ylabel("Accel Z (m/s²)")
    axes[2].set_xlabel("Time (seconds)")
    axes[2].grid(True, linestyle="--", alpha=0.6)
    axes[2].legend(loc="upper right")

    # Add ground truth shaded overlays for reference
    for ax in axes:
        for start_t, end_t, label in spans:
            c = SCENARIO_COLORS.get(label, "#95a5a6")
            ax.axvspan(start_t, end_t, color=c, alpha=0.18)

    plt.tight_layout()
    out_file = out_dir / f"pass_{pass_df['pass_id'].iloc[0]}_accelerometer.png"
    plt.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file


def plot_gyroscope(pass_df, time_rel, spans, out_dir):
    """Plot Gyroscope X, Y, Z signals over time."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 7), sharex=True)
    fig.suptitle(f"ROADPULSE -- Gyroscope Signals (Pass {pass_df['pass_id'].iloc[0]})", fontsize=14, fontweight="bold")

    axes[0].plot(time_rel, pass_df["gyro_x"], label="gyro_x (roll rate)", color="#17becf", linewidth=1.0)
    axes[0].set_ylabel("Gyro X (rad/s)")
    axes[0].grid(True, linestyle="--", alpha=0.6)
    axes[0].legend(loc="upper right")

    axes[1].plot(time_rel, pass_df["gyro_y"], label="gyro_y (pitch rate)", color="#bcbd22", linewidth=1.0)
    axes[1].set_ylabel("Gyro Y (rad/s)")
    axes[1].grid(True, linestyle="--", alpha=0.6)
    axes[1].legend(loc="upper right")

    axes[2].plot(time_rel, pass_df["gyro_z"], label="gyro_z (yaw rate)", color="#7f7f7f", linewidth=1.0)
    axes[2].set_ylabel("Gyro Z (rad/s)")
    axes[2].set_xlabel("Time (seconds)")
    axes[2].grid(True, linestyle="--", alpha=0.6)
    axes[2].legend(loc="upper right")

    for ax in axes:
        for start_t, end_t, label in spans:
            c = SCENARIO_COLORS.get(label, "#95a5a6")
            ax.axvspan(start_t, end_t, color=c, alpha=0.18)

    plt.tight_layout()
    out_file = out_dir / f"pass_{pass_df['pass_id'].iloc[0]}_gyroscope.png"
    plt.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file


def plot_gps_trajectory(pass_df, spans, out_dir):
    """Plot GPS latitude/longitude trajectory."""
    fig, ax = plt.subplots(figsize=(8, 7))
    pid = pass_df['pass_id'].iloc[0]
    ax.set_title(f"ROADPULSE -- Bus GPS Trajectory (Pass {pid})", fontsize=14, fontweight="bold")

    # Plot base path
    ax.plot(pass_df["longitude"], pass_df["latitude"], color="#7f8c8d", linestyle="--", linewidth=1.5, label="Bus GPS Track")

    # Highlight start and end
    ax.scatter(pass_df["longitude"].iloc[0], pass_df["latitude"].iloc[0], color="#27ae60", s=80, zorder=5, label="Start")
    ax.scatter(pass_df["longitude"].iloc[-1], pass_df["latitude"].iloc[-1], color="#c0392b", s=80, zorder=5, label="End")

    # Overlay anomaly/event segments along route
    for start_t, end_t, label in spans:
        mask = (pass_df["timestamp"] - pass_df["timestamp"].iloc[0] >= start_t) & \
               (pass_df["timestamp"] - pass_df["timestamp"].iloc[0] <= end_t)
        sub = pass_df[mask]
        if not sub.empty:
            c = SCENARIO_COLORS.get(label, "#333333")
            ax.plot(sub["longitude"], sub["latitude"], color=c, linewidth=3.0, label=f"GT: {label}")

    # Remove duplicate legend entries
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="best", fontsize=9)

    ax.set_xlabel("Longitude (deg E)")
    ax.set_ylabel("Latitude (deg N)")
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()

    out_file = out_dir / f"pass_{pid}_gps_trajectory.png"
    plt.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file


def plot_combined_overview(pass_df, time_rel, spans, out_dir):
    """
    Combined overview plot showing key motion dynamics (accel_z, accel_y, gyro_z)
    along with shaded ground-truth event regions.
    """
    fig, axes = plt.subplots(3, 1, figsize=(13, 8), sharex=True)
    pid = pass_df['pass_id'].iloc[0]
    fig.suptitle(f"ROADPULSE -- Combined Signal & Scenario Overview (Pass {pid})", fontsize=14, fontweight="bold")

    # 1. Vertical acceleration (road shocks)
    axes[0].plot(time_rel, pass_df["accel_z"], color="#c0392b", linewidth=1.0, label="accel_z (Vertical Shock)")
    axes[0].axhline(9.81, color="black", linestyle=":", alpha=0.7, label="1g Reference")
    axes[0].set_ylabel("Vertical (m/s²)")
    axes[0].grid(True, linestyle="--", alpha=0.6)
    axes[0].legend(loc="upper right")

    # 2. Longitudinal acceleration (braking / acceleration)
    axes[1].plot(time_rel, pass_df["accel_y"], color="#2980b9", linewidth=1.0, label="accel_y (Longitudinal Force)")
    axes[1].axhline(0.0, color="black", linestyle=":", alpha=0.7)
    axes[1].set_ylabel("Longitudinal (m/s²)")
    axes[1].grid(True, linestyle="--", alpha=0.6)
    axes[1].legend(loc="upper right")

    # 3. Yaw rate (turning)
    axes[2].plot(time_rel, pass_df["gyro_z"], color="#8e44ad", linewidth=1.0, label="gyro_z (Yaw Rate)")
    axes[2].axhline(0.0, color="black", linestyle=":", alpha=0.7)
    axes[2].set_ylabel("Yaw Rate (rad/s)")
    axes[2].set_xlabel("Time (seconds)")
    axes[2].grid(True, linestyle="--", alpha=0.6)
    axes[2].legend(loc="upper right")

    # Overlay ground truth scenario banners
    legend_elements = {}
    for ax in axes:
        for start_t, end_t, label in spans:
            c = SCENARIO_COLORS.get(label, "#95a5a6")
            patch = ax.axvspan(start_t, end_t, color=c, alpha=0.20)
            if label not in legend_elements:
                legend_elements[label] = patch

    # Place a single legend for scenario markers on top subplot
    labels = list(legend_elements.keys())
    handles = [legend_elements[k] for k in labels]
    axes[0].legend(handles, [f"GT: {lbl}" for lbl in labels], loc="upper left", fontsize=8, ncol=3)

    plt.tight_layout()
    out_file = out_dir / f"pass_{pid}_combined_overview.png"
    plt.savefig(out_file, dpi=150)
    plt.close(fig)
    return out_file


def inspect_pass(pass_id=1, csv_path=DATA_PATH, output_dir=OUTPUT_DIR, save_plots=True):
    """
    Main function to inspect a pass, print statistics, and generate plots.
    """
    df = load_dataset(csv_path)
    pass_df = df[df["pass_id"] == pass_id].copy()
    if pass_df.empty:
        raise ValueError(f"No samples found for pass_id={pass_id}")

    summary = compute_pass_summary(pass_df)
    print_pass_summary(summary)

    created_plots = []
    if save_plots:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        time_vals = pass_df["timestamp"].values
        time_rel = time_vals - time_vals[0]
        spans = _get_event_spans(pass_df, time_rel)

        p1 = plot_accelerometer(pass_df, time_rel, spans, out_dir)
        p2 = plot_gyroscope(pass_df, time_rel, spans, out_dir)
        p3 = plot_gps_trajectory(pass_df, spans, out_dir)
        p4 = plot_combined_overview(pass_df, time_rel, spans, out_dir)

        created_plots = [p1, p2, p3, p4]
        print(f"\n[ROADPULSE] Inspection plots saved to: {out_dir}")
        for p in created_plots:
            print(f"  - {p.name}")

    return summary, created_plots


if __name__ == "__main__":
    inspect_pass(pass_id=1)
