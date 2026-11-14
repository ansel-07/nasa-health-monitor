# AI-assisted: generated with Claude Code and reviewed by Fran.
"""Caches that make "Advance mission 24 h" fast (docs/CODE_REVIEW.md PERF-1, PERF-5).

They must never change a result: same data, same clock -> same answers as without a cache.
Temporary files and synthetic values only.
"""
import json
from datetime import datetime

import pandas as pd
import pytest

from core import data, episodes, mission, models

START = datetime(2027, 4, 1)
HEADER = "timestamp,astronaut,indicator,value,unit,phase,source\n"


@pytest.fixture
def files(tmp_path, monkeypatch):
    for name in ("MEASUREMENTS_FILE", "MISSION_STATE_FILE", "EPISODES_FILE", "ASTRONAUTS_FILE"):
        monkeypatch.setattr(models, name, tmp_path / getattr(models, name).name)
    monkeypatch.setattr(mission, "load_mission", lambda: {"start": START.isoformat()})
    (tmp_path / "astronauts.csv").write_text("id,name,role\na1,A,Commander\na2,B,Engineer\n")
    return tmp_path


def write_rows(folder, rows):
    (folder / "measurements.csv").write_text(HEADER + "".join(f"{r}\n" for r in rows), encoding="utf-8")


def test_same_size_rewrite_is_never_served_from_the_cache(files):
    """Two writes of the same size can share a modification time on Windows: the cache uses
    the content, so the second version is always read."""
    write_rows(files, ["2027-03-30T08:00:00,a1,_example_indicator,61,u,preflight,simulated"])
    assert list(data.load_measurements()["value"]) == [61.0]
    write_rows(files, ["2027-03-30T08:00:00,a1,_example_indicator,62,u,preflight,simulated"])
    assert list(data.load_measurements()["value"]) == [62.0]


def test_appending_a_measurement_is_seen_at_once(files):
    data.add_measurement({"timestamp": "2027-03-30T08:00:00", "astronaut": "a1",
                          "indicator": "_example_indicator", "value": 60, "unit": "u",
                          "phase": "preflight", "source": "simulated"})
    assert len(data.load_measurements()) == 1
    data.add_measurement({"timestamp": "2027-03-31T08:00:00", "astronaut": "a1",
                          "indicator": "_example_indicator", "value": 64, "unit": "u",
                          "phase": "preflight", "source": "simulated"})
    assert len(data.load_measurements()) == 2
    assert data.get_baseline("a1", "_example_indicator") == {"mean": 62.0, "std": pytest.approx(2.8284271), "n": 2}


def test_changing_a_returned_table_does_not_change_the_cache(files):
    write_rows(files, ["2027-03-30T08:00:00,a1,_example_indicator,61,u,preflight,simulated"])
    first = data.load_measurements()
    first.loc[0, "value"] = 999.0
    del first["unit"]
    again = data.load_measurements()
    assert list(again["value"]) == [61.0] and "unit" in again.columns


def test_changing_a_returned_baseline_does_not_change_the_cache(files):
    write_rows(files, ["2027-03-29T08:00:00,a1,_example_indicator,60,u,preflight,simulated",
                       "2027-03-30T08:00:00,a1,_example_indicator,64,u,preflight,simulated"])
    data.get_baseline("a1", "_example_indicator")["mean"] = -1
    assert data.get_baseline("a1", "_example_indicator")["mean"] == 62.0


def test_baseline_follows_the_mission_clock(files):
    """A simulated pre-flight row after the clock is hidden; once the clock reaches it, the
    baseline must include it (the clock is part of the cache key)."""
    write_rows(files, ["2027-03-30T08:00:00,a1,_example_indicator,60,u,preflight,simulated",
                       "2027-03-31T08:00:00,a1,_example_indicator,64,u,preflight,simulated",
                       "2027-04-01T08:00:00,a1,_example_indicator,80,u,preflight,simulated"])
    assert data.get_baseline("a1", "_example_indicator")["n"] == 2      # clock at the start
    mission.advance(24)
    assert data.get_baseline("a1", "_example_indicator") == {
        "mean": 68.0, "std": pytest.approx(10.583005), "n": 3}


def test_one_advance_parses_the_measurements_file_a_few_times_only(files, monkeypatch):
    """Guard against PERF-1 coming back: with the real demo seed (42 rows revealed, real SANS
    and muscle atrophy rules) one advance used to parse the CSV 537 times."""
    import shutil
    shutil.copyfile(models.SEED_DIR / "measurements.csv", files / "measurements.csv")
    from core import config
    monkeypatch.setattr(mission, "load_mission", config.load_mission)   # the seed's real start
    calls = {"n": 0}
    original = pd.read_csv

    def counting(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(pd, "read_csv", counting)
    result = mission.advance_and_detect(24, "mars")
    assert result["revealed"] == 42
    assert calls["n"] <= 10, calls["n"]


def test_the_clock_file_is_written_once_per_batch(files, monkeypatch):
    """PERF-5: processed rows are removed in one write at the end, not one write per row."""
    write_rows(files, [f"2027-04-01T08:00:00,a1,_example_indicator,{60 + i},u,mission,simulated"
                       for i in range(5)] + ["2027-04-01T08:00:00,a2,_example_indicator,70,u,mission,simulated"])
    monkeypatch.setattr(episodes, "on_new_measurement", lambda m, env: None)
    writes = {"n": 0}
    original = mission._save

    def counting(*args, **kwargs):
        writes["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(mission, "_save", counting)
    assert mission.advance_and_detect(24, "mars")["revealed"] == 6
    assert writes["n"] == 2          # the advance itself, then one write of the processed rows
    state = json.loads((files / "mission_state.json").read_text(encoding="utf-8"))
    assert "unprocessed" not in state


def test_caches_are_safe_with_many_sessions_in_threads(tmp_path, monkeypatch):
    """Streamlit serves each browser session in a thread, each with its own data file. More
    files than the cache holds forces evictions while other threads read."""
    import threading
    monkeypatch.setattr(mission, "now", lambda: START)
    paths = []
    for i in range(data._PARSED_MAX + 16):
        folder = tmp_path / f"session{i}"
        folder.mkdir()
        write_rows(folder, [f"2027-03-29T08:00:00,a1,_example_indicator,{60 + i},u,preflight,simulated",
                            f"2027-03-30T08:00:00,a1,_example_indicator,{62 + i},u,preflight,simulated"])
        paths.append(folder / "measurements.csv")
    errors, current = [], threading.local()
    monkeypatch.setattr(models, "data_file", lambda default: getattr(current, "path", default))

    def session(path, expected_mean):
        current.path = path
        try:
            for _ in range(5):
                assert data.get_baseline("a1", "_example_indicator")["mean"] == expected_mean
                assert len(data.load_measurements()) == 2
        except BaseException as error:   # collected and reported by the main thread
            errors.append(error)

    threads = [threading.Thread(target=session, args=(path, 61.0 + i)) for i, path in enumerate(paths)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert len(data._PARSED) <= data._PARSED_MAX and len(data._BASELINES) <= data._PARSED_MAX
