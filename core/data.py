# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Data layer: measurements, baseline, astronauts and episodes. Owner: Fran.

Every function below is a STUB with the final signature (see AGENTS.md, section 6).
Stubs return fake data in the right format so the rest of the app can be built.
Fran replaces each body with the real implementation using the files in core/models.py.
"""
import pandas as pd

from core.models import MEASUREMENT_COLUMNS


def load_astronauts() -> pd.DataFrame:
    # STUB (Fran): read data/astronauts.csv
    return pd.DataFrame(
        [
            {"id": "a1", "name": "Astronaut A", "role": "Commander"},
            {"id": "a2", "name": "Astronaut B", "role": "Flight engineer"},
            {"id": "a3", "name": "Astronaut C", "role": "Mission specialist"},
        ]
    )


def load_measurements(astronaut=None, indicator=None, phase=None) -> pd.DataFrame:
    # STUB (Fran): read data/measurements.csv and filter
    return pd.DataFrame(columns=MEASUREMENT_COLUMNS)


def add_measurement(m: dict) -> None:
    # STUB (Fran): append one row to data/measurements.csv
    pass


def get_baseline(astronaut: str, indicator: str) -> dict | None:
    # STUB (Fran): mean and std of the preflight measurements
    return None


def z_score(astronaut: str, indicator: str, value: float) -> float | None:
    # STUB (Fran): (value - mean) / std using get_baseline
    return None


def latest_values(astronaut: str) -> dict:
    # STUB (Fran): {indicator: last value} for this astronaut
    return {}


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
