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
    """Problems with numeric test thresholds on _example_indicator (fake values for the test)."""
    problems = {
        "p": {"triggers": [
            {"severity": "mild", "when": {"indicator": "_example_indicator", "z_above": 2}},
            {"severity": "severe", "when": {"indicator": "_example_indicator", "above": 100}},
            {"severity": "moderate", "when": {"indicator": "_example_indicator", "below": 40}},
            {"severity": "severe", "when": {"indicator": "_example_indicator", "above": 90},
             "environments": ["mars"]},
            {"severity": "mild", "when": {"indicator": "_example_indicator", "above": "TODO_EDU"}},
            {"severity": "mild", "when": {"indicator": "_example_indicator_2", "below": 5}},
            {"severity": "mild", "when": {"all": [{"indicator": "_example_indicator", "above": 1}]}},
        ]},
    }
    monkeypatch.setattr(charts.config, "load_problems", lambda: problems)


def add(timestamp, value, phase="mission", indicator="_example_indicator"):
    data.add_measurement({"timestamp": timestamp, "astronaut": "a1", "indicator": indicator,
                          "value": value, "unit": "bpm", "phase": phase,
                          "source": "simulated" if phase == "preflight" else "manual"})


def add_preflight_60_62_64():
    for day, value in zip((1, 2, 3), (60, 62, 64)):
        add(f"2027-03-0{day}T08:00:00", value, phase="preflight")


def test_threshold_bands_from_config(tmp_data, fake_problems):
    add_preflight_60_62_64()  # baseline 62 ± 2
    bands = charts.threshold_bands("a1", "_example_indicator")
    assert [(b["severity"], b["direction"], b["value"]) for b in bands] == [
        ("mild", "above", 66.0),       # z_above 2 -> 62 + 2 * 2
        ("moderate", "below", 40.0),
        ("severe", "above", 100.0),
    ]  # skipped: environment-only, TODO, other indicator, nested all/any


def test_threshold_bands_for_an_environment(tmp_data, fake_problems):
    on_mars = charts.threshold_bands("a1", "_example_indicator", environment="mars")
    assert [(b["severity"], b["value"]) for b in on_mars] == [
        ("moderate", 40.0), ("severe", 100.0), ("severe", 90.0)]  # + the Mars-only trigger
    on_iss = charts.threshold_bands("a1", "_example_indicator", environment="iss")
    assert [b["value"] for b in on_iss] == [40.0, 100.0]


def test_chart_passes_environment_to_bands(tmp_data, fake_problems):
    add("2027-04-10T08:00:00", 70)
    def severe_bands(fig):
        return [s for s in fig.layout.shapes if s.fillcolor == charts.SEVERITY_COLORS["severe"]]
    assert len(severe_bands(charts.indicator_chart("a1", "_example_indicator"))) == 1
    assert len(severe_bands(charts.indicator_chart("a1", "_example_indicator", environment="mars"))) == 2


def test_threshold_bands_skip_z_without_baseline(tmp_data, fake_problems):
    assert [b["value"] for b in charts.threshold_bands("a1", "_example_indicator")] == [40.0, 100.0]


def test_real_config_todo_thresholds_give_no_bands(tmp_data):
    add_preflight_60_62_64()
    for band in charts.threshold_bands("a1", "_example_indicator"):
        assert isinstance(band["value"], float)


@pytest.mark.parametrize("compact", [False, True])
def test_empty_chart(tmp_data, compact):
    fig = charts.indicator_chart("a1", "_example_indicator", compact=compact)
    assert isinstance(fig, go.Figure)
    assert fig.data == ()
    assert fig.layout.annotations[0].text == "No measurements yet"


def test_full_chart(tmp_data, fake_problems):
    add_preflight_60_62_64()
    add("2027-04-10T08:00:00", 70)
    add("2027-04-11T08:00:00", 72)
    data.save_episode({"id": "ep-0001", "astronaut": "a1", "problem": "p", "status": "active",
                       "severity_initial": "mild", "severity": "mild",
                       "trigger": {"indicator": "_example_indicator", "value": 70, "z": 4.0,
                                   "measured_at": "2027-04-10T08:00:00"}})
    fig = charts.indicator_chart("a1", "_example_indicator")

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
    fig = charts.indicator_chart("a1", "_example_indicator", compact=True)
    assert [t.name for t in fig.data] == ["Mission"]
    assert fig.layout.showlegend is False
    assert fig.layout.height == charts.COMPACT_HEIGHT


