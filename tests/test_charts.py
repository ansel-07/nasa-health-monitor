# AI-assisted: generated with Claude Code and reviewed by Fran.
"""core/charts.py: indicator chart and severity bands. Uses temporary files, never data/.

Thresholds here are fake test values (on the _example fixture or patched problems),
not health content.
"""
import plotly.graph_objects as go
import pytest

from core import charts, data, models


@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_path / "episodes.json")
    return tmp_path


@pytest.fixture
def fake_problems(monkeypatch):
    """Problems with numeric test thresholds on heart_rate (fake values for the test)."""
    problems = {
        "p": {"triggers": [
            {"severity": "mild", "when": {"indicator": "heart_rate", "z_above": 2}},
            {"severity": "severe", "when": {"indicator": "heart_rate", "above": 100}},
            {"severity": "moderate", "when": {"indicator": "heart_rate", "below": 40}},
            {"severity": "severe", "when": {"indicator": "heart_rate", "above": 90},
             "environments": ["mars"]},
            {"severity": "mild", "when": {"indicator": "heart_rate", "above": "TODO_EDU"}},
            {"severity": "mild", "when": {"indicator": "sleep_hours", "below": 5}},
            {"severity": "mild", "when": {"all": [{"indicator": "heart_rate", "above": 1}]}},
        ]},
    }
    monkeypatch.setattr(charts.config, "load_problems", lambda: problems)


def add(timestamp, value, phase="mission", indicator="heart_rate"):
    data.add_measurement({"timestamp": timestamp, "astronaut": "a1", "indicator": indicator,
                          "value": value, "unit": "bpm", "phase": phase,
                          "source": "simulated" if phase == "preflight" else "manual"})


def add_preflight_60_62_64():
    for day, value in zip((1, 2, 3), (60, 62, 64)):
        add(f"2027-03-0{day}T08:00:00", value, phase="preflight")


def test_threshold_bands_from_config(tmp_data, fake_problems):
    add_preflight_60_62_64()  # baseline 62 ± 2
    bands = charts.threshold_bands("a1", "heart_rate")
    assert [(b["severity"], b["direction"], b["value"]) for b in bands] == [
        ("mild", "above", 66.0),       # z_above 2 -> 62 + 2 * 2
        ("moderate", "below", 40.0),
        ("severe", "above", 100.0),
    ]  # skipped: environment-only, TODO, other indicator, nested all/any


def test_threshold_bands_for_an_environment(tmp_data, fake_problems):
    on_mars = charts.threshold_bands("a1", "heart_rate", environment="mars")
    assert [(b["severity"], b["value"]) for b in on_mars] == [
        ("moderate", 40.0), ("severe", 100.0), ("severe", 90.0)]  # + the Mars-only trigger
    on_iss = charts.threshold_bands("a1", "heart_rate", environment="iss")
    assert [b["value"] for b in on_iss] == [40.0, 100.0]


def test_chart_passes_environment_to_bands(tmp_data, fake_problems):
    add("2027-04-10T08:00:00", 70)
    def severe_bands(fig):
        return [s for s in fig.layout.shapes if s.fillcolor == charts.SEVERITY_COLORS["severe"]]
    assert len(severe_bands(charts.indicator_chart("a1", "heart_rate"))) == 1
    assert len(severe_bands(charts.indicator_chart("a1", "heart_rate", environment="mars"))) == 2


def test_threshold_bands_skip_z_without_baseline(tmp_data, fake_problems):
    assert [b["value"] for b in charts.threshold_bands("a1", "heart_rate")] == [40.0, 100.0]


def test_real_config_todo_thresholds_give_no_bands(tmp_data):
    add_preflight_60_62_64()
    for band in charts.threshold_bands("a1", "heart_rate"):
        assert isinstance(band["value"], float)


@pytest.mark.parametrize("compact", [False, True])
def test_empty_chart(tmp_data, compact):
    fig = charts.indicator_chart("a1", "heart_rate", compact=compact)
    assert isinstance(fig, go.Figure)
    assert fig.data == ()
    assert fig.layout.annotations[0].text == "No measurements yet"


def test_full_chart(tmp_data, fake_problems):
    add_preflight_60_62_64()
    add("2027-04-10T08:00:00", 70)
    add("2027-04-11T08:00:00", 72)
    data.save_episode({"id": "ep-0001", "astronaut": "a1", "problem": "p", "status": "active",
                       "severity_initial": "mild", "severity": "mild",
                       "trigger": {"indicator": "heart_rate", "value": 70, "z": 4.0,
                                   "measured_at": "2027-04-10T08:00:00"}})
    fig = charts.indicator_chart("a1", "heart_rate")

    assert [t.name for t in fig.data] == ["Pre-flight", "Mission", "Alert"]
    assert fig.layout.showlegend is True
    assert fig.layout.height == charts.FULL_HEIGHT
    labels = {a.text for a in fig.layout.annotations}
    assert {"Your baseline", "Mild", "Moderate", "Severe"} <= labels
    low, high = fig.layout.yaxis.range
    assert low < 40 and high > 100  # every band visible


def test_compact_chart_shows_mission_only(tmp_data, fake_problems):
    add_preflight_60_62_64()
    add("2027-04-10T08:00:00", 70)
    fig = charts.indicator_chart("a1", "heart_rate", compact=True)
    assert [t.name for t in fig.data] == ["Mission"]
    assert fig.layout.showlegend is False
    assert fig.layout.height == charts.COMPACT_HEIGHT


def test_compact_chart_without_mission_data_shows_preflight(tmp_data):
    add_preflight_60_62_64()
    fig = charts.indicator_chart("a1", "heart_rate", compact=True)
    assert [t.name for t in fig.data] == ["Pre-flight"]


def test_single_value_has_a_visible_range(tmp_data):
    add("2027-04-10T08:00:00", 70)
    low, high = charts.indicator_chart("a1", "heart_rate").layout.yaxis.range
    assert low < 70 < high
