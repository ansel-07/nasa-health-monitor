# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: implementation generated with Claude Code and reviewed by Fran.
"""Activity bars and subjective issues. Owner: Fran.

Contract: AGENTS.md 5.6 and 7; product rules: docs/ASTRONAUT_HEALTH_APP_SPEC.md section 4.
A bar shows how recently an activity was done (check-in or protocol tutorial), NOT a health
status. Values are BAR_LEVELS (100..0 in 10-point steps), computed from the last completion
time and the MISSION clock (core.mission.now()), never from a running timer.

- Check-in bars go 100 -> 0 in checkins.json "bar_full_hours"; persistent subjective issues
  linked to that check-in make it faster ("speed_multiplier") from the moment they become
  persistent ("persistence_days" distinct calendar days with a report), never retroactively.
  Several persistent issues on the same check-in do not stack: the multiplier applies once.
- Tutorial bars go 100 -> 0 in problems.json "tutorial_bar_full_days" of that protocol. While
  that value is still TODO the bar shows 0 (due): it never blocks and no duration is invented.
- Never completed = 0 ("Not completed yet"), so a first check-in or tutorial is always possible.
- Stored per astronaut in data/activity.json through models.data_file() (AGENTS.md 5.5):
  {"astronauts": {astronaut: {"completions": {kind: {activity_id: ISO time}},
                              "issues": [{"issue", "since", "reports": [{"day", "at", "source"}],
                                          "persistent_since", "resolved_at"}]}}}
"""
import json
import os
import tempfile
from datetime import datetime, timedelta
from numbers import Real

from core import config, mission, models
from core.models import ACTIVITY_KINDS, BAR_LEVELS, TUTORIAL_REPEAT_BELOW

ISSUE_SOURCES = ["check_in_list", "check_in_detail"]
STEPS = len(BAR_LEVELS) - 1   # 10 steps of 10 points from 100 to 0


# --- storage ---------------------------------------------------------------------------------

def _read() -> dict:
    path = models.data_file(models.ACTIVITY_FILE)
    if not path.exists() or path.stat().st_size == 0:
        return {"astronauts": {}}
    with path.open(encoding="utf-8") as f:
        content = json.load(f)
    content.setdefault("astronauts", {})
    return content


