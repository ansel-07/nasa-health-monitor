# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Shared look (core/ui.py): mission status bar values."""
from datetime import datetime

import pytest

from core import ui


@pytest.mark.parametrize("minutes,expected", [
    (0, "<1 S"), (0.0211, "1 S"), (0.5, "30 S"), (22, "22 MIN"), (3.4, "3 MIN"),
    (None, None), ("TODO_EDU", None), (True, None), (-1, None),
])
def test_format_delay(minutes, expected):
    assert ui.format_delay(minutes) == expected


def test_status_items_show_day_time_and_delay():
    items = ui.status_items("Astronaut A", {"name": "Mars Base", "comm_delay_min": 22},
                            datetime(2027, 4, 3, 8, 0), datetime(2027, 4, 1))
    assert items == [("", "Astronaut A"), ("", "Mars Base"), ("Mission day", "3"),
                     ("", "2027-04-03 08:00"), ("One-way delay", "22 MIN")]


def test_status_items_skip_an_unknown_delay():
    items = ui.status_items("A", {"name": "Moon"}, datetime(2027, 4, 1), datetime(2027, 4, 1))
    assert [label for label, _ in items] == ["", "", "Mission day", ""]


def _band(severity, low, high):
    return {"severity": severity, "low": low, "high": high, "label": severity.capitalize()}


def test_band_status_picks_the_most_serious_band_containing_the_value():
    bands = [_band("watch", 320, None), _band("concern", 340, None)]   # least serious first
    assert ui.band_status(bands, 330)["severity"] == "watch"
    assert ui.band_status(bands, 360)["severity"] == "concern"
    assert ui.band_status(bands, 300) is None and ui.band_status(bands, None) is None


def test_band_status_handles_lower_bounds():
    assert ui.band_status([_band("watch", None, 50)], 40)["severity"] == "watch"


@pytest.mark.parametrize("level,color", [(100, ui.NORMAL), (80, ui.NORMAL), (70, ui.WATCH),
                                         (40, ui.WATCH), (30, ui.URGENCY), (0, ui.URGENCY)])
def test_level_color(level, color):
    assert ui.level_color(level) == color


def test_card_is_one_button_with_its_label():
    from streamlit.testing.v1 import AppTest

    def script():
        import streamlit as st
        from core import ui
        if ui.card("menu_x", "Trends", "show_chart", "3 indicators tracked", 70):
            st.session_state["clicked"] = True

    app = AppTest.from_function(script).run()
    assert not app.exception and [b.label for b in app.button] == ["Trends"]
    assert [p.value for p in app.get("progress")] == [70]
    app.button[0].click().run()
    assert app.session_state["clicked"]