def test_compact_chart_without_mission_data_shows_preflight(tmp_data):
    add_preflight_60_62_64()
    fig = charts.indicator_chart("a1", "_example_indicator", compact=True)
    assert [t.name for t in fig.data] == ["Pre-flight"]


def test_single_value_has_a_visible_range(tmp_data):
    add("2027-04-10T08:00:00", 70)
    low, high = charts.indicator_chart("a1", "_example_indicator").layout.yaxis.range
    assert low < 70 < high


# --- Symptom-based problems (issue #37), with the _example fixture -------------------------

@pytest.fixture
def example_problems(monkeypatch):
    """Load the _example fixture too (the app never shows it as health content)."""
    load = charts.config.load_problems
    monkeypatch.setattr(charts.config, "load_problems", lambda: load(include_examples=True))


def test_example_symptom_levels_give_watch_and_concern_bands(tmp_data, example_problems):
    bands = charts.threshold_bands("a1", "_example_indicator")
    assert [(b["severity"], b["direction"], b["value"], b["symptom"]) for b in bands] == [
        ("watch", "above", 10.0, "symptom_a"),
        ("concern", "above", 30.0, "symptom_a"),
    ]  # symptoms win over the legacy triggers of the same problem: no duplicate bands
    assert bands[0]["label"] == "Watch · Example symptom A (test fixture)"


def test_example_mars_only_level(tmp_data, example_problems):
    bands = charts.threshold_bands("a1", "_example_indicator", environment="mars")
    assert sorted((b["severity"], b["value"]) for b in bands) == [
        ("concern", 30.0), ("watch", 5.0), ("watch", 10.0)]
    assert len(charts.threshold_bands("a1", "_example_indicator", environment="iss")) == 2


def test_example_second_symptom_uses_its_own_indicator(tmp_data, example_problems):
    bands = charts.threshold_bands("a1", "_example_indicator_2")
    assert [(b["severity"], b["value"], b["symptom"]) for b in bands] == [
        ("watch", 10.0, "symptom_b"), ("concern", 20.0, "symptom_b")]


def test_symptom_bands_inclusive_z_todo_and_compound(tmp_data, monkeypatch):
    add_preflight_60_62_64()  # baseline 62 ± 2
    problems = {"p": {"symptoms": {
        "s1": {"name": "TODO_EDU", "levels": [
            {"level": "concern", "when": {"indicator": "_example_indicator", "at_least": 100}},
            {"level": "watch", "when": {"indicator": "_example_indicator", "z_above": 2}},
            {"level": "watch", "when": {"indicator": "_example_indicator", "at_most": 40}},
        ]},
        "s2": {"name": "Skipped", "levels": [
            {"level": "watch", "when": {"indicator": "_example_indicator", "above": "TODO_EDU"}},
            {"level": "concern", "when": {"all": [{"indicator": "_example_indicator", "above": 1}]}},
            {"level": "not_present", "when": {"indicator": "_example_indicator", "above": 1}},
        ]},
    }}}
    monkeypatch.setattr(charts.config, "load_problems", lambda: problems)
    bands = charts.threshold_bands("a1", "_example_indicator")
    assert [(b["severity"], b["direction"], b["value"], b["label"]) for b in bands] == [
        ("watch", "above", 66.0, "Watch"),      # z_above 2 -> 62 + 2 * 2; TODO name -> no name
        ("watch", "below", 40.0, "Watch"),      # at_most
        ("concern", "above", 100.0, "Concern"),  # at_least
    ]