def _write(content: dict) -> None:
    """Write safely: temporary file first, then replace the old one."""
    path = models.data_file(models.ACTIVITY_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".activity-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _astronaut(content: dict, astronaut: str) -> dict:
    record = content["astronauts"].setdefault(astronaut, {})
    record.setdefault("completions", {kind: {} for kind in ACTIVITY_KINDS})
    record.setdefault("issues", [])
    for kind in ACTIVITY_KINDS:
        record["completions"].setdefault(kind, {})
    return record


def _now_iso() -> str:
    return mission.now().isoformat(timespec="seconds")


# --- bars ------------------------------------------------------------------------------------

def _is_number(x) -> bool:
    return isinstance(x, Real) and not isinstance(x, bool)


def _check_kind(kind: str) -> None:
    if kind not in ACTIVITY_KINDS:
        raise ValueError(f"Unknown activity kind {kind!r} (expected one of {ACTIVITY_KINDS})")


def _full_duration(kind: str, activity_id: str) -> timedelta | None:
    """Time from 100 to 0 for this activity; None while the configured value is still TODO."""
    if kind == "check_in":
        checkins = config.load_checkins(include_examples=True)
        if activity_id not in checkins:
            raise ValueError(f"Unknown check-in {activity_id!r}")
        hours = checkins[activity_id].get("bar_full_hours")
        return timedelta(hours=hours) if _is_number(hours) and hours > 0 else None
    problems = config.load_problems(include_examples=True)
    if activity_id not in problems:
        raise ValueError(f"Unknown protocol {activity_id!r}")
    days = problems[activity_id].get("tutorial_bar_full_days")
    return timedelta(days=days) if _is_number(days) and days > 0 else None


def _accelerated_time(record: dict, checkin_id: str, start: datetime, end: datetime) -> timedelta:
    """Time in [start, end] during which a persistent issue linked to this check-in was active.

    Overlapping issues are merged, so the multiplier is applied once, not stacked.
    """
    links = config.load_subjective_issues(include_examples=True).get("issues", {})
    spans = []
    for item in record["issues"]:
        if not item.get("persistent_since") or checkin_id not in links.get(item["issue"], {}).get("check_ins", []):
            continue
        a = max(start, datetime.fromisoformat(item["persistent_since"]))
        b = min(end, datetime.fromisoformat(item["resolved_at"]) if item.get("resolved_at") else end)
        if b > a:
            spans.append((a, b))
    total, current = timedelta(0), None
    for a, b in sorted(spans):
        if current and a <= current[1]:
            current = (current[0], max(current[1], b))
        else:
            if current:
                total += current[1] - current[0]
            current = (a, b)
    if current:
        total += current[1] - current[0]
    return total


def bar_level(astronaut: str, kind: str, activity_id: str) -> int:
    """Current bar of one activity: a value of BAR_LEVELS. kind: "check_in" | "tutorial"."""
    _check_kind(kind)
    full = _full_duration(kind, activity_id)
    record = _astronaut(_read(), astronaut)
    completed = record["completions"][kind].get(activity_id)
    if completed is None or full is None:
        return 0   # never completed, or duration still TODO: due, never blocks
    start, now = datetime.fromisoformat(completed), mission.now()
    if now <= start:
        return 100   # completed now, or a completion stored after the current clock
    elapsed = now - start
    if kind == "check_in":
        settings = config.load_subjective_issues(include_examples=True).get("settings", {})
        multiplier = settings.get("speed_multiplier", 1)
        if _is_number(multiplier) and multiplier > 1:
            elapsed += (multiplier - 1) * _accelerated_time(record, activity_id, start, now)
    steps = int(elapsed / (full / STEPS))
    return max(0, 100 - 10 * steps)


def complete(astronaut: str, kind: str, activity_id: str) -> None:
    """Record that the astronaut completed the activity now (mission time): its bar goes to 100."""
    _check_kind(kind)
    _full_duration(kind, activity_id)   # validates the id
    content = _read()
    _astronaut(content, astronaut)["completions"][kind][activity_id] = _now_iso()
    _write(content)


def can_repeat_tutorial(astronaut: str, protocol_id: str) -> bool:
    """A tutorial can be done when its bar is strictly below TUTORIAL_REPEAT_BELOW (80)."""
    return bar_level(astronaut, "tutorial", protocol_id) < TUTORIAL_REPEAT_BELOW


# --- subjective issues -----------------------------------------------------------------------

def _active_record(record: dict, issue_id: str) -> dict | None:
    for item in record["issues"]:
        if item["issue"] == issue_id and not item.get("resolved_at"):
            return item
    return None


def report_issues(astronaut: str, issue_ids: list[str], source: str) -> None:
    """Record subjective issues the astronaut has now. source: "check_in_list" | "check_in_detail".

    Reporting an issue that is already active does not create a duplicate: it adds the day to
    its reports (once per calendar day). On the report that reaches "persistence_days" distinct
    days, the issue becomes persistent from that moment. An issue never opens an episode.
    """
    if source not in ISSUE_SOURCES:
        raise ValueError(f"Unknown source {source!r} (expected one of {ISSUE_SOURCES})")
    content_config = config.load_subjective_issues(include_examples=True)
    unknown = [i for i in issue_ids if i not in content_config.get("issues", {})]
    if unknown:
        raise ValueError(f"Unknown subjective issues: {unknown}")
    persistence_days = content_config.get("settings", {}).get("persistence_days")
    now = _now_iso()
    day = now[:10]
    content = _read()
    record = _astronaut(content, astronaut)
    for issue_id in dict.fromkeys(issue_ids):   # same id twice in one call counts once
        item = _active_record(record, issue_id)
        if item is None:
            item = {"issue": issue_id, "since": now, "reports": [], "persistent_since": None,
                    "resolved_at": None}
            record["issues"].append(item)
        if all(r["day"] != day for r in item["reports"]):
            item["reports"].append({"day": day, "at": now, "source": source})
        if (item["persistent_since"] is None and _is_number(persistence_days)
                and len(item["reports"]) >= persistence_days):
            item["persistent_since"] = now
    _write(content)


def resolve_issue(astronaut: str, issue_id: str) -> None:
    """Mark an issue as no longer present: its acceleration stops from now on (no refill)."""
    content = _read()
    item = _active_record(_astronaut(content, astronaut), issue_id)
    if item is None:
        return
    item["resolved_at"] = _now_iso()
    _write(content)


def active_issues(astronaut: str) -> list[dict]:
    """Active issues: [{"issue", "since", "persistent": bool}]."""
    record = _astronaut(_read(), astronaut)
    return [{"issue": item["issue"], "since": item["since"], "persistent": bool(item["persistent_since"])}
            for item in record["issues"] if not item.get("resolved_at")]
