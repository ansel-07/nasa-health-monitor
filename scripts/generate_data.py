# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: generator implementation generated with Claude Code and reviewed by Fran.
"""Generate simulated pre-flight and mission data. Owner: Fran.

Usage (from the repo root):  python -m scripts.generate_data

- One row per measurement, columns of AGENTS.md section 5.1, source "simulated".
- Pre-flight: one measurement per day and indicator for PREFLIGHT_DAYS days before the
  mission start, so every astronaut has a personal baseline.
- Mission: MISSION_DAYS days from the mission start: personal level + daily trend + normal
  noise, plus the anomalies of the demo scenario.
- numpy.random.default_rng(SEED): the same parameters always give the same data.
- Writes data/measurements.csv AND data/seed/measurements.csv (the copy used by Reset demo).
- Also writes mission_state.json in data/ and data/seed/: the clock starts at 00:00 of
  DEMO_DAY, so after Reset demo the earlier mission days are history and ONE "Advance 24 h"
  click reveals the demo anomaly (AGENTS.md sections 5.5 and 15).

SYNTHETIC DEMONSTRATION DATA: the output is a scripted example for the demo, not a model of
real astronaut physiology or of how SANS / muscle atrophy develop over time.

Every health value below is written by Edu (TODO_EDU) and the demo scenario by Gonzalo
(TODO_GONZALO). While any TODO is left, the script refuses to run and lists them.
"""
import json
import sys
from datetime import datetime, timedelta
from numbers import Real

import numpy as np
import pandas as pd

from core import config, models
from core.models import MEASUREMENT_COLUMNS, TODO_MARK

# --- Parameters ------------------------------------------------------------------------------

SEED = 2027
PREFLIGHT_DAYS = 14       # days of pre-flight data per astronaut (enough for a baseline)
MISSION_DAYS = "TODO_EDU"     # simulated mission days (Edu: 10 days is not supported by the sources)
DEMO_DAY = "TODO_GONZALO"     # mission day of the demo anomaly, revealed by one Advance click
MEASURE_HOUR = 8          # every simulated measurement is taken at 08:00

# Health values: one entry per indicator used by SANS and muscle atrophy (config/problems.json).
# Edu (#36): the sources give no daily sd, person_sd or trend for these; never use 0 for unknown.
#   mean:            typical pre-flight value, same method/site as the indicator (its unit)
#   sd:              day-to-day variation of one person (standard deviation)
#   person_sd:       optional, how much the personal level differs between astronauts (default 0)
#   trend_per_day:   optional, average change per mission day (default 0)
#   min / max:       optional, values are clipped to this range
#   decimals:        digits kept when rounding (data format, not a health value)
INDICATOR_PARAMS = {
    # SANS (one indicator per eye, AGENTS.md 5.2: never pool sites)
    "peripapillary_trt_left": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 0},
    "peripapillary_trt_right": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 0},
    "optic_disc_edema_grade_left": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 0},
    "optic_disc_edema_grade_right": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 0},
    "refraction_left": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 2},
    "refraction_right": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 2},
    "visual_acuity_left": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 2},
    "visual_acuity_right": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 2},
    # Muscle atrophy
    "muscle_strength": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 0},
    "muscle_area": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 1},
    "muscle_power": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 0},
    "muscle_endurance": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 0},
    "muscle_tone": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 1},
    "muscle_stiffness": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU", "trend_per_day": "TODO_EDU", "decimals": 0},
}

# Demo scenario (Gonzalo, values reviewed by Edu): on that mission day (1 = first day),
# the simulated value of that indicator is replaced by `value`.
ANOMALIES = [
    {"astronaut": "TODO_GONZALO", "indicator": "TODO_GONZALO", "day": "TODO_GONZALO",
     "value": "TODO_EDU"},
]


# --- Generator -------------------------------------------------------------------------------

def _is_todo(value) -> bool:
    return isinstance(value, str) and value.startswith(TODO_MARK)


