# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Data layer: measurements, baseline, astronauts and episodes. Owner: Rol 4.

Every function below is a STUB with the final signature (see AGENTS.md, section 6).
Stubs return fake data in the right format so the rest of the app can be built.
Rol 4 replaces each body with the real implementation using the files in core/models.py.
"""
import pandas as pd

from core.models import MEASUREMENT_COLUMNS


def load_astronauts() -> pd.DataFrame:
    # STUB (Rol 4): read data/astronauts.csv
    return pd.DataFrame(
        [
            {"id": "a1", "name": "Astronaut A", "role": "Commander"},
            {"id": "a2", "name": "Astronaut B", "role": "Flight engineer"},
            {"id": "a3", "name": "Astronaut C", "role": "Mission specialist"},
        ]
    )


def load_measurements(astronaut=None, indicator=None, phase=None) -> pd.DataFrame:
    # STUB (Rol 4): read data/measurements.csv and filter
    return pd.DataFrame(columns=MEASUREMENT_COLUMNS)


def add_measurement(m: dict) -> None:
    # STUB (Rol 4): append one row to data/measurements.csv
    pass


def get_baseline(astronaut: str, indicator: str) -> dict | None:
    # STUB (Rol 4): mean and std of the preflight measurements
    return None


def z_score(astronaut: str, indicator: str, value: float) -> float | None:
    # STUB (Rol 4): (value - mean) / std using get_baseline
    return None


def latest_values(astronaut: str) -> dict:
    # STUB (Rol 4): {indicator: last value} for this astronaut
    return {}


def load_episodes(astronaut: str | None = None) -> list[dict]:
    # STUB (Rol 4): read "episodes" from data/episodes.json
    return []


def save_episode(episode: dict) -> None:
    # STUB (Rol 4): create or replace by id in data/episodes.json
    pass


def get_open_episode(astronaut: str) -> dict | None:
    # STUB (Rol 4): the episode with status pending_confirmation or active
    return None


def load_pending(astronaut: str | None = None) -> list[dict]:
    # STUB (Rol 4): read "pending" from data/episodes.json
    return []


def save_pending(items: list[dict]) -> None:
    # STUB (Rol 4): replace the whole "pending" list
    pass


def reset_demo() -> None:
    # STUB (Rol 4): copy data/seed/* over data/
    pass
