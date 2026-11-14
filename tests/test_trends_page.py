# AI-assisted: generated with Claude Code and reviewed by Fran.
"""Trends page (pages/3_Trends.py) with Streamlit's AppTest. Temporary files, synthetic values."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import charts, config, episodes, models

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


def metrics(app):
    return {m.label: m.value for m in app.metric}


def test_needs_an_astronaut():
    app = AppTest.from_file(str(PAGE)).run()
    assert app.warning[0].value == "Choose an astronaut on the Home page first."


def test_indicator_list_hides_fixtures_and_todo_names(screen):
    app, calls, _ = screen
    app.run()
    assert not app.exception
    box = app.selectbox[0]
    assert box.options == ["Indicator X", "y"]
    assert app.caption[0].value == "Astronaut A · Mars"
    assert calls[-1] == ("a1", "x", False, "mars")  # full chart, with the environment


def test_metrics_without_data(screen):
    app, _, _ = screen
    app.run()
    assert metrics(app) == {"Latest value": "—", "Personal baseline (pre-flight)": "—",
                            "Distance from baseline (z)": "—"}


def test_metrics_with_data(screen):
    app, _, folder = screen
    write_measurements(folder, [
        "2027-03-01T08:00:00,a1,x,60,u,preflight,simulated",
        "2027-03-02T08:00:00,a1,x,62,u,preflight,simulated",
        "2027-03-03T08:00:00,a1,x,64,u,preflight,simulated",
        "2027-04-10T08:00:00,a1,x,66,u,mission,manual",
    ])
    app.run()
    assert metrics(app) == {"Latest value": "66.0 u", "Personal baseline (pre-flight)": "62.0 ± 2.0 u",
                            "Distance from baseline (z)": "+2.0"}


def test_changing_indicator_redraws_chart(screen):
    app, calls, _ = screen
    app.run()
    app.selectbox[0].select("y").run()
    assert not app.exception
    assert calls[-1] == ("a1", "y", False, "mars")


# --- Demo controls: advance mission ------------------------------------------------------

def simulated(folder):
    """Day-1 and day-2 mission rows (fake values), hidden until the clock reaches them."""
    write_measurements(folder, [
        "2027-03-30T08:00:00,a1,x,60,u,preflight,simulated",
        "2027-04-01T08:00:00,a1,x,61,u,mission,simulated",
        "2027-04-01T08:00:00,a2,x,90,u,mission,simulated",
        "2027-04-02T08:00:00,a1,x,62,u,mission,simulated",
    ])


@pytest.fixture
def detection(monkeypatch):
    """Fake episode detection: records calls; opens an episode for values above 80."""
    calls = []

    def on_new(measurement, environment):
        calls.append((measurement["astronaut"], measurement["value"], environment))
        if measurement["value"] > 80:
            from core import data
            data.save_episode({"id": f"ep-{len(calls)}", "astronaut": measurement["astronaut"],
                               "problem": "p", "status": "pending_confirmation"})

    monkeypatch.setattr(episodes, "on_new_measurement", on_new)
    return calls


def advance_button(app):
    return next(b for b in app.button if b.label == "Advance 24 h")


def test_demo_controls_show_mission_time(screen):
    app, _, _ = screen
    app.run()
    assert not app.exception
    assert any("2027-04-01 00:00" in m.value and "day 1" in m.value for m in app.markdown)


def test_advance_reveals_a_day_and_sends_it_to_detection(screen, detection):
    app, _, folder = screen
    simulated(folder)
    app.run()
    advance_button(app).click().run()
    assert not app.exception
    assert any("2027-04-02 00:00" in m.value and "day 2" in m.value for m in app.markdown)
    assert detection == [("a1", 61.0, "mars"), ("a2", 90.0, "mars")]  # every astronaut, day 1 only
    assert "2 new simulated measurement(s)" in app.warning[0].value
    assert "New alert for: Astronaut B." in app.warning[0].value
    assert "Go to Check-in" not in [b.label for b in app.button]  # the alert is not ours

    advance_button(app).click().run()
    assert detection[-1] == ("a1", 62.0, "mars")
    assert app.info[0].value.endswith("1 new simulated measurement(s).")


def test_alert_for_current_astronaut_offers_check_in(screen, detection, monkeypatch):
    app, _, folder = screen
    simulated(folder)
    app.session_state["astronaut"] = "a2"
    app.run()
    advance_button(app).click().run()
    assert "New alert for: Astronaut B." in app.warning[0].value
    assert "Go to Check-in" in [b.label for b in app.button]


def test_detection_error_is_reported(screen, monkeypatch):
    app, _, folder = screen
    simulated(folder)

    def broken(measurement, environment):
        raise ValueError("problem config incomplete")

    monkeypatch.setattr(episodes, "on_new_measurement", broken)
    app.run()
    advance_button(app).click().run()
    assert not app.exception
    assert "detection failed: problem config incomplete" in app.error[0].value


# --- Alert history -------------------------------------------------------------------------

def test_history_without_alerts(screen):
    app, _, _ = screen
    app.run()
    assert not app.exception
    assert [s.value for s in app.subheader] == ["Alert history"]
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