def find_todos(indicator_params: dict, anomalies: list, scenario: dict | None = None) -> list[str]:
    """Where a value still starts with TODO, e.g. 'INDICATOR_PARAMS[heart_rate][mean]'.

    scenario: optional single values, e.g. {"MISSION_DAYS": 10, "DEMO_DAY": 4}.
    """
    found = [name for name, value in (scenario or {}).items() if _is_todo(value)]
    for indicator, params in indicator_params.items():
        for key, value in params.items():
            if isinstance(value, str) and value.startswith(TODO_MARK):
                found.append(f"INDICATOR_PARAMS[{indicator}][{key}]")
    for i, anomaly in enumerate(anomalies):
        for key, value in anomaly.items():
            if isinstance(value, str) and value.startswith(TODO_MARK):
                found.append(f"ANOMALIES[{i}][{key}]")
    return found


def check_params(indicator_params: dict, anomalies: list, astronauts: list, units: dict,
                 mission_days: int) -> list[str]:
    """Errors in the parameters (unknown ids, missing or non-numeric values, days out of range)."""
    errors = []

    def is_number(x):
        return isinstance(x, Real) and not isinstance(x, bool)

    for indicator, params in indicator_params.items():
        if indicator not in units:
            errors.append(f"INDICATOR_PARAMS: unknown indicator {indicator!r}")
        for key in ("mean", "sd"):
            if not is_number(params.get(key)):
                errors.append(f"INDICATOR_PARAMS[{indicator}][{key}]: must be a number")
        for key in ("person_sd", "trend_per_day", "min", "max"):
            if key in params and not is_number(params[key]):
                errors.append(f"INDICATOR_PARAMS[{indicator}][{key}]: must be a number")
        for key in ("sd", "person_sd"):
            if is_number(params.get(key)) and params[key] < 0:
                errors.append(f"INDICATOR_PARAMS[{indicator}][{key}]: cannot be negative")
    for i, anomaly in enumerate(anomalies):
        if anomaly.get("astronaut") not in astronauts:
            errors.append(f"ANOMALIES[{i}]: unknown astronaut {anomaly.get('astronaut')!r}")
        if anomaly.get("indicator") not in indicator_params:
            errors.append(f"ANOMALIES[{i}]: indicator {anomaly.get('indicator')!r} is not simulated")
        day = anomaly.get("day")
        if not (isinstance(day, int) and not isinstance(day, bool) and 1 <= day <= mission_days):
            errors.append(f"ANOMALIES[{i}][day]: must be a whole number from 1 to {mission_days}")
        if not is_number(anomaly.get("value")):
            errors.append(f"ANOMALIES[{i}][value]: must be a number")
    return errors


def _is_whole(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def check_scenario(mission_days, demo_day, anomalies: list) -> list[str]:
    """Errors in MISSION_DAYS / DEMO_DAY: whole numbers, and an anomaly on the demo day."""
    if not (_is_whole(mission_days) and mission_days >= 1):
        return ["MISSION_DAYS: must be a whole number of at least 1"]
    if not (_is_whole(demo_day) and 1 <= demo_day <= mission_days):
        return [f"DEMO_DAY: must be a whole number from 1 to {mission_days}"]
    if not any(a.get("day") == demo_day for a in anomalies):
        return [f"DEMO_DAY: no anomaly on mission day {demo_day}, so the demo click would reveal nothing"]
    return []


def seed_clock(start: datetime, demo_day: int) -> datetime:
    """Mission time to leave in the seed: 00:00 of the demo day.

    Mission day d is measured at start + (d - 1) days, MEASURE_HOUR; so days before the demo
    day are already visible, and one 24 h advance reveals exactly the demo day.
    """
    return start.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=demo_day - 1)