def test_chart_draws_symptom_bands_and_new_state_marks(tmp_data, example_problems):
    data.add_measurement({"timestamp": "2027-04-10T08:00:00", "astronaut": "a1",
                          "indicator": "_example_indicator", "value": 12, "unit": "units",
                          "phase": "mission", "source": "manual"})
    data.save_episode({"id": "ep-0001", "astronaut": "a1", "problem": "_example",
                       "status": "active", "severity_initial": "medical_urgency",
                       "trigger": {"indicator": "_example_indicator", "value": 12,
                                   "measured_at": "2027-04-10T08:00:00"}})
    fig = charts.indicator_chart("a1", "_example_indicator")
    labels = {a.text for a in fig.layout.annotations}
    assert {"Watch · Example symptom A (test fixture)",
            "Concern · Example symptom A (test fixture)"} <= labels
    fills = [s.fillcolor for s in fig.layout.shapes]
    assert charts.WARNING in fills and charts.SERIOUS in fills
    alert = next(t for t in fig.data if t.name == "Alert")
    assert list(alert.marker.color) == [charts.CRITICAL]  # medical_urgency mark is red


# --- metric conditions (issue #56). Synthetic baseline 62 ± 2 (n=3); fake thresholds ------

def symptom_problems(*levels):
    """One fake symptom whose level rules are the given conditions on _example_indicator."""
    return {"p": {"symptoms": {"s": {"name": "S", "levels": [
        {"level": "concern", "when": {"indicator": "_example_indicator", **cond}} for cond in levels]}}}}


def ranges(monkeypatch, *levels, indicator="_example_indicator"):
    monkeypatch.setattr(charts.config, "load_problems", lambda: symptom_problems(*levels))
    return [(b["low"], b["high"], b["direction"]) for b in charts.threshold_bands("a1", indicator)]


@pytest.mark.parametrize("cond, expected", [
    ({"metric": "baseline_fraction", "below": 0.8}, [(None, 49.6, "below")]),       # mu * t
    ({"metric": "baseline_delta", "at_least": 20}, [(82.0, None, "above")]),        # mu + t
    ({"metric": "baseline_delta", "at_least": 20, "below": 55},                      # ANDed bounds
     [(82.0, 117.0, "between")]),
    ({"metric": "z_score", "above": 2}, [(66.0, None, "above")]),                   # mu + t * sigma
    ({"metric": "z_score", "at_most": -1.5}, [(None, 59.0, "below")]),
    ({"metric": "abs_z_score", "at_least": 2}, [(None, 58.0, "below"), (66.0, None, "above")]),
    ({"metric": "abs_z_score", "below": 1}, [(60.0, 64.0, "between")]),
    ({"metric": "abs_z_score", "at_least": 2, "below": 3},
     [(56.0, 58.0, "between"), (66.0, 68.0, "between")]),
    ({"metric": "raw", "above": 100}, [(100.0, None, "above")]),
    ({"above": 50, "at_most": 70}, [(50.0, 70.0, "between")]),                      # default raw
])
def test_metric_bounds_become_values_in_the_indicator_unit(tmp_data, monkeypatch, cond, expected):
    add_preflight_60_62_64()
    got = ranges(monkeypatch, cond)
    assert [(pytest.approx(lo) if lo is not None else None,
             pytest.approx(hi) if hi is not None else None, d) for lo, hi, d in got] == expected


@pytest.mark.parametrize("cond", [
    {"metric": "raw", "at_least": 5, "at_most": 3},                 # empty range
    {"metric": "baseline_delta", "at_least": 20, "below": "TODO_EDU"},  # incomplete: skip all of it
    {"metric": "not_a_metric", "above": 1},
])
def test_unusable_metric_conditions_give_no_band(tmp_data, monkeypatch, cond):
    add_preflight_60_62_64()
    assert ranges(monkeypatch, cond) == []


def test_metric_needs_a_valid_baseline(tmp_data, monkeypatch):
    conds = [{"metric": "z_score", "above": 2}, {"metric": "baseline_delta", "above": 5},
             {"metric": "abs_z_score", "above": 2}, {"z_above": 2}, {"metric": "raw", "above": 70}]
    assert ranges(monkeypatch, *conds) == [(70.0, None, "above")]   # no baseline: only raw
    add("2027-03-01T08:00:00", 62, phase="preflight")                # n = 1: still not valid
    assert ranges(monkeypatch, *conds) == [(70.0, None, "above")]


