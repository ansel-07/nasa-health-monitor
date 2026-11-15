# AI-assisted: generated with Claude Code and reviewed by Fran.
"""Activity bars and subjective issues (core/activity.py, AGENTS.md 5.6, spec sections 4 and 6).

Synthetic config and a controllable mission clock; temporary files only, never data/.
Durations and settings here are FAKE test values, not demo or medical decisions.
"""
import json
from datetime import datetime, timedelta

import pytest

from core import activity, config, data, mission, models

T0 = datetime(2027, 4, 1, 8, 0)

CHECKINS = {"c1": {"name": "C1", "indicators": ["x"], "bar_full_hours": 10},   # 1 h per step
            "c2": {"name": "C2", "indicators": ["y"], "bar_full_hours": 20},
            "c_todo": {"name": "C?", "indicators": ["z"], "bar_full_hours": "TODO_EDU"}}
PROBLEMS = {"p1": {"tutorial_bar_full_days": 10},                               # 1 day per step
            "p_todo": {"tutorial_bar_full_days": "TODO_EDU"}}
ISSUES = {"settings": {"persistence_days": 3, "speed_multiplier": 2},
          "issues": {"headache": {"label": "Headache", "check_ins": ["c1"]},
                     "dizzy": {"label": "Dizzy", "check_ins": ["c1"]},
                     "unmapped": {"label": "Unmapped", "check_ins": []}}}


class Clock:
    def __init__(self):
        self.now = T0

    def __call__(self):
        return self.now

    def move(self, **delta):
        self.now += timedelta(**delta)


@pytest.fixture
def clock(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "ACTIVITY_FILE", tmp_path / "activity.json")
    monkeypatch.setattr(config, "load_checkins", lambda include_examples=False: CHECKINS)
    monkeypatch.setattr(config, "load_problems", lambda include_examples=False: PROBLEMS)
    monkeypatch.setattr(config, "load_subjective_issues", lambda include_examples=False: ISSUES)
    c = Clock()
    monkeypatch.setattr(mission, "now", c)
    return c


# --- bars ------------------------------------------------------------------------------------

def test_never_completed_is_zero_and_tutorial_available(clock):
    assert activity.bar_level("a1", "check_in", "c1") == 0
    assert activity.bar_level("a1", "tutorial", "p1") == 0
    assert activity.can_repeat_tutorial("a1", "p1") is True


def test_check_in_bar_steps_down_every_tenth_of_the_full_time(clock):
    activity.complete("a1", "check_in", "c1")
    expected = {0: 100, 59: 100, 60: 90, 119: 90, 120: 80, 180: 70, 9 * 60 + 59: 10, 600: 0, 900: 0}
    for minutes, level in expected.items():
        clock.now = T0 + timedelta(minutes=minutes)
        assert activity.bar_level("a1", "check_in", "c1") == level, minutes


def test_tutorial_gate_at_exactly_80_and_just_below(clock):
    activity.complete("a1", "tutorial", "p1")
    assert (activity.bar_level("a1", "tutorial", "p1"), activity.can_repeat_tutorial("a1", "p1")) == (100, False)
    clock.move(days=2)
    assert (activity.bar_level("a1", "tutorial", "p1"), activity.can_repeat_tutorial("a1", "p1")) == (80, False)
    clock.move(days=1)
    assert (activity.bar_level("a1", "tutorial", "p1"), activity.can_repeat_tutorial("a1", "p1")) == (70, True)
    clock.move(days=30)
    assert activity.bar_level("a1", "tutorial", "p1") == 0   # never negative
    activity.complete("a1", "tutorial", "p1")
    assert activity.bar_level("a1", "tutorial", "p1") == 100


def test_activities_and_astronauts_are_independent(clock):
    activity.complete("a1", "check_in", "c1")
    clock.move(hours=4)
    activity.complete("a1", "check_in", "c2")
    assert activity.bar_level("a1", "check_in", "c1") == 60
    assert activity.bar_level("a1", "check_in", "c2") == 100
    assert activity.bar_level("a2", "check_in", "c1") == 0          # astronaut switch
    assert activity.bar_level("a1", "tutorial", "p1") == 0
    stored = json.loads(models.ACTIVITY_FILE.read_text(encoding="utf-8"))
    assert set(stored["astronauts"]) == {"a1"}


