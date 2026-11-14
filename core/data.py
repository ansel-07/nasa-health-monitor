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


def _read_episodes_file() -> dict:
    """Whole content of data/episodes.json; empty lists if the file is missing or empty."""
    import json

    from core import models

    path = models.EPISODES_FILE
    if not path.exists() or path.stat().st_size == 0:
        return {"episodes": [], "pending": []}
    with path.open(encoding="utf-8") as f:
        content = json.load(f)
    content.setdefault("episodes", [])
    content.setdefault("pending", [])
    return content


def _write_episodes_file(content: dict) -> None:
    """Write data/episodes.json safely: temporary file first, then replace the old one."""
    import json
    import os
    import tempfile

    from core import models

    path = models.EPISODES_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".episodes-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def load_episodes(astronaut: str | None = None) -> list[dict]:
    """Episodes from data/episodes.json, in stored order; only this astronaut's if given."""
    episodes = _read_episodes_file()["episodes"]
    if astronaut is not None:
        episodes = [e for e in episodes if e.get("astronaut") == astronaut]
    return episodes


def save_episode(episode: dict) -> None:
    """Create the episode, or replace the stored one with the same id (keeps its position)."""
    if not episode.get("id"):
        raise ValueError("Episode has no 'id'")
    content = _read_episodes_file()
    episodes = content["episodes"]
    for i, stored in enumerate(episodes):
        if stored.get("id") == episode["id"]:
            episodes[i] = episode
            break
    else:
        episodes.append(episode)
    _write_episodes_file(content)


def get_open_episode(astronaut: str) -> dict | None:
    """The astronaut's episode with status pending_confirmation or active, or None.

    There should be at most one (AGENTS.md 10.3); if there are several, the latest stored wins.
    """
    from core.models import OPEN_STATUSES

    open_episodes = [e for e in load_episodes(astronaut) if e.get("status") in OPEN_STATUSES]
    return open_episodes[-1] if open_episodes else None


def load_pending(astronaut: str | None = None) -> list[dict]:
    """Pending triggers from data/episodes.json; only this astronaut's if given."""
    pending = _read_episodes_file()["pending"]
    if astronaut is not None:
        pending = [p for p in pending if p.get("astronaut") == astronaut]
    return pending


def save_pending(items: list[dict]) -> None:
    """Replace the WHOLE pending list (every astronaut), keeping the episodes untouched."""
    content = _read_episodes_file()
    content["pending"] = list(items)
    _write_episodes_file(content)


def reset_demo() -> None:
    # STUB (Fran): copy data/seed/* over data/
    pass
