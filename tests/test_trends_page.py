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
    (tmp_path / "astronauts.csv").write_text("id,name,role\na1,Astronaut A,Commander\n")
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