def test_todo_duration_shows_due_and_never_blocks(clock):
    activity.complete("a1", "tutorial", "p_todo")
    activity.complete("a1", "check_in", "c_todo")
    assert activity.bar_level("a1", "tutorial", "p_todo") == 0
    assert activity.can_repeat_tutorial("a1", "p_todo") is True
    assert activity.bar_level("a1", "check_in", "c_todo") == 0


def test_completion_after_the_clock_shows_full(clock):
    activity.complete("a1", "check_in", "c1")
    clock.move(hours=-5)   # e.g. a stored time later than the current clock
    assert activity.bar_level("a1", "check_in", "c1") == 100


@pytest.mark.parametrize("call", [
    lambda: activity.bar_level("a1", "walk", "c1"),
    lambda: activity.bar_level("a1", "check_in", "nope"),
    lambda: activity.bar_level("a1", "tutorial", "nope"),
    lambda: activity.complete("a1", "check_in", "nope"),
    lambda: activity.report_issues("a1", ["nope"], "check_in_list"),
    lambda: activity.report_issues("a1", ["headache"], "somewhere"),
])
def test_invalid_input_raises(clock, call):
    with pytest.raises(ValueError):
        call()
    assert not models.ACTIVITY_FILE.exists()


def test_bars_drain_with_the_real_mission_clock(tmp_path, monkeypatch):
    """Advancing mission time (not real time) drains the bars."""
    monkeypatch.setattr(models, "ACTIVITY_FILE", tmp_path / "activity.json")
    monkeypatch.setattr(models, "MISSION_STATE_FILE", tmp_path / "mission_state.json")
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(mission, "load_mission", lambda: {"start": T0.isoformat()})
    monkeypatch.setattr(config, "load_checkins", lambda include_examples=False: CHECKINS)
    monkeypatch.setattr(config, "load_subjective_issues", lambda include_examples=False: ISSUES)
    activity.complete("a1", "check_in", "c1")
    mission.advance(hours=3)
    assert activity.bar_level("a1", "check_in", "c1") == 70


def test_reset_demo_clears_bars_and_issues(clock, tmp_path, monkeypatch):
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "activity.json").write_text('{"astronauts": {}}\n')
    monkeypatch.setattr(models, "SEED_DIR", seed)
    monkeypatch.setattr(models, "DATA_DIR", tmp_path)
    activity.complete("a1", "check_in", "c1")
    activity.report_issues("a1", ["headache"], "check_in_list")
    data.reset_demo()
    assert activity.bar_level("a1", "check_in", "c1") == 0
    assert activity.active_issues("a1") == []


def test_repository_seed_has_an_empty_activity_file():
    seed = json.loads((models.SEED_DIR / "activity.json").read_text(encoding="utf-8"))
    assert seed == {"astronauts": {}}


# --- subjective issues -----------------------------------------------------------------------

def test_issue_becomes_persistent_on_the_third_distinct_day(clock):
    activity.report_issues("a1", ["headache"], "check_in_list")
    clock.move(hours=2)
    activity.report_issues("a1", ["headache", "headache"], "check_in_detail")   # same day: no new day
    assert activity.active_issues("a1") == [{"issue": "headache", "since": "2027-04-01T08:00:00",
                                             "persistent": False, "details": None}]
    clock.move(days=1)
    activity.report_issues("a1", ["headache"], "check_in_list")
    assert activity.active_issues("a1")[0]["persistent"] is False
    clock.move(days=3)   # not necessarily consecutive days (AGENTS.md 5.6)
    activity.report_issues("a1", ["headache"], "check_in_detail")
    assert activity.active_issues("a1") == [{"issue": "headache", "since": "2027-04-01T08:00:00",
                                             "persistent": True, "details": None}]
    stored = json.loads(models.ACTIVITY_FILE.read_text(encoding="utf-8"))["astronauts"]["a1"]["issues"]
    assert len(stored) == 1 and [r["source"] for r in stored[0]["reports"]] == [
        "check_in_list", "check_in_list", "check_in_detail"]


def make_persistent(clock, issue="headache"):
    """Report on 3 distinct days; returns the moment it became persistent."""
    for _ in range(2):
        activity.report_issues("a1", [issue], "check_in_list")
        clock.move(days=1)
    activity.report_issues("a1", [issue], "check_in_list")
    return clock.now