def test_baseline_fraction_needs_a_positive_mean(tmp_data, monkeypatch):
    for day, value in zip((1, 2, 3), (-2.0, -3.0, -4.0)):
        add(f"2027-03-0{day}T08:00:00", value, phase="preflight")
    assert ranges(monkeypatch, {"metric": "baseline_fraction", "below": 0.8}) == []
    assert ranges(monkeypatch, {"metric": "baseline_delta", "below": -1}) == [(None, -4.0, "below")]


def test_chart_draws_a_between_band_with_both_edges(tmp_data, monkeypatch):
    add_preflight_60_62_64()
    add("2027-04-10T08:00:00", 90)
    monkeypatch.setattr(charts.config, "load_problems", lambda: symptom_problems(
        {"metric": "baseline_delta", "at_least": 20, "below": 55}))
    fig = charts.indicator_chart("a1", "_example_indicator")
    band = next(s for s in fig.layout.shapes if s.fillcolor == charts.SERIOUS)
    assert (band.y0, band.y1) == (pytest.approx(82.0), pytest.approx(117.0))
    assert fig.layout.yaxis.range[1] > 117


# --- projector readability: mission-day axis, Launch and Now lines -------------------------

@pytest.fixture
def fixed_now(monkeypatch):
    from datetime import datetime
    now = datetime(2027, 4, 3, 0, 0)          # start of mission day 3
    monkeypatch.setattr(charts.mission, "now", lambda: now)
    return now


def test_x_axis_is_the_mission_day_with_real_time_in_hover(tmp_data, fixed_now):
    add("2027-03-31T00:00:00", 60, phase="preflight")   # the day before launch -> day 0
    add("2027-04-01T12:00:00", 66)                       # mission day 1, noon -> 1.5
    fig = charts.indicator_chart("a1", "_example_indicator")
    pre, mission_trace = fig.data[0], fig.data[1]
    assert list(pre.x) == [pytest.approx(0.0)] and list(mission_trace.x) == [pytest.approx(1.5)]
    assert list(mission_trace.customdata) == ["2027-04-01 12:00"]
    assert fig.layout.xaxis.title.text == "Mission day"


def test_launch_and_now_lines(tmp_data, fixed_now):
    add("2027-03-31T08:00:00", 60, phase="preflight")
    add("2027-04-01T08:00:00", 66)
    fig = charts.indicator_chart("a1", "_example_indicator")
    vlines = sorted(s.x0 for s in fig.layout.shapes if s.type == "line" and s.x0 == s.x1)
    assert vlines == [1, pytest.approx(3.0)]                     # Launch at day 1, Now at day 3
    labels = {a.text for a in fig.layout.annotations}
    assert {"Launch", "Now"} <= labels

    compact = charts.indicator_chart("a1", "_example_indicator", compact=True)
    compact_labels = {a.text for a in compact.layout.annotations}
    assert "Now" in compact_labels and "Launch" not in compact_labels   # mission only: no Launch


def test_projector_font_sizes(tmp_data, fixed_now):
    add("2027-04-01T08:00:00", 66)
    assert charts.indicator_chart("a1", "_example_indicator").layout.font.size == charts.FULL_FONT_SIZE
    assert (charts.indicator_chart("a1", "_example_indicator", compact=True).layout.font.size
            == charts.COMPACT_FONT_SIZE)


def test_alert_marks_use_the_mission_day(tmp_data, fixed_now):
    add("2027-04-02T08:00:00", 90)
    data.save_episode({"id": "ep-1", "astronaut": "a1", "problem": "p", "status": "active",
                       "severity_initial": "watch",
                       "trigger": {"indicator": "_example_indicator", "value": 90,
                                   "measured_at": "2027-04-02T06:00:00"}})
    alert = next(t for t in charts.indicator_chart("a1", "_example_indicator").data if t.name == "Alert")
    assert list(alert.x) == [pytest.approx(2.25)]
    assert alert.customdata[0][3] == "2027-04-02 06:00"
