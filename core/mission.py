# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: clock implementation generated with Claude Code and reviewed by Fran.
"""Simulated mission clock. Owner: Fran.

The current mission time is stored in data/mission_state.json ({"now": ISO time}) so it
survives Streamlit reruns; data/seed/ has the clean copy, so Reset demo restarts the clock.
Without that file the clock is at the mission start (config/mission.json).

Recovery (#77, AGENTS.md 5.5): after a failed detection the file also holds
"unprocessed": [measurement dicts], the revealed rows detection did not finish. The next
advance_and_detect() sends them first; the clock is never rewound and history never replayed.

Simulated measurements with a timestamp after now() stay hidden (core.data.load_measurements)
until advance() reveals them. Contract: AGENTS.md, section 7.
"""
import json
import os
import tempfile
from datetime import datetime, timedelta
from math import isfinite
from numbers import Real

import pandas as pd

from core import models
from core.config import load_mission
from core.models import MEASUREMENT_COLUMNS


def _start() -> datetime:
    return datetime.fromisoformat(load_mission()["start"])


def _state() -> dict:
    path = models.data_file(models.MISSION_STATE_FILE)
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def now() -> datetime:
    """Current simulated mission time."""
    state = _state()
    return datetime.fromisoformat(state["now"]) if "now" in state else _start()


def _unprocessed() -> list[dict]:
    return list(_state().get("unprocessed", []))


def _save(moment: datetime, unprocessed: list[dict] | None = None) -> None:
    """Write the clock (and any unprocessed rows) safely: temporary file, then replace."""
    state = {"now": moment.isoformat(timespec="seconds")}
    if unprocessed:
        state["unprocessed"] = unprocessed
    path = models.data_file(models.MISSION_STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".mission-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _check_hours(hours) -> None:
    try:
        valid = isinstance(hours, Real) and not isinstance(hours, bool) and isfinite(hours) and hours > 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"hours must be a positive number, got {hours!r}")


def _revealed(before: datetime, after: datetime) -> list[dict]:
    """Simulated rows with a timestamp in (before, after], as dicts (AGENTS.md 5.1), by time.

    Read from the measurements file itself, because core.data.load_measurements() hides rows
    after the clock and this is computed before the new clock is saved.
    """
    path = models.data_file(models.MEASUREMENTS_FILE)
    if not path.exists() or path.stat().st_size == 0:
        return []
    df = pd.read_csv(path, dtype={"astronaut": str, "indicator": str, "unit": str,
                                  "phase": str, "source": str})
    if df.empty:
        return []
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    rows = df[(df["source"] == "simulated") & (df["timestamp"] > before) & (df["timestamp"] <= after)]
    items = []
    for row in rows.sort_values("timestamp", kind="stable").to_dict("records"):
        row["timestamp"] = row["timestamp"].isoformat(timespec="seconds")
        row["value"] = float(row["value"])
        items.append({key: row[key] for key in MEASUREMENT_COLUMNS})
    return items


def advance(hours: int = 24) -> list[dict]:
    """Move the clock forward and return the simulated measurements that become visible.

    One dict per measurement (keys = columns of AGENTS.md 5.1), sorted by timestamp.
    The caller passes each one to episodes.on_new_measurement(); advance_and_detect() does it.
    The new time and the revealed rows (as "unprocessed", after any rows already waiting) are
    saved in ONE write, so a revealed row can never be lost before detection has seen it.
    Raises ValueError if hours is not a positive number.
    """
    _check_hours(hours)
    before = now()
    try:
        after = before + timedelta(hours=float(hours))
    except OverflowError:
        raise ValueError("Mission advance exceeds the supported time range.") from None
    revealed = _revealed(before, after)
    _save(after, _unprocessed() + revealed)
    return revealed


def _mark_processed(rows: list[dict]) -> None:
    """Remove these rows from the stored "unprocessed" list; the stored time is kept as it is.

    Nothing is written when none of them is in the list (for example rows given by a caller).
    """
    if not rows:
        return
    state = _state()
    pending = state.get("unprocessed", [])
    removed = False
    for row in rows:
        if row in pending:
            pending.remove(row)
            removed = True
    if removed:
        _save(datetime.fromisoformat(state["now"]) if "now" in state else _start(), pending)


def _detect_in_order(rows: list[dict], environment: str) -> None:
    """Send rows to detection one by one, then remove the processed ones from "unprocessed".

    The file is written once at the end, or as soon as detection raises: then the rows already
    processed are removed, the failing row and every later one stay, and the error propagates,
    so the next advance_and_detect() starts with them (#77). If the process were killed in the
    middle, the whole batch would be sent again, which is safe: detection is idempotent.
    """
    from core import episodes  # here, not at the top: core.episodes imports this module

    done = 0
    try:
        for row in rows:
            episodes.on_new_measurement(row, environment)
            done += 1
    finally:
        _mark_processed(rows[:done])


def advance_and_detect(hours: int, environment: str) -> dict:
    """Advance the clock and send every revealed measurement to episode detection.

    All astronauts, not only the current one (AGENTS.md section 10, rule 1). Rows left
    unprocessed by a failed earlier run are sent first (#77). Returns {"revealed": number of new
    simulated measurements, "new_alerts": ids of the astronauts with an episode opened by this
    call, "recovered": number of leftover rows processed now}. Raises ValueError for bad hours;
    a detection error propagates after saving what is still unprocessed (nothing is skipped).
    """
    from core import data  # here, not at the top: core.data imports this module

    _check_hours(hours)
    astronauts = list(data.load_astronauts()["id"])
    before_episodes = {a: (data.get_open_episode(a) or {}).get("id") for a in astronauts}

    leftovers = _unprocessed()
    _detect_in_order(leftovers, environment)        # a failure here leaves the clock as it was

    revealed = advance(hours)                       # new time + revealed rows in one write
    _detect_in_order(revealed, environment)

    new_alerts = [a for a in astronauts
                  if (data.get_open_episode(a) or {}).get("id") not in (None, before_episodes[a])]
    return {"revealed": len(revealed), "new_alerts": new_alerts, "recovered": len(leftovers)}
