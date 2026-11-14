# AI-assisted: generated with Claude Code and reviewed by Fran.
"""scripts/generate_data.py. Every number here is a FAKE test value, not health content."""
import json
from datetime import datetime

import pandas as pd
import pytest

from core import data, models
from core.models import MEASUREMENT_COLUMNS
from scripts import generate_data as gen

UNITS = {"x": "u", "y": "v"}
PARAMS = {"x": {"mean": 100, "sd": 5, "person_sd": 10, "trend_per_day": 2, "decimals": 0},
          "y": {"mean": 3, "sd": 1, "min": 1, "max": 5, "decimals": 1}}
ANOMALY = {"astronaut": "a1", "indicator": "x", "day": 4, "value": 999}
START = datetime(2027, 4, 1)


def run(params=PARAMS, anomalies=(ANOMALY,), seed=1, preflight=14, mission=10):
    return gen.generate(params, list(anomalies), ["a1", "a2"], UNITS, START, preflight, mission, seed)


def test_find_todos():
    params = {"x": {"mean": "TODO_EDU", "sd": 1}}
    anomalies = [{"astronaut": "a1", "indicator": "x", "day": "TODO_GONZALO", "value": 5}]
    assert gen.find_todos(params, anomalies) == ["INDICATOR_PARAMS[x][mean]", "ANOMALIES[0][day]"]
    assert gen.find_todos(PARAMS, [ANOMALY]) == []


def _documented_block() -> dict:
    """The parameter block of docs/DEMO_DATA_HANDOFF.md (parsed as literals, never executed)."""
    import ast
    from pathlib import Path
    doc = Path(__file__).resolve().parents[1] / "docs" / "DEMO_DATA_HANDOFF.md"
    block = doc.read_text(encoding="utf-8").split("```python\n", 1)[1].split("```", 1)[0]
    return {node.targets[0].id: ast.literal_eval(node.value) for node in ast.parse(block).body}


def test_generator_uses_the_documented_benchmark():
    """The script's parameters are exactly Edu's documented block (#83), same order."""
    spec = _documented_block()
    for name in ("SEED", "PREFLIGHT_DAYS", "MISSION_DAYS", "DEMO_DAY", "MEASURE_HOUR", "ANOMALIES"):
        assert getattr(gen, name) == spec[name], name
    assert list(gen.INDICATOR_PARAMS.items()) == list(spec["INDICATOR_PARAMS"].items())


def test_real_parameters_are_complete():
    scenario = {"MISSION_DAYS": gen.MISSION_DAYS, "DEMO_DAY": gen.DEMO_DAY}
    assert gen.find_todos(gen.INDICATOR_PARAMS, gen.ANOMALIES, scenario) == []
    assert gen.check_scenario(gen.MISSION_DAYS, gen.DEMO_DAY, gen.ANOMALIES) == []


def test_check_params():
    assert gen.check_params(PARAMS, [ANOMALY], ["a1", "a2"], UNITS, 10) == []
    bad_params = {"x": {"mean": 1, "sd": -1}, "z": {"mean": 1, "sd": 1, "trend_per_day": "fast"}}
    bad_anomalies = [{"astronaut": "a9", "indicator": "y", "day": 11, "value": "high"}]
    errors = gen.check_params(bad_params, bad_anomalies, ["a1"], UNITS, 10)
    assert len(errors) == 7


def test_shape_and_columns():
    df = run()
    assert list(df.columns) == MEASUREMENT_COLUMNS
    assert len(df) == 2 * 2 * (14 + 10)  # astronauts × indicators × days
    assert set(df["source"]) == {"simulated"}
    assert df["timestamp"].is_monotonic_increasing
    counts = df.groupby(["astronaut", "indicator", "phase"]).size()
    assert set(counts.xs("preflight", level="phase")) == {14}
    assert set(counts.xs("mission", level="phase")) == {10}
    assert set(df.loc[df["indicator"] == "y", "unit"]) == {"v"}


def test_dates_around_mission_start():
    df = run()
    ts = pd.to_datetime(df["timestamp"])
    pre, mission = ts[df["phase"] == "preflight"], ts[df["phase"] == "mission"]
    assert pre.max() < datetime(2027, 4, 1) <= mission.min()
    assert pre.min() == datetime(2027, 3, 18, 8)      # 14 days before
    assert mission.min() == datetime(2027, 4, 1, 8)   # mission day 1 = start date
    assert mission.max() == datetime(2027, 4, 10, 8)  # mission day 10


def test_same_seed_same_data():
    pd.testing.assert_frame_equal(run(seed=7), run(seed=7))
    assert not run(seed=7).equals(run(seed=8))


def test_anomaly_replaces_that_day_only():
    df = run()
    rows = df[(df["astronaut"] == "a1") & (df["indicator"] == "x") & (df["phase"] == "mission")]
    assert rows.iloc[3]["value"] == 999            # day 4
    assert (rows["value"] == 999).sum() == 1
    other = df[(df["astronaut"] == "a2") & (df["indicator"] == "x")]
    assert 999 not in set(other["value"])


def test_clip_and_rounding():
    df = run()
    y = df[df["indicator"] == "y"]["value"]
    assert y.between(1, 5).all()
    assert (y.round(1) == y).all()
    x = df[df["indicator"] == "x"]["value"]
    assert (x.round(0) == x).all()


