# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Each Streamlit session works on its own copy of data/seed/ (AGENTS.md, section 5.5)."""
import os
import time

import pytest

from core import data, mission, models


@pytest.fixture
def sessions(tmp_path, monkeypatch):
    """Session data on, with a fake seed and a switchable fake session id."""
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "measurements.csv").write_text(",".join(models.MEASUREMENT_COLUMNS) + "\n", encoding="utf-8")
    (seed / "episodes.json").write_text('{"episodes": [], "pending": []}\n', encoding="utf-8")
    (seed / "mission_state.json").write_text('{"now": "2027-04-01T00:00:00"}\n', encoding="utf-8")
    monkeypatch.setattr(models, "SESSION_DATA", True)
    monkeypatch.setattr(models, "SEED_DIR", seed)
    monkeypatch.setattr(models, "SESSIONS_DIR", tmp_path / "sessions")
    current = {"id": "browser-a"}
    monkeypatch.setattr(models, "_session_id", lambda: current["id"])
    return current


def measurement(value):
    return {"timestamp": "2027-04-01T08:00:00", "astronaut": "a1", "indicator": "_example_indicator",
            "value": value, "unit": "units", "phase": "mission", "source": "manual"}


def test_outside_the_app_paths_are_unchanged(monkeypatch):
    monkeypatch.setattr(models, "SESSION_DATA", True)
    monkeypatch.setattr(models, "_session_id", lambda: None)
    assert models.data_dir() == models.DATA_DIR
    assert models.data_file(models.MEASUREMENTS_FILE) == models.MEASUREMENTS_FILE


def test_new_session_starts_from_a_copy_of_the_seed(sessions):
    folder = models.data_dir()
    assert folder == models.SESSIONS_DIR / "browser-a"
    assert sorted(p.name for p in folder.iterdir()) == ["episodes.json", "measurements.csv", "mission_state.json"]
    assert models.data_file(models.EPISODES_FILE) == folder / "episodes.json"


def test_sessions_do_not_see_each_other(sessions):
    data.add_measurement(measurement(12))
    mission.advance(24)
    assert len(data.load_measurements()) == 1
    sessions["id"] = "browser-b"
    assert data.load_measurements().empty
    assert mission.now().isoformat() == "2027-04-01T00:00:00"
    sessions["id"] = "browser-a"
    assert len(data.load_measurements()) == 1


def test_reset_demo_only_resets_the_current_session(sessions):
    data.add_measurement(measurement(12))
    sessions["id"] = "browser-b"
    data.add_measurement(measurement(13))
    data.reset_demo()
    assert data.load_measurements().empty
    sessions["id"] = "browser-a"
    assert len(data.load_measurements()) == 1


def test_the_seed_and_data_folders_are_never_written(sessions):
    before = {p.name: p.read_text(encoding="utf-8") for p in models.SEED_DIR.iterdir()}
    data.add_measurement(measurement(12))
    mission.advance(24)
    assert {p.name: p.read_text(encoding="utf-8") for p in models.SEED_DIR.iterdir()} == before


def test_old_sessions_are_removed_when_a_new_one_starts(sessions):
    models.data_dir()
    old = models.SESSIONS_DIR / "browser-a"
    stale = time.time() - (models.SESSION_MAX_AGE_HOURS + 1) * 3600
    os.utime(old, (stale, stale))
    sessions["id"] = "browser-b"
    models.data_dir()
    assert not old.exists()
    assert (models.SESSIONS_DIR / "browser-b").is_dir()
