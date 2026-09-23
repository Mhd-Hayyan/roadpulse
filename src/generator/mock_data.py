"""
ROADPULSE — Mock Sensor Data Generator
=======================================
Simulates smartphone accelerometer, gyroscope and GPS data recorded
by a bus travelling along a fictional but geographically plausible
Kerala route.

Usage
-----
    python src/generator/mock_data.py

Output
------
    data/raw/sensor_data.csv

Physical axis convention (right-hand, sensor frame)
----------------------------------------------------
    accel_x  — lateral axis        (+right)           m/s²
    accel_y  — longitudinal axis   (+forward)         m/s²
    accel_z  — vertical axis       (+up, includes gravity ≈ 9.81)  m/s²
    gyro_x   — roll rate                               rad/s
    gyro_y   — pitch rate                              rad/s
    gyro_z   — yaw rate                                rad/s

Ground-truth policy
-------------------
    ground_truth_event : 1 if a real road-surface anomaly is present, else 0
    ground_truth_type  : string label for the active scenario in this section

    ⚠ These columns are for EVALUATION ONLY.
      Future detection code must NOT read or depend on them.
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ─── Configurable constants ───────────────────────────────────────────────────
SAMPLE_RATE = 50              # Hz — 50 samples per second is standard for
                              #       smooth event detection without data excess
DT          = 1.0 / SAMPLE_RATE   # 0.02 s between consecutive samples
NUM_PASSES  = 4               # Number of bus passes over the same route
RANDOM_SEED = 42              # Change this to get a different (but reproducible) dataset

G = 9.81   # m/s² — standard gravity

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_CSV   = PROJECT_ROOT / "data" / "raw" / "sensor_data.csv"


# ─── Fictional Kerala route ───────────────────────────────────────────────────
# A fictional bus route near Ernakulam, Kerala.
# (latitude, longitude) waypoints — geographically plausible, ~1.5 km long.
# NOT based on any real person's private location data.
WAYPOINTS = [
    (9.9312, 76.2673),   # Start — near Ernakulam South
    (9.9323, 76.2685),
    (9.9337, 76.2697),
    (9.9352, 76.2709),
    (9.9368, 76.2721),
    (9.9383, 76.2733),
    (9.9398, 76.2746),
    (9.9413, 76.2758),   # End   — approaching MG Road area
]


# ─── Route section definitions ────────────────────────────────────────────────
# Each section describes one segment of the journey.
#
# 'duration'  : how many seconds this section lasts
# 'scenario'  : the physical phenomenon to simulate
# 'label'     : ground_truth_type for ALL samples in this section
#
# The actual sensor event (e.g. pothole spike) is embedded WITHIN the section.
# Approach and departure samples carry the same label but show normal signals.
ROUTE_SECTIONS = [
    {"duration": 6.0, "scenario": "normal",        "label": "none"},
    {"duration": 5.0, "scenario": "pothole",        "label": "pothole"},
    {"duration": 4.0, "scenario": "normal",         "label": "none"},
    {"duration": 5.0, "scenario": "speed_breaker",  "label": "speed_breaker"},
    {"duration": 4.0, "scenario": "normal",         "label": "none"},
    {"duration": 7.0, "scenario": "rough_road",     "label": "rough_road"},
    {"duration": 4.0, "scenario": "normal",         "label": "none"},
    {"duration": 5.0, "scenario": "braking",        "label": "braking"},
    {"duration": 3.0, "scenario": "normal",         "label": "none"},
    {"duration": 6.0, "scenario": "turning",        "label": "turning"},
    {"duration": 3.0, "scenario": "normal",         "label": "none"},
    {"duration": 4.0, "scenario": "acceleration",   "label": "acceleration"},
    {"duration": 5.0, "scenario": "normal",         "label": "none"},
]

TOTAL_DURATION = sum(s["duration"] for s in ROUTE_SECTIONS)   # seconds per pass


# ─── Base signal: smooth normal driving ───────────────────────────────────────

def _normal_base(n, rng):
    """
    Generate sensor arrays representing smooth, uneventful driving.

    Even on a good road a bus is never perfectly quiet:
    - Engine and road vibration appear on accel_z at 5–15 Hz
    - Gentle body sway appears on accel_x at sub-1 Hz
    - All channels carry low-level white noise
    """
    t = np.arange(n) * DT

    # Lateral — gentle body sway at a slow frequency
    ax = (0.02 * np.sin(2 * np.pi * 0.7 * t + rng.uniform(0, 2 * np.pi))
          + rng.normal(0.0, 0.04, n))

    # Longitudinal — near-zero at constant cruising speed
    ay = rng.normal(0.0, 0.04, n)

    # Vertical — gravity dominates; road and engine vibration sit on top
    az = (G
          + 0.10 * np.sin(2 * np.pi * 6.5  * t + rng.uniform(0, 2 * np.pi))
          + 0.06 * np.sin(2 * np.pi * 11.0 * t + rng.uniform(0, 2 * np.pi))
          + rng.normal(0.0, 0.08, n))

    # Gyroscope — very low rotational activity on a straight road
    gx = rng.normal(0.0, 0.007, n)   # roll rate
    gy = rng.normal(0.0, 0.007, n)   # pitch rate
    gz = rng.normal(0.0, 0.004, n)   # yaw rate

    return {"ax": ax, "ay": ay, "az": az, "gx": gx, "gy": gy, "gz": gz}


# ─── Pothole ──────────────────────────────────────────────────────────────────

def _pothole(n, rng, intensity=1.0):
    """
    Simulate a wheel striking and rebounding from a pothole.

    Physical model
    --------------
    When a wheel drops into a pothole and hits the far edge, the suspension
    undergoes a damped-spring response:

        z(t) = A · exp(−decay · |t|) · sin(2π · f · t + φ)

    This produces a sharp negative dip followed by a strong positive rebound,
    which then damps out over ~0.3 s.

    Key characteristics
    -------------------
    - Very SHORT duration  (~0.2–0.3 s core event)
    - Sharp VERTICAL spike (accel_z)
    - Small lateral jolt on accel_x (tire catching the pothole edge)
    - Slight pitch on gyro_y

    ground_truth_event = 1  (this IS a road surface anomaly)
    """
    sig = _normal_base(n, rng)
    event_mask = np.zeros(n, dtype=int)

    t = np.arange(n) * DT
    t_rel = t - (n // 2) * DT   # time relative to the moment of impact

    # Randomise parameters so every pothole looks slightly different
    amplitude   = intensity * rng.uniform(3.5, 6.5)    # m/s² — severity of impact
    freq        = rng.uniform(8.0, 13.0)               # Hz   — suspension bounce rate
    decay       = rng.uniform(12.0, 20.0)              # 1/s  — how fast vibration dies
    phase_shift = rng.uniform(-0.4, 0.4)               # rad  — randomises the waveform

    # Damped sinusoidal vertical perturbation
    in_window = np.abs(t_rel) < 0.5   # only compute within a ±0.5 s window
    z_perturb = np.where(
        in_window,
        amplitude * np.exp(-decay * np.abs(t_rel))
                  * np.sin(2 * np.pi * freq * t_rel + phase_shift),
        0.0,
    )
    sig["az"] += z_perturb

    # Small lateral jolt as the tire edge catches the pothole wall
    sig["ax"] += np.where(in_window, rng.normal(0.0, 0.08 * amplitude, n), 0.0)

    # Slight pitch response on the front axle
    sig["gy"] += np.where(
        in_window,
        0.025 * amplitude * np.sin(2 * np.pi * freq * t_rel),
        0.0,
    )

    # Mark only the tight core-impact window as a road event
    event_mask[np.abs(t_rel) < 0.15] = 1

    return sig, event_mask


# ─── Speed breaker ────────────────────────────────────────────────────────────

def _speed_breaker(n, rng, intensity=1.0):
    """
    Simulate a bus crossing a road speed breaker (hump).

    Physical model
    --------------
    As the bus rides over the hump, the front axle goes UP then DOWN,
    followed ~0.3 s later by the rear axle repeating the same motion.
    The shape is a smooth sine arch — very different from a pothole.

    Key characteristics
    -------------------
    - BROAD and SMOOTH duration  (~0.8–1.2 s, much longer than a pothole)
    - Structured arch shape on accel_z  (not a sharp spike)
    - Two-hump signature from front + rear axles
    - Slight pitch on gyro_y

    ground_truth_event = 1  (this IS a road surface anomaly)
    """
    sig = _normal_base(n, rng)
    event_mask = np.zeros(n, dtype=int)

    t = np.arange(n) * DT
    t_rel = t - (n // 2) * DT   # time relative to hump centre

    half_width = rng.uniform(0.35, 0.55)     # seconds — half-duration of crossing
    amplitude  = intensity * rng.uniform(2.0, 3.5)   # m/s²

    # Front axle arch: smooth sine arch rising then falling
    front_active = np.abs(t_rel) < half_width
    front_arch   = np.where(
        front_active,
        amplitude * np.sin(np.pi * t_rel / half_width),
        0.0,
    )

    # Rear axle: same arch, slightly smaller, delayed by axle-to-axle spacing
    rear_delay  = rng.uniform(0.20, 0.35)    # seconds — axle separation in time
    t_rear      = t_rel - rear_delay
    rear_active = np.abs(t_rear) < half_width
    rear_arch   = np.where(
        rear_active,
        0.65 * amplitude * np.sin(np.pi * t_rear / half_width),
        0.0,
    )

    sig["az"] += front_arch + rear_arch

    # Pitch: front of bus dips as it descends the back slope
    sig["gy"] += np.where(
        front_active,
        0.04 * amplitude * np.cos(np.pi * t_rel / half_width),
        0.0,
    )

    event_mask[front_active] = 1

    return sig, event_mask


# ─── Rough / broken road patch ────────────────────────────────────────────────

def _rough_road(n, rng, intensity=1.0):
    """
    Simulate driving over a sustained rough or broken road surface.

    Physical model
    --------------
    A broken or potholed road surface excites multiple vibration frequencies
    simultaneously and continuously. Unlike a pothole, there is NO single spike:
    the signal is persistently elevated for several seconds.

    Multiple superimposed frequencies represent:
    - Large cracks / patches  → 4–5 Hz
    - Small bumps / gravel    → 8–15 Hz
    - Surface texture         → 15–20 Hz

    Key characteristics
    -------------------
    - SUSTAINED for the whole section (not a spike)
    - Elevated amplitude across all axes (z most prominent)
    - No clear dominant frequency — broadband / chaotic
    - Gyroscope also shows mild wobble

    ground_truth_event = 1  (the entire rough patch is the event)
    """
    sig = _normal_base(n, rng)

    t = np.arange(n) * DT
    roughness = intensity * rng.uniform(0.6, 1.1)   # controls overall severity

    # Superimpose several vibration frequencies on vertical axis
    for freq, amp_fraction in [(4.0, 0.50), (8.5, 0.40), (14.0, 0.30), (20.0, 0.20)]:
        phase = rng.uniform(0, 2 * np.pi)
        sig["az"] += roughness * amp_fraction * np.sin(2 * np.pi * freq * t + phase)

    # Lateral also gets affected (rough surface pushes wheels sideways)
    for freq, amp_fraction in [(3.5, 0.30), (9.0, 0.20)]:
        phase = rng.uniform(0, 2 * np.pi)
        sig["ax"] += roughness * amp_fraction * 0.4 * np.sin(2 * np.pi * freq * t + phase)

    # Additive broadband noise burst on top of the structured vibration
    sig["az"] += rng.normal(0.0, roughness * 0.35, n)
    sig["ax"] += rng.normal(0.0, roughness * 0.20, n)
    sig["ay"] += rng.normal(0.0, roughness * 0.15, n)

    # Gyroscope shows mild wobble from the irregular surface
    sig["gx"] += rng.normal(0.0, roughness * 0.015, n)
    sig["gy"] += rng.normal(0.0, roughness * 0.012, n)

    # The ENTIRE section is the event
    event_mask = np.ones(n, dtype=int)

    return sig, event_mask


# ─── Braking ──────────────────────────────────────────────────────────────────

def _braking(n, rng, intensity=1.0):
    """
    Simulate the bus decelerating under normal braking.

    Physical model
    --------------
    Braking produces a sustained NEGATIVE longitudinal acceleration on accel_y.
    The force follows a trapezoidal profile: ramps up quickly, holds steady,
    then eases off as the bus slows.

    Key characteristics
    -------------------
    - Long duration  (~3–5 s — much longer than any road impact)
    - PRIMARY effect on accel_y  (longitudinal), NOT accel_z
    - Slight nose-dip: small pitch (gyro_y) and tiny z reduction
    - NO sharp vertical spike  — this is how it differs from a pothole

    ground_truth_event = 0  (vehicle maneuver, NOT a road surface anomaly)
    The future detector must NOT falsely flag braking as a pothole.
    """
    sig = _normal_base(n, rng)

    brake_amp = intensity * rng.uniform(2.5, 4.5)   # m/s² deceleration magnitude

    # Build a trapezoidal brake profile: ramp up → plateau → ease off
    ramp_up  = int(0.3 * SAMPLE_RATE)              # 0.3 s to build up
    ease_off = int(0.6 * SAMPLE_RATE)              # 0.6 s to ease off
    plateau  = max(0, n - ramp_up - ease_off)

    profile = np.concatenate([
        np.linspace(0.0, brake_amp, ramp_up),
        np.full(plateau, brake_amp),
        np.linspace(brake_amp, 0.0, ease_off),
    ])
    profile = profile[:n]   # safety trim to exactly n samples

    sig["ay"] -= profile + rng.normal(0.0, 0.10, n)   # deceleration is negative y

    # Front of bus dips slightly under braking (pitch and small z reduction)
    sig["gy"] += 0.025 * profile
    sig["az"] -= 0.06  * profile + rng.normal(0.0, 0.04, n)

    # NOT a road surface anomaly
    event_mask = np.zeros(n, dtype=int)

    return sig, event_mask


# ─── Turning ──────────────────────────────────────────────────────────────────

def _turning(n, rng, intensity=1.0):
    """
    Simulate the bus turning at a junction.

    Physical model
    --------------
    Turning generates centripetal force felt as LATERAL acceleration (accel_x).
    The bus body also rotates around its vertical axis (yaw — gyro_z)
    and leans slightly into the turn (roll — gyro_x).

    Key characteristics
    -------------------
    - PRIMARY effect on accel_x  (lateral) and gyro_z  (yaw rate)
    - Smooth arch profile: enter turn, peak lateral force, exit turn
    - NO significant vertical spike on accel_z
    - Distinguishable from a pothole/breaker by its axis signature

    ground_truth_event = 0  (vehicle maneuver, NOT a road surface anomaly)
    """
    sig = _normal_base(n, rng)

    t = np.arange(n) * DT
    total_t = n * DT

    turn_amp  = intensity * rng.uniform(1.5, 3.0)   # m/s² peak centripetal
    direction = rng.choice([-1.0, 1.0])              # -1 = left, +1 = right

    # Smooth arch: lateral force builds, peaks at mid-turn, fades out
    turn_profile = turn_amp * np.sin(np.pi * t / total_t)

    sig["ax"] += direction * turn_profile + rng.normal(0.0, 0.06, n)

    # Yaw rate is proportional to the lateral acceleration during a steady turn
    sig["gz"] += direction * 0.12 * turn_profile

    # Mild body roll into the turn (lean)
    sig["gx"] += direction * 0.03 * turn_profile

    # NOT a road surface anomaly
    event_mask = np.zeros(n, dtype=int)

    return sig, event_mask


# ─── Acceleration ─────────────────────────────────────────────────────────────

def _acceleration(n, rng, intensity=1.0):
    """
    Simulate the bus accelerating (e.g. pulling away from a bus stop).

    Physical model
    --------------
    Acceleration produces POSITIVE longitudinal acceleration on accel_y.
    The speed builds up quickly at first then plateaus (exponential approach).
    The bus tail squats slightly under engine torque (slight pitch-back on gyro_y).

    Key characteristics
    -------------------
    - PRIMARY effect on accel_y  (positive, longitudinal)
    - Opposite sign from braking
    - NO significant vertical spike on accel_z
    - Easy to distinguish from road events by axis pattern

    ground_truth_event = 0  (vehicle maneuver, NOT a road surface anomaly)
    """
    sig = _normal_base(n, rng)

    t = np.arange(n) * DT
    total_t = n * DT

    accel_amp = intensity * rng.uniform(1.0, 2.5)   # m/s²

    # Exponential approach: rapid acceleration that levels off
    accel_profile = accel_amp * (1.0 - np.exp(-3.0 * t / total_t))

    sig["ay"] += accel_profile + rng.normal(0.0, 0.07, n)

    # Rear of bus squats: slight pitch-back (nose up)
    sig["gy"] -= 0.015 * accel_profile

    # NOT a road surface anomaly
    event_mask = np.zeros(n, dtype=int)

    return sig, event_mask


# ─── Scenario dispatcher ─────────────────────────────────────────────────────

def _generate_section(scenario, n, rng, intensity=1.0):
    """
    Route the scenario name to the correct signal generator.

    Returns
    -------
    signals    : dict {ax, ay, az, gx, gy, gz}  — numpy float arrays of length n
    event_mask : numpy int array of length n     — 1 = road anomaly, 0 = not
    """
    if scenario == "normal":
        return _normal_base(n, rng), np.zeros(n, dtype=int)
    elif scenario == "pothole":
        return _pothole(n, rng, intensity)
    elif scenario == "speed_breaker":
        return _speed_breaker(n, rng, intensity)
    elif scenario == "rough_road":
        return _rough_road(n, rng, intensity)
    elif scenario == "braking":
        return _braking(n, rng, intensity)
    elif scenario == "turning":
        return _turning(n, rng, intensity)
    elif scenario == "acceleration":
        return _acceleration(n, rng, intensity)
    else:
        raise ValueError(f"Unknown scenario: '{scenario}'")


# ─── GPS helpers ──────────────────────────────────────────────────────────────

def _interpolate_gps(total_samples):
    """
    Linearly interpolate lat/lon along the route waypoints by time.
    The bus travels from the first waypoint to the last over total_samples steps.
    GPS interpolation is by time only (not by true distance), which is a
    deliberate simplification for the hackathon prototype.
    """
    lats = np.array([w[0] for w in WAYPOINTS])
    lons = np.array([w[1] for w in WAYPOINTS])
    t_waypoints = np.linspace(0.0, 1.0, len(WAYPOINTS))
    t_samples   = np.linspace(0.0, 1.0, total_samples)
    return np.interp(t_samples, t_waypoints, lats), np.interp(t_samples, t_waypoints, lons)


def _add_gps_noise(lats, lons, rng):
    """
    Add realistic smartphone GPS noise.
    Smartphone GPS accuracy ≈ 5–15 m  →  ±0.00008° ≈ ±8–9 m.
    Each pass gets independent noise, so GPS tracks differ slightly between passes.
    """
    scale = 0.00008   # degrees
    return (
        lats + rng.normal(0.0, scale, len(lats)),
        lons + rng.normal(0.0, scale, len(lons)),
    )


# ─── Per-pass generation ─────────────────────────────────────────────────────

def generate_pass(pass_id, rng, start_time=0.0):
    """
    Generate one complete bus pass over the route.

    Parameters
    ----------
    pass_id    : integer identifier for this pass (1-based)
    rng        : numpy Generator, seeded independently for each pass
    start_time : timestamp (seconds) of the first sample in this pass

    Returns
    -------
    pandas DataFrame — one row per sample, with all 12 columns.
    """
    records = []
    t = start_time

    for section in ROUTE_SECTIONS:
        scenario = section["scenario"]
        label    = section["label"]
        n        = int(section["duration"] * SAMPLE_RATE)

        # ±20 % intensity variation between passes so signals are not identical
        intensity = rng.uniform(0.80, 1.20)

        signals, event_mask = _generate_section(scenario, n, rng, intensity)

        for i in range(n):
            records.append({
                "timestamp":          round(t, 4),
                "pass_id":            pass_id,
                # lat/lon inserted later (after DataFrame is built)
                "accel_x":            round(float(signals["ax"][i]), 5),
                "accel_y":            round(float(signals["ay"][i]), 5),
                "accel_z":            round(float(signals["az"][i]), 5),
                "gyro_x":             round(float(signals["gx"][i]), 6),
                "gyro_y":             round(float(signals["gy"][i]), 6),
                "gyro_z":             round(float(signals["gz"][i]), 6),
                "ground_truth_event": int(event_mask[i]),
                "ground_truth_type":  label,
            })
            t += DT

    df = pd.DataFrame(records)

    # Insert GPS columns at positions 2 and 3 so the column order matches the spec
    total_n = len(df)
    base_lats, base_lons = _interpolate_gps(total_n)
    lats, lons = _add_gps_noise(base_lats, base_lons, rng)
    df.insert(2, "latitude",  np.round(lats, 6))
    df.insert(3, "longitude", np.round(lons, 6))

    return df


# ─── All passes ───────────────────────────────────────────────────────────────

def generate_all_passes(seed=RANDOM_SEED, n_passes=NUM_PASSES):
    """
    Generate all bus passes and return them as one combined DataFrame.

    Reproducibility
    ---------------
    A master RNG (seeded from 'seed') derives a unique sub-seed for each pass.
    This makes the whole dataset deterministic: running with the same seed
    always produces the same CSV. Change 'seed' to get a different dataset.
    """
    master_rng  = np.random.default_rng(seed)
    all_passes  = []
    current_t   = 0.0

    for pass_id in range(1, n_passes + 1):
        # Each pass gets its own independent RNG so its noise is uncorrelated
        pass_seed = int(master_rng.integers(0, 2**31))
        pass_rng  = np.random.default_rng(pass_seed)

        df_pass = generate_pass(pass_id=pass_id, rng=pass_rng, start_time=current_t)
        all_passes.append(df_pass)
        current_t += TOTAL_DURATION   # next pass starts right after this one

    return pd.concat(all_passes, ignore_index=True)


# ─── Save ─────────────────────────────────────────────────────────────────────

def save_data(df, output_path=OUTPUT_CSV):
    """Save the DataFrame to CSV and print a human-readable summary."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    print(f"\n[ROADPULSE] Dataset saved -> {out}")
    print(f"  Total rows   : {len(df):,}")
    print(f"  Passes       : {df['pass_id'].nunique()}")
    print(f"  Duration/pass: {TOTAL_DURATION:.1f} s  at  {SAMPLE_RATE} Hz")
    print(f"  File size    : {out.stat().st_size / 1024:.1f} KB")
    print(f"  Columns      : {list(df.columns)}")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[ROADPULSE] Generating mock sensor data ...")
    df = generate_all_passes(seed=RANDOM_SEED, n_passes=NUM_PASSES)
    save_data(df)

    print("\n-- First 5 rows --------------------------------------------------")
    print(df.head(5).to_string(index=False))
    print("\n-- ground_truth_type distribution --------------------------------")
    print(df["ground_truth_type"].value_counts().to_string())
    print("\n-- ground_truth_event counts -------------------------------------")
    print(df["ground_truth_event"].value_counts().to_string())