def test_trend_raises_mission_values():
    params = {"x": {"mean": 100, "sd": 0, "trend_per_day": 2, "decimals": 0}}
    df = run(params=params, anomalies=())
    mission = df[(df["astronaut"] == "a1") & (df["phase"] == "mission")]["value"]
    assert list(mission) == [102 + 2 * d for d in range(10)]


def test_write_and_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "SEED_DIR", tmp_path / "seed")
    df = run()
    gen.write(df)
    assert (tmp_path / "measurements.csv").read_bytes() == (tmp_path / "seed" / "measurements.csv").read_bytes()
    # Count rows in the file itself: load_measurements() may hide future mission rows (mission clock).
    assert len(pd.read_csv(tmp_path / "measurements.csv")) == len(df)
    baseline = data.get_baseline("a1", "x")
    assert baseline["n"] == 14 and baseline["std"] > 0


def test_main_refuses_while_todo(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "MISSION_STATE_FILE", tmp_path / "mission_state.json")
    monkeypatch.setattr(models, "SEED_DIR", tmp_path / "seed")
    monkeypatch.setattr(gen, "DEMO_DAY", "TODO_GONZALO")
    assert gen.main() == 1
    assert "TODO" in capsys.readouterr().out
    assert not (tmp_path / "measurements.csv").exists()


@pytest.fixture
def complete(tmp_path, monkeypatch):
    """Complete FAKE parameters (not health values); every data path in a temporary folder."""
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "MISSION_STATE_FILE", tmp_path / "mission_state.json")
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_path / "episodes.json")
    monkeypatch.setattr(models, "SEED_DIR", tmp_path / "seed")
    monkeypatch.setattr(gen, "INDICATOR_PARAMS", {"heart_rate": {"mean": 50, "sd": 1, "decimals": 0}})
    monkeypatch.setattr(gen, "ANOMALIES", [{"astronaut": "a1", "indicator": "heart_rate",
                                            "day": 4, "value": 80}])
    monkeypatch.setattr(gen, "MISSION_DAYS", 6)
    monkeypatch.setattr(gen, "DEMO_DAY", 4)
    return tmp_path


def test_main_writes_with_complete_parameters(complete):
    assert gen.main() == 0
    written = pd.read_csv(complete / "measurements.csv")
    assert len(written) == 3 * (gen.PREFLIGHT_DAYS + 6)
    for folder in (complete, complete / "seed"):
        state = json.loads((folder / "mission_state.json").read_text(encoding="utf-8"))
        assert state == {"now": "2027-04-04T00:00:00"}   # 00:00 of mission day 4


def test_one_advance_after_reset_reveals_the_demo_anomaly(complete, monkeypatch):
    """End to end: generate -> Reset demo -> one Advance 24 h -> the demo anomaly is revealed."""
    from core import mission
    monkeypatch.setattr(models, "DATA_DIR", complete)
    assert gen.main() == 0
    data.reset_demo()
    visible = data.load_measurements(astronaut="a1", phase="mission")
    assert list(visible["timestamp"].dt.day) == [1, 2, 3]     # earlier days: history
    revealed = mission.advance(24)
    assert [(m["astronaut"], m["value"]) for m in revealed if m["value"] == 80] == [("a1", 80.0)]
    assert {m["timestamp"] for m in revealed} == {"2027-04-04T08:00:00"}


def test_scenario_todos_are_listed():
    todos = gen.find_todos({}, [], {"MISSION_DAYS": "TODO_EDU", "DEMO_DAY": 3})
    assert todos == ["MISSION_DAYS"]


@pytest.mark.parametrize("mission_days, demo_day, anomaly_day, ok", [
    (10, 4, 4, True),
    (10, 4, 5, False),     # no anomaly on the demo day
    (10, 11, 11, False),   # demo day after the mission
    (0, 1, 1, False),
    (10, 2.5, 2.5, False),
    (10, True, 1, False),
])
def test_check_scenario(mission_days, demo_day, anomaly_day, ok):
    errors = gen.check_scenario(mission_days, demo_day, [{"day": anomaly_day}])
    assert (errors == []) is ok


def test_seed_clock():
    assert gen.seed_clock(datetime(2027, 4, 1), 1) == datetime(2027, 4, 1)
    assert gen.seed_clock(datetime(2027, 4, 1, 6, 30), 5) == datetime(2027, 4, 5)


def _indicators_in(cond, found):
    if isinstance(cond, dict):
        if "indicator" in cond:
            found.add(cond["indicator"])
        for value in cond.values():
            _indicators_in(value, found)
    elif isinstance(cond, list):
        for value in cond:
            _indicators_in(value, found)
    return found


def test_generator_simulates_the_indicators_of_the_real_problems():
    """INDICATOR_PARAMS only simulates indicators used by the real problems (#35), all configured.

    A subset is fine: the benchmark only covers the indicators with fully specified values (#83).
    """
    from core import config
    used = set()
    for problem in config.load_problems().values():  # real problems only (no "_" fixtures)
        _indicators_in(problem.get("symptoms", {}), used)
        _indicators_in(problem.get("triggers", []), used)
    assert gen.INDICATOR_PARAMS and set(gen.INDICATOR_PARAMS) <= used
    assert used <= set(config.load_indicators())
