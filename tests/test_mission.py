# AI-assisted: generated with Claude Code and reviewed by Fran.
"""Mission clock (core/mission.py) and hidden future measurements. Temporary files only."""
import json
from datetime import datetime

import pytest

from core import data, mission, models

START = datetime(2027, 4, 1)  # mission start in config/mission.json


@pytest.fixture
def tmp_files(tmp_path, monkeypatch):
    # raising=False: works before and after MISSION_STATE_FILE exists in core/models.py.
    monkeypatch.setattr(models, "MISSION_STATE_FILE", tmp_path / "mission_state.json", raising=False)
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(mission, "load_mission", lambda: {"start": START.isoformat()})
    return tmp_path


def add(timestamp, value, source="simulated", phase="mission", astronaut="a1"):
    data.add_measurement({"timestamp": timestamp, "astronaut": astronaut, "indicator": "heart_rate",
                          "value": value, "unit": "bpm", "phase": phase, "source": source})


def test_clock_starts_at_mission_start(tmp_files):
    assert mission.now() == START


def test_advance_moves_and_stores_the_clock(tmp_files):
    mission.advance()
    assert mission.now() == datetime(2027, 4, 2)
    mission.advance(hours=3)
    assert mission.now() == datetime(2027, 4, 2, 3)
    stored = json.loads((tmp_files / "mission_state.json").read_text(encoding="utf-8"))
    assert stored == {"now": "2027-04-02T03:00:00"}


@pytest.mark.parametrize("hours", [0, -5, "24", True, None])
def test_advance_rejects_bad_hours(tmp_files, hours):
    with pytest.raises(ValueError):
        mission.advance(hours)
    assert mission.now() == START


def test_future_simulated_measurements_are_hidden(tmp_files):
    add("2027-03-30T08:00:00", 60, phase="preflight")   # past
    add("2027-04-01T08:00:00", 70)                      # mission day 1, still future
    add("2027-04-05T08:00:00", 75, source="manual")     # manual rows are never hidden
    assert list(data.load_measurements()["value"]) == [60.0, 75.0]
    assert data.latest_values("a1") == {"heart_rate": 75.0}
    assert data.get_baseline("a1", "heart_rate")["n"] == 1


def test_advance_returns_only_newly_visible_simulated_rows(tmp_files):
    add("2027-03-30T08:00:00", 60, phase="preflight")
    add("2027-04-01T08:00:00", 70)
    add("2027-04-01T08:00:00", 71, astronaut="a2")
    add("2027-04-02T08:00:00", 72)
    add("2027-04-01T09:00:00", 99, source="manual")

    revealed = mission.advance(hours=24)  # now 2027-04-02T00:00
    assert [(m["astronaut"], m["value"]) for m in revealed] == [("a1", 70.0), ("a2", 71.0)]
    assert revealed[0] == {"timestamp": "2027-04-01T08:00:00", "astronaut": "a1",
                           "indicator": "heart_rate", "value": 70.0, "unit": "bpm",
                           "phase": "mission", "source": "simulated"}
    assert 70.0 in list(data.load_measurements()["value"])

    assert [m["value"] for m in mission.advance(hours=24)] == [72.0]
    assert mission.advance(hours=24) == []


def test_reset_demo_restarts_the_clock(tmp_files, monkeypatch):
    seed = tmp_files / "seed"
    seed.mkdir()
    (seed / "mission_state.json").write_text(json.dumps({"now": START.isoformat()}))
    monkeypatch.setattr(models, "SEED_DIR", seed)
    monkeypatch.setattr(models, "DATA_DIR", tmp_files)
    mission.advance(hours=48)
    data.reset_demo()
    assert mission.now() == START


def test_repository_seed_clock_is_a_midnight_during_the_mission():
    """The generator leaves the seed clock at 00:00 of the demo day (scripts/generate_data.py)."""
    from core.config import load_mission
    seed_file = models.SEED_DIR / "mission_state.json"
    state = json.loads(seed_file.read_text(encoding="utf-8"))
    assert set(state) == {"now"}
    clock = datetime.fromisoformat(state["now"])
    assert clock >= datetime.fromisoformat(load_mission()["start"])
    assert (clock.hour, clock.minute, clock.second) == (0, 0, 0)
