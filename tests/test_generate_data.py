# AI-assisted: generated with Claude Code and reviewed by Fran.
"""scripts/generate_data.py. Every number here is a FAKE test value, not health content."""
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


def test_real_parameters_are_still_todo():
    """Until Edu and Gonzalo fill them in, the real parameters must not be used."""
    assert gen.find_todos(gen.INDICATOR_PARAMS, gen.ANOMALIES)


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
    assert len(data.load_measurements()) == len(df)
    baseline = data.get_baseline("a1", "x")
    assert baseline["n"] == 14 and baseline["std"] > 0


def test_main_refuses_while_todo(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "SEED_DIR", tmp_path / "seed")
    assert gen.main() == 1
    assert "TODO" in capsys.readouterr().out
    assert not (tmp_path / "measurements.csv").exists()


def test_main_writes_with_complete_parameters(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "SEED_DIR", tmp_path / "seed")
    fake = {"heart_rate": {"mean": 50, "sd": 1, "decimals": 0}}
    monkeypatch.setattr(gen, "INDICATOR_PARAMS", fake)
    monkeypatch.setattr(gen, "ANOMALIES", [{"astronaut": "a1", "indicator": "heart_rate",
                                            "day": 2, "value": 80}])
    assert gen.main() == 0
    assert len(data.load_measurements()) == 3 * (gen.PREFLIGHT_DAYS + gen.MISSION_DAYS)
