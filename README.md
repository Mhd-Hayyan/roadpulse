# ROADPULSE

> **Bus Fleet as a Mobile Road-Condition Sensing Network**

## What is ROADPULSE?

ROADPULSE is a data pipeline that turns ordinary city buses into a distributed road-quality monitoring system. Every bus in a fleet already travels hundreds of kilometres of road every day. By attaching a smartphone to each bus and reading its built-in accelerometer, gyroscope, and GPS, we can passively detect road anomalies — without any dedicated hardware, road closures, or manual surveys.

## The Problem It Solves

Poor road conditions — potholes, speed breakers, rough patches — cost governments, logistics operators, and commuters billions every year in vehicle damage, fuel waste, and accidents. Traditional road surveys are:

- **Expensive** — specialised vehicles, equipment, and trained personnel.
- **Infrequent** — typically done once every few years.
- **Slow to act on** — by the time a report reaches a maintenance team, the damage has worsened.

ROADPULSE replaces periodic surveys with **continuous, crowd-sourced sensing** from the buses that are already on the road.

## How It Works (High Level)

```
Bus smartphone sensors
        │
        ▼
  [generator]  ──  Simulates raw accelerometer / gyroscope / GPS data streams
        │
        ▼
  [processing]  ── Filters noise, detects candidate road anomaly events
        │
        ▼
  [geospatial]  ── Map-matches each event to a specific road segment
        │
        ▼
 [aggregation]  ── Merges repeated detections, scores severity & confidence
        │
        ▼
     [api]      ── Serves results to a frontend map dashboard
        │
        ▼
   [frontend/]  ── Next.js dashboard — heatmap, event markers, filters
```

## Directory Structure

| Path | Purpose |
|------|---------|
| `data/raw/` | Raw sensor recordings (CSV / JSON) before any processing |
| `data/processed/` | Cleaned, labelled data ready for analysis |
| `src/generator/` | Simulated sensor data generation (accelerometer, gyroscope, GPS) |
| `src/processing/` | Signal processing, noise reduction, anomaly event detection |
| `src/geospatial/` | GPS map-matching — linking events to specific road segments |
| `src/aggregation/` | Cross-bus aggregation, severity scoring, confidence calculation |
| `src/api/` | REST API layer exposing road condition data to the frontend |
| `tests/` | Unit and integration tests for all modules |
| `app/` | Next.js App Router — frontend pages and API routes |

## Current Status — Milestone 6A Complete

- [x] Project directory structure created
- [x] Python virtual environment (`.venv`) created
- [x] Package `__init__.py` files in place
- [x] `.gitignore` configured
- [x] Next.js + TypeScript + Tailwind CSS + Leaflet frontend scaffolded
- [x] Mock sensor data generator (`src/generator/mock_data.py`) implemented
- [x] Multi-pass raw sensor dataset generated (`data/raw/sensor_data.csv`)
- [x] Dataset validation suite passing (`tests/test_sensor_data.py`) — 13 pytest checks
- [x] Signal inspection & visualization (`src/processing/inspect_signals.py`) implemented
- [x] Signal inspection test suite passing (`tests/test_signal_inspection.py`) — 5 pytest checks
- [x] Sensor preprocessing pipeline (`src/processing/preprocessing.py`) implemented
- [x] Preprocessing test suite passing (`tests/test_preprocessing.py`) — 9 pytest checks
- [x] Feature extraction pipeline (`src/processing/features.py`) implemented
- [x] Feature extraction test suite passing (`tests/test_features.py`) — 11 pytest checks
- [x] Feature distribution analysis (`src/processing/analyze_feature_distributions.py`) implemented
- [x] Feature distribution test suite passing (`tests/test_feature_distributions.py`) — 10 pytest checks
- [ ] Candidate event detection — not yet implemented
- [ ] Event classification — not yet implemented
- [ ] False-positive filtering — not yet implemented
- [ ] Geospatial map-matching — not yet implemented
- [ ] Multi-pass aggregation & scoring — not yet implemented
- [ ] REST API — not yet implemented
- [ ] Frontend dashboard — not yet implemented

## Mock Sensor Data & Simulation

