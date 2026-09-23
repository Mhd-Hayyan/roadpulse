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

## Current Status — Milestone 2 Complete

- [x] Project directory structure created
- [x] Python virtual environment (`.venv`) created
- [x] Package `__init__.py` files in place
- [x] `.gitignore` configured
- [x] Next.js + TypeScript + Tailwind CSS + Leaflet frontend scaffolded
- [x] Mock sensor data generator (`src/generator/mock_data.py`) implemented
- [x] Multi-pass raw sensor dataset generated (`data/raw/sensor_data.csv`)
- [x] Dataset validation suite passing (`tests/test_sensor_data.py`)
- [ ] Signal processing & noise filtering — not yet implemented
- [ ] Event detection & classification — not yet implemented
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

## Getting Started

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
