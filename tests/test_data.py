# AI-assisted: generated with Claude Code and reviewed by Fran.
"""Measurements and astronauts in core/data.py. Uses temporary files, never data/."""
from datetime import datetime

import pandas as pd
import pytest

from core import data, models
from core.models import MEASUREMENT_COLUMNS


@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    """Redirect the data files to an empty temporary folder."""
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "ASTRONAUTS_FILE", tmp_path / "astronauts.csv")
    return tmp_path


def make(timestamp, value, astronaut="a1", indicator="_example_indicator", phase="mission",
         source="manual", unit="bpm"):
    return {"timestamp": timestamp, "astronaut": astronaut, "indicator": indicator,
            "value": value, "unit": unit, "phase": phase, "source": source}


def test_load_astronauts_reads_csv(tmp_data):
    (tmp_data / "astronauts.csv").write_text(
        "id,name,role\na1,Astronaut A,Commander\na2,Astronaut B,Flight engineer\n",
        encoding="utf-8",
    )
    df = data.load_astronauts()
    assert list(df.columns) == ["id", "name", "role"]
    assert list(df["id"]) == ["a1", "a2"]


def test_load_astronauts_missing_file(tmp_data):
    assert data.load_astronauts().empty


def test_load_measurements_empty_and_missing(tmp_data):
    df = data.load_measurements()
    assert df.empty and list(df.columns) == MEASUREMENT_COLUMNS
    (tmp_data / "measurements.csv").write_text(",".join(MEASUREMENT_COLUMNS) + "\n")
    assert data.load_measurements().empty


def test_add_then_load_roundtrip(tmp_data):
    data.add_measurement(make("2027-04-10T08:00:00", 62))
    data.add_measurement(make(datetime(2027, 4, 10, 9, 0), "64.5"))
    df = data.load_measurements()
    assert list(df.columns) == MEASUREMENT_COLUMNS
    assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
    assert list(df["value"]) == [62.0, 64.5]


def test_iso_timestamps_with_mixed_precision_roundtrip(tmp_data):
    data.add_measurement(make("2027-04-10T08:00:00", 62))
    data.add_measurement(make("2027-04-10T08:00:00.123456", 63))
    data.add_measurement(make(datetime(2027, 4, 10, 8, 0, 0, 654321), 64))
    rows = data.load_measurements()
    assert list(rows["timestamp"].dt.microsecond) == [0, 123456, 654321]
    assert data.latest_values("a1") == {"_example_indicator": 64}


@pytest.mark.parametrize("timestamp", [None, "not-a-time", "NaT", "2027-04-10T08:00:00+01:00"])
def test_bad_timestamp_is_rejected_without_poisoning_existing_csv(tmp_data, timestamp):
    data.add_measurement(make("2027-04-10T08:00:00", 62))
    before = (tmp_data / "measurements.csv").read_bytes()
    with pytest.raises(ValueError, match="timestamp"):
        data.add_measurement(make(timestamp, 63))
    assert (tmp_data / "measurements.csv").read_bytes() == before


def test_load_measurements_filters_and_sorts(tmp_data):
    data.add_measurement(make("2027-04-10T10:00:00", 70))
    data.add_measurement(make("2027-04-10T08:00:00", 60))
    data.add_measurement(make("2027-03-31T08:00:00", 58, phase="preflight", source="simulated"))
    data.add_measurement(make("2027-04-10T08:00:00", 6.5, indicator="_example_indicator_2", unit="h"))
    data.add_measurement(make("2027-04-10T08:00:00", 80, astronaut="a2"))

    hr = data.load_measurements(astronaut="a1", indicator="_example_indicator")
    assert list(hr["value"]) == [58.0, 60.0, 70.0]
    mission = data.load_measurements(astronaut="a1", indicator="_example_indicator", phase="mission")
    assert list(mission["value"]) == [60.0, 70.0]
    assert len(data.load_measurements(astronaut="a2")) == 1
    assert len(data.load_measurements()) == 5


@pytest.mark.parametrize("change", [
    {"phase": "landing"},
    {"source": "guess"},
    {"indicator": "not_an_indicator"},
    {"value": "abc"},
])
def test_add_measurement_rejects_bad_values(tmp_data, change):
    with pytest.raises(ValueError):
        data.add_measurement({**make("2027-04-10T08:00:00", 62), **change})
    assert not (tmp_data / "measurements.csv").exists()


def test_add_measurement_rejects_missing_column(tmp_data):
    m = make("2027-04-10T08:00:00", 62)
    del m["unit"]
    with pytest.raises(ValueError):
        data.add_measurement(m)


def test_latest_values(tmp_data):
    assert data.latest_values("a1") == {}
    data.add_measurement(make("2027-04-10T10:00:00", 70))
    data.add_measurement(make("2027-04-10T08:00:00", 60))
    data.add_measurement(make("2027-04-10T08:00:00", 6.5, indicator="_example_indicator_2", unit="h"))
    data.add_measurement(make("2027-04-11T08:00:00", 99, astronaut="a2"))
    assert data.latest_values("a1") == {"_example_indicator": 70.0, "_example_indicator_2": 6.5}


def add_preflight(values, astronaut="a1", indicator="_example_indicator"):
    for day, value in enumerate(values, start=1):
        data.add_measurement(make(f"2027-03-{day:02d}T08:00:00", value, astronaut=astronaut,
                                  indicator=indicator, phase="preflight", source="simulated"))


def test_get_baseline_uses_only_preflight_of_that_astronaut(tmp_data):
    add_preflight([60, 62, 64])
    add_preflight([90, 95], astronaut="a2")
    data.add_measurement(make("2027-04-10T08:00:00", 120))  # mission value: ignored
    baseline = data.get_baseline("a1", "_example_indicator")
    assert baseline == {"mean": 62.0, "std": 2.0, "n": 3}  # sample std (ddof=1)
    assert isinstance(baseline["n"], int)


def test_get_baseline_without_data(tmp_data):
    assert data.get_baseline("a1", "_example_indicator") is None
    data.add_measurement(make("2027-04-10T08:00:00", 62))  # only mission data
    assert data.get_baseline("a1", "_example_indicator") is None


def test_z_score(tmp_data):
    add_preflight([60, 62, 64])
    assert data.z_score("a1", "_example_indicator", 66) == pytest.approx(2.0)
    assert data.z_score("a1", "_example_indicator", 59) == pytest.approx(-1.5)
    assert data.z_score("a1", "_example_indicator", 62) == pytest.approx(0.0)


def test_z_score_none_without_baseline_or_zero_std(tmp_data):
    assert data.z_score("a1", "_example_indicator", 70) is None
    add_preflight([62])  # one value: std 0.0
    assert data.get_baseline("a1", "_example_indicator")["std"] == 0.0
    assert data.z_score("a1", "_example_indicator", 70) is None
    add_preflight([5, 5, 5], indicator="_example_indicator_2")  # identical values: std 0
    assert data.z_score("a1", "_example_indicator_2", 3) is None
