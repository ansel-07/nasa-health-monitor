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


def make(timestamp, value, astronaut="a1", indicator="heart_rate", phase="mission",
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


def test_load_measurements_filters_and_sorts(tmp_data):
    data.add_measurement(make("2027-04-10T10:00:00", 70))
    data.add_measurement(make("2027-04-10T08:00:00", 60))
    data.add_measurement(make("2027-04-01T08:00:00", 58, phase="preflight", source="simulated"))
    data.add_measurement(make("2027-04-10T08:00:00", 6.5, indicator="sleep_hours", unit="h"))
    data.add_measurement(make("2027-04-10T08:00:00", 80, astronaut="a2"))

    hr = data.load_measurements(astronaut="a1", indicator="heart_rate")
    assert list(hr["value"]) == [58.0, 60.0, 70.0]
    mission = data.load_measurements(astronaut="a1", indicator="heart_rate", phase="mission")
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
    data.add_measurement(make("2027-04-10T08:00:00", 6.5, indicator="sleep_hours", unit="h"))
    data.add_measurement(make("2027-04-11T08:00:00", 99, astronaut="a2"))
    assert data.latest_values("a1") == {"heart_rate": 70.0, "sleep_hours": 6.5}
