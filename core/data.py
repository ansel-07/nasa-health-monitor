# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Data layer: measurements, baseline, astronauts and episodes. Owner: Fran.

Signatures are fixed by AGENTS.md, section 7. Functions still marked STUB return fake
data in the right format so the rest of the app can be built.
File paths always come from core.models (read at call time, so tests can redirect them).
"""
import csv

import pandas as pd

from core import models
from core.config import load_indicators
from core.models import MEASUREMENT_COLUMNS, PHASES, SOURCES

ASTRONAUT_COLUMNS = ["id", "name", "role"]


def _empty_measurements() -> pd.DataFrame:
    df = pd.DataFrame(columns=MEASUREMENT_COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["value"] = df["value"].astype(float)
    return df


def load_astronauts() -> pd.DataFrame:
    """All astronauts from data/astronauts.csv (columns: id, name, role)."""
    path = models.ASTRONAUTS_FILE
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=ASTRONAUT_COLUMNS)
    return pd.read_csv(path, dtype=str)[ASTRONAUT_COLUMNS]


def load_measurements(astronaut=None, indicator=None, phase=None) -> pd.DataFrame:
    """Measurements from data/measurements.csv, filtered and sorted by timestamp.

    Each filter is ignored when it is None. `timestamp` is a datetime and `value` a float.
    """
    path = models.MEASUREMENTS_FILE
    if not path.exists() or path.stat().st_size == 0:
        return _empty_measurements()
    df = pd.read_csv(path, dtype={"astronaut": str, "indicator": str, "unit": str,
                                  "phase": str, "source": str})
    if df.empty:
        return _empty_measurements()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["value"] = df["value"].astype(float)
    if astronaut is not None:
        df = df[df["astronaut"] == astronaut]
    if indicator is not None:
        df = df[df["indicator"] == indicator]
    if phase is not None:
        df = df[df["phase"] == phase]
    return df.sort_values("timestamp", kind="stable").reset_index(drop=True)


def add_measurement(m: dict) -> None:
    """Append one measurement (keys = columns of AGENTS.md 5.1) to data/measurements.csv.

    Raises ValueError if a column is missing or a value is not allowed.
    """
    missing = [c for c in MEASUREMENT_COLUMNS if c not in m]
    if missing:
        raise ValueError(f"Measurement is missing columns: {missing}")
    if m["indicator"] not in load_indicators():
        raise ValueError(f"Unknown indicator: {m['indicator']!r}")
    if m["phase"] not in PHASES:
        raise ValueError(f"Unknown phase: {m['phase']!r} (expected one of {PHASES})")
    if m["source"] not in SOURCES:
        raise ValueError(f"Unknown source: {m['source']!r} (expected one of {SOURCES})")
    try:
        value = float(m["value"])
    except (TypeError, ValueError):
        raise ValueError(f"Value is not a number: {m['value']!r}") from None

    row = dict(m, value=value)
    timestamp = row["timestamp"]
    if hasattr(timestamp, "isoformat"):
        row["timestamp"] = timestamp.isoformat(timespec="seconds")

    path = models.MEASUREMENTS_FILE
    write_header = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MEASUREMENT_COLUMNS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def get_baseline(astronaut: str, indicator: str) -> dict | None:
    # STUB (Fran): mean and std of the preflight measurements
    return None


def z_score(astronaut: str, indicator: str, value: float) -> float | None:
    # STUB (Fran): (value - mean) / std using get_baseline
    return None


def latest_values(astronaut: str) -> dict:
    """{indicator: last value} for this astronaut (latest timestamp wins)."""
    df = load_measurements(astronaut=astronaut)
    if df.empty:
        return {}
    last = df.groupby("indicator", sort=False).tail(1)
    return {row.indicator: float(row.value) for row in last.itertuples()}


def load_episodes(astronaut: str | None = None) -> list[dict]:
    # STUB (Fran): read "episodes" from data/episodes.json
    return []


def save_episode(episode: dict) -> None:
    # STUB (Fran): create or replace by id in data/episodes.json
    pass


def get_open_episode(astronaut: str) -> dict | None:
    # STUB (Fran): the episode with status pending_confirmation or active
    return None


def load_pending(astronaut: str | None = None) -> list[dict]:
    # STUB (Fran): read "pending" from data/episodes.json
    return []


def save_pending(items: list[dict]) -> None:
    # STUB (Fran): replace the whole "pending" list
    pass


def reset_demo() -> None:
    # STUB (Fran): copy data/seed/* over data/
    pass
