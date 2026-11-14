# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: clock implementation generated with Claude Code and reviewed by Fran.
"""Simulated mission clock. Owner: Fran.

The current mission time is stored in data/mission_state.json ({"now": ISO time}) so it
survives Streamlit reruns; data/seed/ has the clean copy, so Reset demo restarts the clock.
Without that file the clock is at the mission start (config/mission.json).

Simulated measurements with a timestamp after now() stay hidden (core.data.load_measurements)
until advance() reveals them. Contract: AGENTS.md, section 7.
"""
import json
import os
import tempfile
from datetime import datetime, timedelta
from numbers import Real

from core import models
from core.config import load_mission


def _start() -> datetime:
    return datetime.fromisoformat(load_mission()["start"])


def now() -> datetime:
    """Current simulated mission time."""
    path = models.data_file(models.MISSION_STATE_FILE)
    if not path.exists() or path.stat().st_size == 0:
        return _start()
    with path.open(encoding="utf-8") as f:
        return datetime.fromisoformat(json.load(f)["now"])


def _save(moment: datetime) -> None:
    """Write the clock safely: temporary file first, then replace the old one."""
    path = models.data_file(models.MISSION_STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".mission-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"now": moment.isoformat(timespec="seconds")}, f, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def advance(hours: int = 24) -> list[dict]:
    """Move the clock forward and return the simulated measurements that become visible.

    One dict per measurement (keys = columns of AGENTS.md 5.1), sorted by timestamp.
    The caller passes each one to episodes.on_new_measurement(). Raises ValueError if
    hours is not a positive number.
    """
    if not isinstance(hours, Real) or isinstance(hours, bool) or not hours > 0:
        raise ValueError(f"hours must be a positive number, got {hours!r}")
    from core import data  # here, not at the top: core.data imports this module

    before = now()
    after = before + timedelta(hours=hours)
    _save(after)
    df = data.load_measurements()
    revealed = df[(df["source"] == "simulated") & (df["timestamp"] > before) & (df["timestamp"] <= after)]
    items = []
    for row in revealed.to_dict("records"):
        row["timestamp"] = row["timestamp"].isoformat(timespec="seconds")
        row["value"] = float(row["value"])
        items.append(row)
    return items