- **Why mock data?** Real-world bus deployment requires hardware installation, transport permissions, and extensive driving hours. A physically grounded synthetic generator allows rapid, reproducible prototyping and testing of road-anomaly algorithms under known, controlled conditions.
- **Why 50 Hz?** Standard smartphone IMU sensors (accelerometer & gyroscope) comfortably sample at 50 Hz (20 ms interval). This provides sufficient temporal resolution to capture sharp pothole impacts (~100–300 ms) and speed-breaker profiles without generating excessively large log files.
- **What sensors are simulated?**
  - **Tri-axial Accelerometer (`accel_x`, `accel_y`, `accel_z`):** Lateral sway/turns, longitudinal braking/acceleration, and vertical road shocks (including gravity ~9.81 m/s²).
  - **Tri-axial Gyroscope (`gyro_x`, `gyro_y`, `gyro_z`):** Roll, pitch, and yaw angular velocities in rad/s.
  - **GPS (`latitude`, `longitude`):** Time-interpolated coordinates along a fictional Kerala route with realistic ~5–10 m noise.
- **Ground-Truth Labels:**
  - `ground_truth_event` (0 or 1): Binary flag indicating whether the sample coincides with a true road surface anomaly.
  - `ground_truth_type`: Describes the simulated scenario (`none`, `pothole`, `speed_breaker`, `rough_road`, `braking`, `turning`, `acceleration`).
- **Separation of Ground Truth:** The ground-truth columns are provided **strictly for validation, testing, and benchmark evaluation**. Future signal processing and detection pipelines must never read or depend on these columns; detections will be made purely from raw sensor and GPS streams.

## Milestone 3 — Signal Inspection

- **Why Signal Inspection is Necessary:** Before designing filtering stages, heuristic thresholds, or feature extractors for anomaly detection, inspecting the raw signal plots is essential to understand baseline noise levels, impact impulse profiles, decay times, and maneuver patterns (such as braking or turning).
- **What Signals are Inspected:**
  - **Accelerometer ($a_x, a_y, a_z$):** Baseline gravity (~9.81 m/s²), sharp impulse shocks on $a_z$, longitudinal braking/acceleration on $a_y$, and lateral swaying/turning on $a_x$.
  - **Gyroscope ($g_x, g_y, g_z$):** Rotational rates, especially pitch ($g_y$) over speed breakers/braking and yaw ($g_z$) during turns.
  - **GPS Trajectory:** Route tracking from start to end in Ernakulam, Kerala.
  - **Combined Timeline Overview:** Contrast of road surface anomalies against vehicle maneuvers across key motion channels.
- **Ground Truth Role:** Ground-truth scenario labels and time windows are plotted solely as visual references for human inspection. They are not used to formulate detection rules or calculate thresholds.
- **Plot Output Location:** Generated visualization plots are stored under `data/processed/inspection/`:
  - `pass_1_accelerometer.png`: Tri-axial accelerometer time series with event overlays.
  - `pass_1_gyroscope.png`: Tri-axial gyroscope time series with event overlays.
  - `pass_1_gps_trajectory.png`: Spatial trajectory with annotated event sections.
  - `pass_1_combined_overview.png`: Multi-sensor overview contrasting vertical shocks against maneuvers.

## Milestone 4 — Sensor Preprocessing

- **Why Preprocessing is Needed:** Raw smartphone IMU data contains high-frequency electronic noise, road surface vibration hash, and a large gravitational bias (~9.81 m/s² on $a_z$). Preprocessing conditions the signals so feature extractors can accurately measure anomaly impulses and vehicle dynamics without being misled by sensor jitter.
- **What Smoothing Does:** A lightweight, symmetric rolling average (0.10 s / 5 samples at 50 Hz) reduces point-to-point electronic jitter while strictly preserving short-duration physical events (pothole spikes lasting 0.15–0.30 s). Heavy low-pass filtering is avoided so impact transients are not flattened.
- **Why Gravity Removal is Useful:** Static gravity masks relative road shocks. By estimating a slow-moving baseline ($a_{z,\text{baseline}}$ over a 2.0 s window), we derive the dynamic vertical component ($a_{z,\text{dynamic}} = a_{z,\text{smooth}} - a_{z,\text{baseline}}$), centered cleanly around $0.0\text{ m/s}^2$ on flat terrain.
- **Why Raw Signals are Preserved:** All original raw channels (`accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z`), timestamps, GPS coordinates, and ground-truth tags are preserved side-by-side with processed features for auditability and validation.
- **Why Orientation Correction is Postponed:** Real-world deployments require estimating smartphone attitude (Euler angles/quaternions) to project sensor readings into vehicle coordinates. Because our simulation mounts the sensor directly aligned with the bus frame, orientation estimation is deferred to keep the hackathon codebase explainable and beginner-friendly.
- **Output Location:** The processed dataset is saved to `data/processed/preprocessed_sensor_data.csv`.

## Milestone 5 — Feature Extraction

