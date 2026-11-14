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

Every health value below is written by Edu (TODO_EDU) and the demo scenario by Gonzalo
(TODO_GONZALO). While any TODO is left, the script refuses to run and lists them.
"""
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
MISSION_DAYS = 10         # simulated mission days
MEASURE_HOUR = 8          # every simulated measurement is taken at 08:00

# Health values: one entry per indicator to simulate (keys of config/indicators.json).
#   mean:            typical value for a healthy adult (unit of config/indicators.json)
#   sd:              day-to-day variation of one person (standard deviation)
#   person_sd:       optional, how much the personal level differs between astronauts (default 0)
#   trend_per_day:   optional, average change per mission day (default 0)
#   min / max:       optional, values are clipped to this range
#   decimals:        digits kept when rounding (data format, not a health value)
INDICATOR_PARAMS = {
    "heart_rate":   {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU",
                     "trend_per_day": "TODO_EDU", "decimals": 0},
    "bp_systolic":  {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU",
                     "trend_per_day": "TODO_EDU", "decimals": 0},
    "bp_diastolic": {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU",
                     "trend_per_day": "TODO_EDU", "decimals": 0},
    "glucose":      {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU",
                     "trend_per_day": "TODO_EDU", "decimals": 0},
    "temperature":  {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU",
                     "trend_per_day": "TODO_EDU", "decimals": 1},
    "sleep_hours":  {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU",
                     "trend_per_day": "TODO_EDU", "decimals": 1},
    "mood":         {"mean": "TODO_EDU", "sd": "TODO_EDU", "person_sd": "TODO_EDU",
                     "trend_per_day": "TODO_EDU", "min": 1, "max": 5, "decimals": 0},
}

# Demo scenario (Gonzalo, values reviewed by Edu): on that mission day (1 = first day),
# the simulated value of that indicator is replaced by `value`.
ANOMALIES = [
    {"astronaut": "TODO_GONZALO", "indicator": "TODO_GONZALO", "day": "TODO_GONZALO",
     "value": "TODO_EDU"},
]


# --- Generator -------------------------------------------------------------------------------

def find_todos(indicator_params: dict, anomalies: list) -> list[str]:
    """Where a value still starts with TODO, e.g. 'INDICATOR_PARAMS[heart_rate][mean]'."""
    found = []
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


def write(df: pd.DataFrame) -> list:
    """Write the measurements to data/ and data/seed/; returns the paths written."""
    paths = [models.MEASUREMENTS_FILE, models.SEED_DIR / models.MEASUREMENTS_FILE.name]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False, columns=MEASUREMENT_COLUMNS, lineterminator="\n")
    return paths


def main() -> int:
    todos = find_todos(INDICATOR_PARAMS, ANOMALIES)
    if todos:
        print("Cannot generate data yet: these values are still marked TODO "
              "(health values: Edu; demo scenario: Gonzalo):")
        for item in todos:
            print(f"  - {item}")
        return 1

    mission = config.load_mission()
    units = {key: info["unit"] for key, info in config.load_indicators().items()
             if not key.startswith("_")}
    errors = check_params(INDICATOR_PARAMS, ANOMALIES, mission["astronauts"], units, MISSION_DAYS)
    if errors:
        print("Cannot generate data: the parameters have errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    df = generate(INDICATOR_PARAMS, ANOMALIES, mission["astronauts"], units,
                  datetime.fromisoformat(mission["start"]), PREFLIGHT_DAYS, MISSION_DAYS, SEED)
    for path in write(df):
        print(f"Wrote {len(df)} measurements to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
