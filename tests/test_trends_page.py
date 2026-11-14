# AI-assisted: generated with Claude Code and reviewed by Fran.
"""Trends page (pages/3_Trends.py) with Streamlit's AppTest. Temporary files, synthetic values."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import charts, config, models

PAGE = Path(__file__).resolve().parents[1] / "pages" / "3_Trends.py"

INDICATORS = {
    "x": {"name": "Indicator X", "unit": "u"},
    "y": {"name": "TODO_EDU", "unit": "u"},
    "_example_indicator": {"name": "Fixture", "unit": "u"},
}
HEADER = "timestamp,astronaut,indicator,value,unit,phase,source\n"


@pytest.fixture
def screen(tmp_path, monkeypatch):
    calls = []
    (tmp_path / "astronauts.csv").write_text(
        "id,name,role\na1,Astronaut A,Commander\na2,Astronaut B,Flight engineer\n")
    monkeypatch.setattr(models, "MISSION_STATE_FILE", tmp_path / "mission_state.json")
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(models, "ASTRONAUTS_FILE", tmp_path / "astronauts.csv")
    monkeypatch.setattr(models, "EPISODES_FILE", tmp_path / "episodes.json")
    monkeypatch.setattr(config, "load_indicators", lambda: INDICATORS)
    monkeypatch.setattr(config, "load_environments", lambda: {"mars": {"name": "Mars"}})
    original_chart = charts.indicator_chart

    def chart(astronaut, indicator, compact=False, environment=None):
        calls.append((astronaut, indicator, compact, environment))
        return original_chart(astronaut, indicator, compact, environment)

    monkeypatch.setattr(charts, "indicator_chart", chart)
    app = AppTest.from_file(str(PAGE))
    app.session_state["astronaut"] = "a1"
    app.session_state["environment"] = "mars"
    return app, calls, tmp_path


def write_measurements(folder, rows):
    (folder / "measurements.csv").write_text(HEADER + "".join(f"{r}\n" for r in rows))


def test_needs_an_astronaut():
    app = AppTest.from_file(str(PAGE)).run()
    assert app.warning[0].value == "Choose an astronaut on the Home page first."


def preflight_and_mission(folder, extra=()):
    write_measurements(folder, [
        "2027-03-28T08:00:00,a1,x,60,u,preflight,simulated",
        "2027-03-29T08:00:00,a1,x,62,u,preflight,simulated",
        "2027-03-30T08:00:00,a1,x,64,u,preflight,simulated",
        "2027-04-01T08:00:00,a1,x,66,u,mission,manual",
        *extra,
    ])


def test_no_measurements_shows_an_empty_state(screen):
    app, calls, _ = screen
    app.run()
    assert not app.exception
    assert [i.value for i in app.info] == ["No measurements yet."]
    assert len(app.expander) == 0
    assert calls == []


def test_one_card_per_indicator_with_data_and_no_demo_controls(screen):
    app, calls, folder = screen
    preflight_and_mission(folder, extra=[
        "2027-04-01T08:00:00,a1,y,7,u,mission,manual",                 # TODO name -> id
        "2027-04-01T08:00:00,a1,_example_indicator,9,u,mission,manual",  # fixture: hidden
        "2027-04-01T08:00:00,a2,x,99,u,mission,manual",                # another astronaut
    ])
    app.run()
    assert not app.exception
    assert [e.label for e in app.expander] == ["Indicator X · latest 66.0 u", "y · latest 7.0 u"]
    assert app.caption[0].value == "Astronaut A · Mars"
    assert sorted(calls) == [("a1", "x", False, "mars"), ("a1", "y", False, "mars")]  # full charts
    assert not [b for b in app.button if "Advance" in b.label]       # moved to the Main Menu (#94)


def test_card_shows_latest_baseline_and_z(screen):
    app, _, folder = screen
    preflight_and_mission(folder)
    app.run()
    card = app.expander[0]
    assert {m.label: m.value for m in card.metric} == {
        "Latest value": "66.0 u", "Personal baseline (pre-flight)": "62.0 ± 2.0 u",
        "Distance from baseline (z)": "+2.0"}
    assert not [c for c in card.caption if "Not enough pre-flight" in c.value]


def test_card_without_valid_baseline_says_so(screen):
    app, _, folder = screen
    write_measurements(folder, ["2027-03-30T08:00:00,a1,x,60,u,preflight,simulated",   # n = 1
                                "2027-04-01T08:00:00,a1,x,66,u,mission,manual"])
    app.run()
    card = app.expander[0]
    assert {m.label: m.value for m in card.metric}["Distance from baseline (z)"] == "—"
    assert any("Not enough pre-flight measurements" in c.value for c in card.caption)


# --- Alert history -------------------------------------------------------------------------

def test_history_without_alerts(screen):
    app, _, _ = screen
    app.run()
    assert not app.exception
    assert [s.value for s in app.subheader] == ["Measurements", "Alert history"]
    assert any(c.value == "No alerts yet for this astronaut." for c in app.caption)
    assert len(app.dataframe) == 0


def test_history_lists_alerts_newest_first_with_readable_text(screen, monkeypatch):
    from core import data
    app, _, _ = screen
    monkeypatch.setattr(config, "load_problems", lambda: {"p1": {"name": "Problem One"}})
    data.save_episode({"id": "ep-1", "astronaut": "a1", "problem": "p1", "status": "dismissed",
                       "severity": "watch", "opened_at": "2027-04-01T08:05:00",
                       "closed_at": "2027-04-01T09:00:00",
                       "trigger": {"indicator": "x", "value": 70, "measured_at": "2027-04-01T08:00:00"}})
    data.save_episode({"id": "ep-2", "astronaut": "a1", "problem": "p_unnamed", "status": "active",
                       "severity": "medical_urgency", "opened_at": "2027-04-03T08:05:00",
                       "closed_at": None,
                       "trigger": {"indicator": "x", "value": 95.5, "measured_at": "2027-04-03T08:00:00"}})
    data.save_episode({"id": "ep-3", "astronaut": "a2", "problem": "p1", "status": "active",
                       "severity": "watch", "opened_at": "2027-04-02T08:00:00"})  # other astronaut
    app.run()
    assert not app.exception
    rows = app.dataframe[0].value.to_dict("records")
    assert rows == [
        {"Alert": "P unnamed", "Severity": "Medical urgency", "Status": "Active: protocol in progress",
         "Raised by": "Indicator X: 95.5 u", "Opened": "2027-04-03 08:05 (day 3)", "Closed": "—"},
        {"Alert": "Problem One", "Severity": "Watch", "Status": "False alarm: the repeat was normal",
         "Raised by": "Indicator X: 70.0 u", "Opened": "2027-04-01 08:05 (day 1)",
         "Closed": "2027-04-01 09:00 (day 1)"},
    ]


def test_history_shows_waiting_alerts(screen, monkeypatch):
    from core import data
    app, _, _ = screen
    monkeypatch.setattr(config, "load_problems", lambda: {"p2": {"name": "Problem Two"}})
    data.save_pending([
        {"astronaut": "a1", "problem": "p2", "severity": "watch", "indicator": "x", "value": 3.0,
         "z": None, "measured_at": "2027-04-02T08:00:00"},
        {"astronaut": "a2", "problem": "p2", "severity": "watch", "indicator": "x", "value": 9.0,
         "z": None, "measured_at": "2027-04-02T08:00:00"},
    ])
    app.run()
    assert not app.exception
    assert any(m.value == "**Waiting alerts**" for m in app.markdown)
    assert app.dataframe[0].value.to_dict("records") == [
        {"Alert": "Problem Two", "Severity": "Watch", "Raised by": "Indicator X: 3.0 u",
         "Measured": "2027-04-02 08:00 (day 2)"}]