- **What is a Time Window?** Instead of classifying every individual 20 ms sensor reading in isolation, we group consecutive readings into time windows (e.g. 25 samples spanning ~0.50 seconds). Road events like potholes and speed breakers unfold over time, so an entire window captures the complete physical impulse and recovery.
- **Why Use Overlapping Windows?** With a 50% overlap (12-sample step size / ~0.24 s advance), every moment in time is covered by at least two windows. This prevents a critical anomaly spike that occurs near a window boundary from being split into two weak, undetected halves.
- **Why Multiple Features Instead of Raw Samples?** Raw instantaneous accelerations fluctuate rapidly due to road texture and vibrations. Aggregating into statistical and physical features summarizes the shape, magnitude, and directionality of the motion:
  - **Peak-to-Peak Range & Max Absolute Value:** Measure the extreme impact force, distinguishing a sharp pothole dip/spike ($>3\text{ m/s}^2$) from benign cruising.
  - **Root Mean Square (RMS) & Signal Energy:** Quantify sustained vibration power over time, clearly identifying extended rough road patches even when individual peaks are moderate.
  - **Standard Deviation (Variance):** Indicates signal turbulence; flat smooth road has low variance, while anomalies produce high variance.
  - **Longitudinal ($a_y$) vs. Lateral ($a_x$) vs. Vertical ($a_z$):** Decouples maneuvers (braking drops $a_y$, turning spikes $a_x$ and yaw rate $g_z$) from road surface defects (which dominate $a_z$).
- **Strict Ground Truth Isolation:** Ground truth columns (`ground_truth_event`, `ground_truth_type`) are strictly excluded during feature calculation and do not exist in the features dataset. Detection code will rely exclusively on sensor-derived motion statistics.
- **Output Location:** The extracted features dataset is saved to `data/processed/features.csv`.

## Milestone 6A — Feature Distribution Analysis

- **Why Analyse Feature Distributions?** Before writing any detection rules or thresholds, we need empirical evidence that our extracted features actually differ between road-surface anomaly scenarios and normal driving. If a feature does not separate scenarios it adds noise to detection; if it does, we know its threshold range.
- **Window Label Assignment:** Each feature window is assigned a dominant scenario label by taking the most frequent `ground_truth_type` value among all raw samples that fall inside that window. The window's **purity** (fraction of samples matching the dominant label) measures how cleanly a single scenario occupies the window. Windows with purity ≥ 0.80 are used for analysis (94.86% of all windows qualify).
- **Ground Truth Role in 6A:** Ground truth is used here **only for analysis and visualization** — it is never used by the actual detection pipeline. The feature distribution plots are reference material for the human designer setting detection thresholds, not inputs to any algorithm.
- **Key Discriminating Features Identified:**

  | Feature | What it Separates |
  |---------|-------------------|
  | `accel_z_max_abs_diff` | Pothole (sharp spike) vs. normal cruising |
  | `accel_z_peak_to_peak` | Speed breaker (broad vertical swing) vs. normal |
  | `accel_z_std` / `accel_z_rms` | Rough road (sustained vibration) vs. normal |
  | `accel_y_mean` | Braking (negative) / acceleration (positive) vs. road events (~0) |
  | `accel_x_max_abs` | Turning (lateral spike) vs. all road events |
  | `gyro_z_max_abs` | Turning (yaw rate) vs. all road events |

- **Outputs:** All outputs are saved under `data/processed/feature_analysis/`:
  - `feature_distribution_summary.csv` — per-feature median, IQR, min, max broken down by scenario.
  - `window_label_analysis.csv` — per-window label, purity, and all 41 features for reference.
  - `accel_z_max_abs_diff.png`, `accel_z_peak_to_peak.png`, `accel_z_std.png`, `accel_y_mean.png`, `accel_y_max_abs.png`, `accel_x_max_abs.png`, `gyro_z_max_abs.png`, `gyro_mag_max.png` — side-by-side boxplots for the 8 most discriminating features.



### Backend (Python)

```bash
# Activate the virtual environment (Windows)
.venv\Scripts\activate

# Activate the virtual environment (macOS / Linux)
source .venv/bin/activate

# Install dependencies (once requirements.txt is populated)
pip install -r requirements.txt
```

### Frontend (Next.js)

```bash
# Install Node dependencies
npm install

# Run the development server
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000) in your browser.

## Hackathon Context

ROADPULSE was built for a hackathon. Every component is designed to be simple, explainable, and demo-ready. The goal is not perfection — it is a working proof-of-concept that a judge can understand in five minutes.
