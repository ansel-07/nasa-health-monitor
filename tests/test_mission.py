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
    data.add_measurement({"timestamp": timestamp, "astronaut": astronaut, "indicator": "_example_indicator",
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


@pytest.mark.parametrize("hours", [0, -5, "24", True, None, float("inf"), float("nan"), 1e300])
def test_advance_rejects_bad_hours(tmp_files, hours):
    with pytest.raises(ValueError):
        mission.advance(hours)
    assert mission.now() == START


def test_future_simulated_measurements_are_hidden(tmp_files):
    add("2027-03-30T08:00:00", 60, phase="preflight")   # past
    add("2027-04-01T08:00:00", 70)                      # mission day 1, still future
    add("2027-04-05T08:00:00", 75, source="manual")     # manual rows are never hidden
    assert list(data.load_measurements()["value"]) == [60.0, 75.0]
    assert data.latest_values("a1") == {"_example_indicator": 75.0}
    assert data.get_baseline("a1", "_example_indicator")["n"] == 1


def test_advance_returns_only_newly_visible_simulated_rows(tmp_files):
    add("2027-03-30T08:00:00", 60, phase="preflight")
    add("2027-04-01T08:00:00", 70)
    add("2027-04-01T08:00:00", 71, astronaut="a2")
    add("2027-04-02T08:00:00", 72)
    add("2027-04-01T09:00:00", 99, source="manual")

    revealed = mission.advance(hours=24)  # now 2027-04-02T00:00
    assert [(m["astronaut"], m["value"]) for m in revealed] == [("a1", 70.0), ("a2", 71.0)]
    assert revealed[0] == {"timestamp": "2027-04-01T08:00:00", "astronaut": "a1",
                           "indicator": "_example_indicator", "value": 70.0, "unit": "bpm",
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


# --- advance_and_detect (issue #58) ---------------------------------------------------------

@pytest.fixture
def crew(tmp_files, monkeypatch):
    """Two astronauts, empty episodes, and a fake detection that opens an episode above 80."""
    (tmp_files / "astronauts.csv").write_text("id,name,role\na1,A,Commander\na2,B,Engineer\n")
    monkeypatch.setattr(models, "ASTRONAUTS_FILE", tmp_files / "astronauts.csv")
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_files / "episodes.json")
    calls = []

    def on_new(measurement, environment):
        calls.append((measurement["astronaut"], measurement["value"], environment))
        if measurement["value"] > 80:
            data.save_episode({"id": f"ep-{len(calls)}", "astronaut": measurement["astronaut"],
                               "problem": "p", "status": "pending_confirmation"})

    from core import episodes
    monkeypatch.setattr(episodes, "on_new_measurement", on_new)
    return calls


def test_advance_and_detect_sends_every_revealed_row(crew):
    add("2027-03-30T08:00:00", 60, phase="preflight")   # history: never sent
    add("2027-04-01T08:00:00", 61)
    add("2027-04-01T08:00:00", 90, astronaut="a2")
    add("2027-04-02T08:00:00", 95)                      # next day: not yet
    result = mission.advance_and_detect(24, "mars")
    assert result == {"revealed": 2, "new_alerts": ["a2"], "recovered": 0}
    assert crew == [("a1", 61.0, "mars"), ("a2", 90.0, "mars")]
    assert mission.now() == datetime(2027, 4, 2)

    assert mission.advance_and_detect(24, "iss") == {"revealed": 1, "new_alerts": ["a1"], "recovered": 0}
    assert crew[-1] == ("a1", 95.0, "iss")


def test_advance_and_detect_ignores_episodes_already_open(crew):
    data.save_episode({"id": "ep-old", "astronaut": "a1", "problem": "p", "status": "active"})
    add("2027-04-01T08:00:00", 61)
    assert mission.advance_and_detect(24, "mars") == {"revealed": 1, "new_alerts": [], "recovered": 0}


def test_advance_and_detect_with_nothing_to_reveal(crew):
    assert mission.advance_and_detect(12, "mars") == {"revealed": 0, "new_alerts": [], "recovered": 0}
    assert mission.now() == datetime(2027, 4, 1, 12)
    assert crew == []


def test_advance_and_detect_rejects_bad_hours(crew):
    with pytest.raises(ValueError):
        mission.advance_and_detect(0, "mars")
    assert mission.now() == START


def test_advance_and_detect_lets_detection_errors_through(crew, monkeypatch):
    from core import episodes

    def broken(measurement, environment):
        raise KeyError("missing config")

    monkeypatch.setattr(episodes, "on_new_measurement", broken)
    add("2027-04-01T08:00:00", 61)
    with pytest.raises(KeyError):
        mission.advance_and_detect(24, "mars")


# --- recovery after a failed detection (issue #77) -------------------------------------------

def stored_state(tmp_files):
    return json.loads((tmp_files / "mission_state.json").read_text(encoding="utf-8"))


def fail_on(calls_to_fail, monkeypatch, after_processing=False):
    """Wrap the current detection so the given call numbers (1-based) raise OSError once."""
    from core import episodes
    real = episodes.on_new_measurement
    seen = {"n": 0}

    def flaky(measurement, environment):
        seen["n"] += 1
        if seen["n"] in calls_to_fail and not after_processing:
            raise OSError("synthetic storage failure")
        real(measurement, environment)
        if seen["n"] in calls_to_fail and after_processing:
            raise OSError("synthetic failure after the row was processed")

    monkeypatch.setattr(episodes, "on_new_measurement", flaky)


def day1_rows():
    add("2027-04-01T08:00:00", 61)
    add("2027-04-01T08:00:00", 90, astronaut="a2")
    add("2027-04-02T08:00:00", 95)


def test_failure_before_the_first_row_keeps_every_revealed_row(crew, tmp_files, monkeypatch):
    day1_rows()
    fail_on({1}, monkeypatch)
    with pytest.raises(OSError):
        mission.advance_and_detect(24, "mars")
    assert mission.now() == datetime(2027, 4, 2)               # the clock moved...
    state = stored_state(tmp_files)
    assert [(m["astronaut"], m["value"]) for m in state["unprocessed"]] == [("a1", 61.0), ("a2", 90.0)]
    assert crew == []                                           # ...but nothing was processed

    result = mission.advance_and_detect(24, "mars")             # detection works again
    assert result == {"revealed": 1, "new_alerts": ["a1", "a2"], "recovered": 2}
    assert crew == [("a1", 61.0, "mars"), ("a2", 90.0, "mars"), ("a1", 95.0, "mars")]
    assert "unprocessed" not in stored_state(tmp_files)
    assert mission.now() == datetime(2027, 4, 3)


def test_failure_mid_batch_keeps_only_the_rest(crew, tmp_files, monkeypatch):
    day1_rows()
    fail_on({2}, monkeypatch)
    with pytest.raises(OSError):
        mission.advance_and_detect(24, "mars")
    assert crew == [("a1", 61.0, "mars")]                       # first row done once
    assert [m["value"] for m in stored_state(tmp_files)["unprocessed"]] == [90.0]

    assert mission.advance_and_detect(24, "mars")["recovered"] == 1
    assert crew == [("a1", 61.0, "mars"), ("a2", 90.0, "mars"), ("a1", 95.0, "mars")]  # no repeats


def test_failure_on_leftovers_does_not_advance_again(crew, tmp_files, monkeypatch):
    day1_rows()
    fail_on({1, 2}, monkeypatch)
    with pytest.raises(OSError):
        mission.advance_and_detect(24, "mars")                  # fails on call 1
    with pytest.raises(OSError):
        mission.advance_and_detect(24, "mars")                  # leftover fails again (call 2)
    assert mission.now() == datetime(2027, 4, 2)                # no second advance
    assert len(stored_state(tmp_files)["unprocessed"]) == 2


def test_bad_hours_never_touch_the_leftovers(crew, tmp_files, monkeypatch):
    day1_rows()
    fail_on({1}, monkeypatch)
    with pytest.raises(OSError):
        mission.advance_and_detect(24, "mars")
    with pytest.raises(ValueError):
        mission.advance_and_detect(0, "mars")
    assert len(stored_state(tmp_files)["unprocessed"]) == 2


def test_advance_alone_marks_revealed_rows_as_unprocessed(crew, tmp_files):
    day1_rows()
    revealed = mission.advance(24)
    assert stored_state(tmp_files)["unprocessed"] == revealed
    assert mission.advance_and_detect(24, "mars")["recovered"] == 2   # nothing is skipped


def test_reset_demo_clears_unprocessed_rows(crew, tmp_files, monkeypatch):
    seed = tmp_files / "seed"
    seed.mkdir()
    (seed / "mission_state.json").write_text(json.dumps({"now": START.isoformat()}))
    monkeypatch.setattr(models, "SEED_DIR", seed)
    monkeypatch.setattr(models, "DATA_DIR", tmp_files)
    day1_rows()
    mission.advance(24)
    data.reset_demo()
    assert stored_state(tmp_files) == {"now": START.isoformat()}


def test_replaying_a_processed_row_with_real_detection_creates_no_duplicates(tmp_files, monkeypatch):
    """Crash AFTER a row was processed: the recovery re-sends it; the real episodes code must
    not duplicate the CSV row, the episode or pending items (synthetic values, not clinical)."""
    from core import episodes
    (tmp_files / "astronauts.csv").write_text("id,name,role\na1,A,Commander\n")
    monkeypatch.setattr(models, "ASTRONAUTS_FILE", tmp_files / "astronauts.csv")
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_files / "episodes.json")
    def trt(timestamp, value, phase):
        data.add_measurement({"timestamp": timestamp, "astronaut": "a1", "indicator": "peripapillary_trt_left",
                              "value": value, "unit": "µm", "phase": phase, "source": "simulated"})
    for day, value in ((28, 298), (29, 300), (30, 302)):     # synthetic baseline 300 ± 2
        trt(f"2027-03-{day}T08:00:00", value, "preflight")
    trt("2027-04-01T08:00:00", 360, "mission")                # synthetic +60 above it
    fail_on({1}, monkeypatch, after_processing=True)
    with pytest.raises(OSError):
        mission.advance_and_detect(24, "mars")
    rows_after_first = len(data.load_measurements())
    episodes_after_first = data.load_episodes()
    pending_after_first = data.load_pending()
    assert len(episodes_after_first) == 1                     # the real detection opened it

    assert mission.advance_and_detect(24, "mars")["recovered"] == 1   # the row is sent again
    assert len(data.load_measurements()) == rows_after_first
    assert data.load_episodes() == episodes_after_first
    assert data.load_pending() == pending_after_first
