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