def test_acceleration_starts_when_persistent_never_retroactively(clock):
    start = make_persistent(clock)                 # persistent from `start`
    clock.now = start - timedelta(hours=2)
    activity.complete("a1", "check_in", "c1")      # completed 2 h before it became persistent
    activity.complete("a1", "check_in", "c2")
    clock.now = start + timedelta(hours=2)
    # 4 h elapsed, 2 of them accelerated x2: 4 + 2 = 6 effective hours -> 40
    assert activity.bar_level("a1", "check_in", "c1") == 40
    assert activity.bar_level("a1", "check_in", "c2") == 80   # not linked: base rate (2 h per step)
    activity.complete("a1", "tutorial", "p1")
    clock.move(days=1)
    assert activity.bar_level("a1", "tutorial", "p1") == 90    # tutorials are never accelerated


def test_resolving_stops_acceleration_without_refill(clock):
    start = make_persistent(clock)
    activity.complete("a1", "check_in", "c1")      # at `start`
    clock.move(hours=2)                            # 2 h x2 = 4 effective -> 60
    assert activity.bar_level("a1", "check_in", "c1") == 60
    activity.resolve_issue("a1", "headache")
    assert activity.bar_level("a1", "check_in", "c1") == 60    # no refill
    clock.move(hours=2)                            # base rate again: 4 + 2 = 6 -> 40
    assert activity.bar_level("a1", "check_in", "c1") == 40
    assert activity.active_issues("a1") == []
    activity.resolve_issue("a1", "headache")       # resolving twice is harmless


def test_overlapping_issues_do_not_stack_and_unmapped_has_no_effect(clock):
    make_persistent(clock, "headache")
    clock.move(days=-2)
    make_persistent(clock, "dizzy")
    make_persistent(clock, "unmapped")
    activity.complete("a1", "check_in", "c1")
    clock.move(hours=2)                            # x2 once, not x3: 4 effective -> 60
    assert activity.bar_level("a1", "check_in", "c1") == 60


def test_reporting_again_after_resolving_starts_a_new_record(clock):
    make_persistent(clock)
    activity.resolve_issue("a1", "headache")
    clock.move(days=1)
    activity.report_issues("a1", ["headache"], "check_in_list")
    assert activity.active_issues("a1") == [{"issue": "headache", "since": clock.now.isoformat(),
                                             "persistent": False, "details": None}]


def test_details_attach_to_todays_report_and_the_latest_wins(clock):
    """Task 4: optional details of docs/sintomas_subjetivos_atrofia_SANS.md section 4."""
    activity.report_issues("a1", ["headache"], "check_in_list")
    activity.add_issue_details("a1", "headache", {"onset": "gradual", "trend": "stable", "impact": "none",
                                                  "intensity": 3, "notes": "  after exercise ", "context": ""})
    activity.add_issue_details("a1", "headache", {"onset": "sudden", "impact": "task_adapted"})
    assert activity.active_issues("a1")[0]["details"] == {"onset": "sudden", "impact": "task_adapted"}
    clock.move(days=1)
    with pytest.raises(ValueError):      # not reported today
        activity.add_issue_details("a1", "headache", {"trend": "worsening"})
    activity.report_issues("a1", ["headache"], "check_in_detail")
    activity.add_issue_details("a1", "headache", {"trend": "worsening", "notes": "worse today"})
    assert activity.active_issues("a1")[0]["details"] == {"trend": "worsening", "notes": "worse today"}
    stored = json.loads(models.ACTIVITY_FILE.read_text(encoding="utf-8"))["astronauts"]["a1"]["issues"][0]
    assert [r["details"] for r in stored["reports"]] == [
        {"onset": "sudden", "impact": "task_adapted"}, {"trend": "worsening", "notes": "worse today"}]


@pytest.mark.parametrize("details", [{"onset": "slow"}, {"impact": "bad"}, {"intensity": 11},
                                     {"intensity": True}, {"colour": "red"}, {"notes": 5}])
def test_invalid_details_raise(clock, details):
    activity.report_issues("a1", ["headache"], "check_in_list")
    with pytest.raises(ValueError):
        activity.add_issue_details("a1", "headache", details)


def test_details_need_an_active_issue_and_safety_rule(clock):
    with pytest.raises(ValueError):
        activity.add_issue_details("a1", "headache", {"onset": "sudden"})
    assert activity.needs_safety_assessment({"impact": "task_not_completed"})
    assert not activity.needs_safety_assessment({"impact": "task_adapted"})
    assert not activity.needs_safety_assessment(None)
