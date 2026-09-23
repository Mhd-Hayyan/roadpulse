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

## Current Status — Milestone 1

This milestone establishes the project skeleton only:

- ✅ Project directory structure created
- ✅ Python virtual environment (`.venv`) created
- ✅ Package `__init__.py` files in place
- ✅ `.gitignore` configured
- ⬜ Sensor simulation — not yet implemented
- ⬜ Signal processing — not yet implemented
- ⬜ Event detection — not yet implemented
- ⬜ Geospatial map-matching — not yet implemented
- ⬜ Aggregation & scoring — not yet implemented
- ⬜ REST API — not yet implemented
- ⬜ Dependencies — not yet chosen (`requirements.txt` is empty)

## Getting Started

```bash
# Activate the virtual environment (Windows)
.venv\Scripts\activate

# Activate the virtual environment (macOS / Linux)
source .venv/bin/activate

# Install dependencies (once requirements.txt is populated)
pip install -r requirements.txt
```

## Hackathon Context

ROADPULSE was built for a hackathon. Every component is designed to be simple, explainable, and demo-ready. The goal is not perfection — it is a working proof-of-concept that a judge can understand in five minutes.
