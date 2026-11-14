# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Activity bars and subjective issues. Owner: Fran.

Contract: AGENTS.md 5.6 and 7; product rules: docs/ASTRONAUT_HEALTH_APP_SPEC.md section 4.
A bar shows how recently an activity was done (check-in or protocol tutorial), NOT a health
status. Values are BAR_LEVELS (100..0 in 10-point steps), computed from the last completion
time and the MISSION clock (core.mission.now()), never from a running timer.

- Check-in bars go 100 -> 0 in checkins.json "bar_full_hours"; persistent subjective issues
  linked to that check-in make it faster ("speed_multiplier") from the moment they become
  persistent ("persistence_days" calendar days), never retroactively.
- Tutorial bars go 100 -> 0 in problems.json "tutorial_bar_full_days" of that protocol.
- Never completed = 0 ("Not completed yet"), so a first check-in or tutorial is always possible.
- Stored per astronaut in data/activity.json through models.data_file() (AGENTS.md 5.5).
"""
from core.models import TUTORIAL_REPEAT_BELOW


def bar_level(astronaut: str, kind: str, activity_id: str) -> int:
    """Current bar of one activity: a value of BAR_LEVELS. kind: "check_in" | "tutorial"."""
    # STUB (Fran): compute from the stored last completion and mission.now().
    return 0


def complete(astronaut: str, kind: str, activity_id: str) -> None:
    """Record that the astronaut completed the activity now (mission time): its bar goes to 100."""
    # STUB (Fran): store the completion time.
    return None


def can_repeat_tutorial(astronaut: str, protocol_id: str) -> bool:
    """A tutorial can be done when its bar is strictly below TUTORIAL_REPEAT_BELOW (80)."""
    return bar_level(astronaut, "tutorial", protocol_id) < TUTORIAL_REPEAT_BELOW


def report_issues(astronaut: str, issue_ids: list[str], source: str) -> None:
    """Record subjective issues the astronaut has now. source: "check_in_list" | "check_in_detail".

    Reporting an issue that is already active does not create a duplicate.
    """
    # STUB (Fran): store {issue, astronaut, reported_at, active} records.
    return None


def resolve_issue(astronaut: str, issue_id: str) -> None:
    """Mark an issue as no longer present: its acceleration stops from now on (no refill)."""
    # STUB (Fran)
    return None


def active_issues(astronaut: str) -> list[dict]:
    """Active issues: [{"issue", "since", "persistent": bool}]."""
    # STUB (Fran)
    return []