def generate(indicator_params: dict, anomalies: list, astronauts: list, units: dict,
             start: datetime, preflight_days: int, mission_days: int, seed: int,
             measure_hour: int = MEASURE_HOUR) -> pd.DataFrame:
    """All simulated measurements, sorted by timestamp, with the columns of AGENTS.md 5.1."""
    rng = np.random.default_rng(seed)
    first_day = start.replace(hour=measure_hour, minute=0, second=0, microsecond=0)
    overrides = {(a["astronaut"], a["indicator"], a["day"]): a["value"] for a in anomalies}
    rows = []
    for astronaut in astronauts:
        for indicator, p in indicator_params.items():
            level = p["mean"] + rng.normal(0, p.get("person_sd", 0))
            trend = p.get("trend_per_day", 0)
            days = [("preflight", d) for d in range(-preflight_days, 0)]
            days += [("mission", d) for d in range(1, mission_days + 1)]
            for phase, day in days:
                value = level + rng.normal(0, p["sd"])
                if phase == "mission":
                    value += trend * day
                    value = overrides.get((astronaut, indicator, day), value)
                value = float(np.clip(value, p.get("min", -np.inf), p.get("max", np.inf)))
                value = round(value, p.get("decimals", 1))
                offset = day if phase == "preflight" else day - 1  # mission day 1 = start date
                rows.append({
                    "timestamp": (first_day + timedelta(days=offset)).isoformat(timespec="seconds"),
                    "astronaut": astronaut, "indicator": indicator, "value": value,
                    "unit": units[indicator], "phase": phase, "source": "simulated",
                })
    df = pd.DataFrame(rows, columns=MEASUREMENT_COLUMNS)
    return df.sort_values(["timestamp", "astronaut", "indicator"], kind="stable").reset_index(drop=True)


def write(df: pd.DataFrame, clock: datetime | None = None) -> list:
    """Write the measurements (and the mission clock, if given) to data/ and data/seed/.

    Scripts run outside the app, so these are the repository files (AGENTS.md 5.5).
    Returns the paths written.
    """
    paths = []
    for path in (models.MEASUREMENTS_FILE, models.SEED_DIR / models.MEASUREMENTS_FILE.name):
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, columns=MEASUREMENT_COLUMNS, lineterminator="\n")
        paths.append(path)
    if clock is not None:
        state = json.dumps({"now": clock.isoformat(timespec="seconds")}, indent=2) + "\n"
        for path in (models.MISSION_STATE_FILE, models.SEED_DIR / models.MISSION_STATE_FILE.name):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(state, encoding="utf-8", newline="\n")
            paths.append(path)
    return paths


def main() -> int:
    todos = find_todos(INDICATOR_PARAMS, ANOMALIES,
                       {"MISSION_DAYS": MISSION_DAYS, "DEMO_DAY": DEMO_DAY})
    if todos:
        print("Cannot generate data yet: these values are still marked TODO "
              "(health values: Edu; demo scenario: Gonzalo):")
        for item in todos:
            print(f"  - {item}")
        return 1

    mission = config.load_mission()
    units = {key: info["unit"] for key, info in config.load_indicators().items()
             if not key.startswith("_")}
    errors = check_scenario(MISSION_DAYS, DEMO_DAY, ANOMALIES)
    if not errors:
        errors = check_params(INDICATOR_PARAMS, ANOMALIES, mission["astronauts"], units, MISSION_DAYS)
    if errors:
        print("Cannot generate data: the parameters have errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    start = datetime.fromisoformat(mission["start"])
    df = generate(INDICATOR_PARAMS, ANOMALIES, mission["astronauts"], units,
                  start, PREFLIGHT_DAYS, MISSION_DAYS, SEED)
    clock = seed_clock(start, DEMO_DAY)
    for path in write(df, clock):
        print(f"Wrote {path}")
    print(f"{len(df)} synthetic demonstration measurements (not a model of real physiology). "
          f"Seed clock: {clock.isoformat()} -> one 'Advance 24 h' reveals mission day {DEMO_DAY}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
