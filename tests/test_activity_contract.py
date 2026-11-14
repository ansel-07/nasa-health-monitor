# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Contract of core/activity.py (AGENTS.md 5.6). Fran replaces the stubs and adds behaviour tests."""
from core import activity
from core.models import BAR_LEVELS, TUTORIAL_REPEAT_BELOW


def test_bar_levels_are_ten_point_steps():
    assert BAR_LEVELS == list(range(100, -1, -10))


def test_never_completed_tutorial_can_be_done():
    assert activity.bar_level("a1", "tutorial", "_example") in BAR_LEVELS
    assert TUTORIAL_REPEAT_BELOW == 80


def test_tutorial_gate_is_strictly_below_80(monkeypatch):
    for level, allowed in ((100, False), (80, False), (70, True), (0, True)):
        monkeypatch.setattr(activity, "bar_level", lambda *args, level=level: level)
        assert activity.can_repeat_tutorial("a1", "_example") is allowed
