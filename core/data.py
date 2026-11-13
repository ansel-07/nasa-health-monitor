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
