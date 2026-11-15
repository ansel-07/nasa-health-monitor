# AI-assisted: generated with Claude Code and reviewed by Ansel.
# AI-assisted: lifecycle implementation generated with Codex and reviewed by Juan Carlos.
"""Episode lifecycle: open, confirm, dismiss, pending list. Owner: Juan Carlos.

Rules: AGENTS.md, sections 5.4, 7 and 10. Storage goes through core/data.py only.
"""
from copy import deepcopy
from datetime import datetime, timedelta
from itertools import product
from math import isfinite
from numbers import Real

from core import conditions, config, data, mission, triggers
from core.models import MEASUREMENT_COLUMNS, OPEN_STATUSES, PROBLEM_STATES, SOURCES, SYMPTOM_LEVELS, severity_rank


def _priority(severity: str) -> int:
    """Transition queue: watch ties mild, medical_urgency ties severe.

    Legacy moderate remains between watch and urgency. This only orders work;
    it does not translate or change the stored state or any medical criterion.
    """
    if severity in PROBLEM_STATES:
        return {"no_concern": 0, "watch": 1, "medical_urgency": 3}[severity]
    return severity_rank(severity)


def _at(value) -> datetime:
    try:
        at = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Expected an ISO 8601 mission timestamp.") from None
    if at.tzinfo is not None:
        raise ValueError("Mission timestamps must not include a timezone.")
    return at


def _finite(value) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


def _measurement(measurement: dict, now: datetime) -> dict:
    if not isinstance(measurement, dict) or any(k not in measurement for k in MEASUREMENT_COLUMNS):
        raise ValueError("Measurement must contain all measurement columns.")
    m = {key: measurement[key] for key in MEASUREMENT_COLUMNS}
    for key in ("astronaut", "indicator", "unit"):
        if not isinstance(m[key], str) or not m[key].strip() or m[key].startswith("TODO"):
            raise ValueError(f"Measurement {key} is missing or still TODO.")
    if m["phase"] != "mission" or m["source"] not in SOURCES or not _finite(m["value"]):
        raise ValueError("Expected a finite new mission measurement with a supported source.")
    errors = config.measurement_errors(m)
    if errors:
        raise ValueError(" ".join(errors))
    at = _at(m["timestamp"])
    if at > now:
        raise ValueError("Measurement cannot be later than the mission clock.")
    m["timestamp"] = at.isoformat()
    m["value"] = float(m["value"])
    return m


def _save_measurement_once(m: dict) -> None:
    rows = data.load_measurements(astronaut=m["astronaut"], indicator=m["indicator"])
    rows = rows[rows["timestamp"] == _at(m["timestamp"])]
    for row in rows.to_dict("records"):
        if all(
            row[key] == m[key] for key in MEASUREMENT_COLUMNS if key != "timestamp"
        ):
            return
    data.add_measurement(m)


def _open(episodes: list[dict], astronaut: str) -> dict | None:
    opened = [e for e in episodes if e["astronaut"] == astronaut and e["status"] in OPEN_STATUSES]
    if len(opened) > 1:
        raise ValueError("Astronaut has multiple open episodes; repair the stored state first.")
    return opened[0] if opened else None


def _wait(problem: dict) -> timedelta:
    minutes = problem.get("confirm_wait_min")
    if not _finite(minutes) or minutes < 0:
        raise ValueError("confirm_wait_min must be a configured non-negative number; resolve any TODO.")
    return timedelta(minutes=float(minutes))


def _new_episode(stored: list[dict], astronaut: str, environment: str, match: dict,
                 measured_at: str, now: datetime) -> dict:
    _wait(config.load_problems()[match["problem"]])
    numbers = [int(e["id"][3:]) for e in stored
               if e["id"].startswith("ep-") and e["id"][3:].isdigit()]
    return {
        "id": f"ep-{max(numbers, default=0) + 1:04d}", "astronaut": astronaut,
        "problem": match["problem"], "environment": environment,
        "status": "pending_confirmation", "severity_initial": match["severity"],
        "severity": match["severity"],
        "trigger": {"indicator": match["indicator"], "value": match["value"], "z": match["z"],
                    "measured_at": measured_at},
        "current_node": None, "vars": {}, "answers": {}, "log": [],
        "opened_at": now.isoformat(), "closed_at": None, "outcome": None,
        **({"symptoms": deepcopy(match["symptoms"])} if "symptoms" in match else {}),
    }


def _later_equal_time_evidence(m: dict, previous: dict) -> bool:
    """Use stored row order to distinguish a fresh same-time reading from a replay."""
    if (m["indicator"], m["value"]) == (previous["indicator"], previous["value"]):
        return True
    rows = data.load_measurements(astronaut=m["astronaut"])
    rows = rows[rows["timestamp"] == _at(m["timestamp"])]
    incoming = rows.index[(rows["indicator"] == m["indicator"]) & (rows["value"] == m["value"])]
    if incoming.empty:
        return True  # a fresh manual/protocol reading, not saved yet
    earlier = rows.index[(rows["indicator"] == previous["indicator"]) & (rows["value"] == previous["value"])]
    return earlier.empty or incoming[-1] > earlier[-1]


def _pending_items(items: list[dict], matches: list[dict], m: dict, exclude: str | None) -> list[dict]:
    """Keep one pending item per astronaut/problem, with the most recent evidence."""
    updated = deepcopy(items)
    for match in matches:
        if match["problem"] == exclude:
            continue
        item = {"astronaut": m["astronaut"], **match, "measured_at": m["timestamp"]}
        previous = next((p for p in updated if p["astronaut"] == item["astronaut"]
                         and p["problem"] == item["problem"]), None)
        if previous is None:
            updated.append(item)
        elif _at(item["measured_at"]) > _at(previous["measured_at"]) or (
            _at(item["measured_at"]) == _at(previous["measured_at"])
            and _later_equal_time_evidence(m, previous)
        ):
            previous.update(item)
    return [p for p in updated if not (p["astronaut"] == m["astronaut"] and p["problem"] == exclude)]


def _references(cond: dict, indicator: str) -> bool:
    if cond.get("indicator") == indicator:
        return True
    return any(_references(child, indicator) for op in ("all", "any", "of") for child in cond.get(op, []))


def _known_result(cond: dict, ctx: dict) -> bool | None:
    """Use three-valued logic so unavailable data cannot silently dismiss an episode."""
    if "count_at_least" in cond:
        values = [_known_result(child, ctx) for child in cond["of"]]
        known = sum(value is True for value in values)
        if known >= cond["count_at_least"]:
            return True
        return None if known + values.count(None) >= cond["count_at_least"] else False
    for op in ("all", "any"):
        if op in cond:
            values = [_known_result(child, ctx) for child in cond[op]]
            decisive = False if op == "all" else True
            if decisive in values:
                return decisive
            if None in values:
                return None
            return not decisive
    if "indicator" in cond:
        indicator = cond["indicator"]
        value = ctx["latest"].get(indicator)
        if conditions._metric_value(cond, ctx) is None:
            return None
        absolute = {k: v for k, v in cond.items() if k not in ("z_above", "z_below")}
        if len(absolute) > 1 and not conditions.check(absolute, ctx):
            return False
        if "z_above" in cond or "z_below" in cond:
            if not _finite(data.z_score(ctx["astronaut"], indicator, value)):
                return None
    return conditions.check(cond, ctx)


def _require_symptom_confirmation_data(problem: dict, ctx: dict, match: dict | None, indicator: str) -> None:
    """Block confirmation only when missing data could change the ordered state result."""
    possibilities = {}
    for sid, symptom in problem["symptoms"].items():
        levels = []
        for rule in symptom["levels"]:
            if "environments" in rule and ctx["environment"] not in rule["environments"]:
                continue
            result = _known_result(rule["when"], ctx)
            if match is None and result is None and _references(rule["when"], indicator):
                raise ValueError("Confirmation needs unavailable measurements or baseline data; episode remains pending.")
            if result is not False:
                levels.append(rule["level"])
            if result is True:
                break
        else:
            levels.append(SYMPTOM_LEVELS[0])
        possibilities[sid] = list(dict.fromkeys(levels))
    # No alert can also mean that this repeat is normal while another symptom
    # remains positive. Compare uncertain states with the actual latest state.
    current = {**ctx, "symptoms": triggers._symptom_levels(problem, ctx)}
    expected = next((rule["state"] for rule in problem["states"]
                     if conditions.check(rule["when"], current)), PROBLEM_STATES[0])
    for combination in product(*possibilities.values()):
        hypothetical = {**ctx, "symptoms": dict(zip(possibilities, combination))}
        state = next((rule["state"] for rule in problem["states"]
                      if conditions.check(rule["when"], hypothetical)), PROBLEM_STATES[0])
        if state != expected:
            raise ValueError("Confirmation needs unavailable measurements or baseline data; episode remains pending.")


def _require_confirmation_data(problem: dict, m: dict, environment: str, match: dict | None) -> None:
    latest = dict(data.latest_values(m["astronaut"]))
    latest[m["indicator"]] = m["value"]
    ctx = {"astronaut": m["astronaut"], "environment": environment, "latest": latest}
    if "symptoms" in problem or "states" in problem:
        _require_symptom_confirmation_data(problem, ctx, match, m["indicator"])
        return
    for trigger in problem["triggers"]:
        if "environments" in trigger and environment not in trigger["environments"]:
            continue
        if not _references(trigger["when"], m["indicator"]):
            continue
        if _known_result(trigger["when"], ctx) is None and (
            match is None or _priority(trigger["severity"]) > _priority(match["severity"])
        ):
            raise ValueError("Confirmation needs unavailable measurements or baseline data; episode remains pending.")


def on_new_measurement(measurement: dict, environment: str) -> dict | None:
    """Record one new mission measurement, opening at most one episode.

    Callers must not replay simulated history. Already stored protocol/simulated
    measurements are evaluated without appending another CSV row. An open
    episode is never confirmed or escalated here. Same-problem matches are
    suppressed while it is open. Other matches update the pending queue.
    """
    now = mission.now()
    m = _measurement(measurement, now)
    stored = data.load_episodes()
    opened = _open(stored, m["astronaut"])
    matches = triggers.evaluate(m, environment)
    # Replaying the evidence that originally opened an episode must not reopen it.
    matches = [match for match in matches if not any(
        e["astronaut"] == m["astronaut"] and e["problem"] == match["problem"]
        and e.get("trigger", {}).get("indicator") == m["indicator"]
        and e["trigger"].get("value") == m["value"]
        and _at(e["trigger"]["measured_at"]) == _at(m["timestamp"])
        for e in stored
    )]
    created = False
    if opened is None and matches:
        chosen = max(matches, key=lambda item: _priority(item["severity"]))
        opened = _new_episode(stored, m["astronaut"], environment, chosen, m["timestamp"], now)
        created = True
    pending = data.load_pending()
    updated = _pending_items(pending, matches, m, opened["problem"] if opened else None)
    _save_measurement_once(m)
    if created:
        data.save_episode(opened)
    if updated != pending:
        data.save_pending(updated)
    return deepcopy(opened)


def confirm(episode_id: str, measurement: dict) -> dict:
    """Confirm only the original problem using a later, explicitly submitted repeat.

    Both the repeat timestamp and mission clock must satisfy the configured
    wait from opened_at. Invalid repeats leave storage unchanged. Unevaluable
    repeats are retained without changing the episode or consuming pending alerts.
    Confirmation sets severity from the repeat; subsequent changes belong to
    protocol set_severity nodes. Call accept_pending separately to review the queue.
    """
    stored = data.load_episodes()
    episode = next((e for e in stored if e["id"] == episode_id), None)
    if episode is None or episode["status"] != "pending_confirmation":
        raise ValueError("Confirmation requires an existing pending_confirmation episode.")
    _open(stored, episode["astronaut"])
    now = mission.now()
    m = _measurement(measurement, now)
    if m["astronaut"] != episode["astronaut"] or m["indicator"] != episode["trigger"]["indicator"]:
        raise ValueError("Repeat the same indicator for the same astronaut.")
    problem = config.load_problems()[episode["problem"]]
    ready = _at(episode["opened_at"]) + _wait(problem)
    at = _at(m["timestamp"])
    if at <= _at(episode["trigger"]["measured_at"]) or at < ready or now < ready:
        raise ValueError("Repeat measurement must be later than the original and after confirm_wait_min.")
    matches = triggers.evaluate(m, episode["environment"])
    match = next((item for item in matches if item["problem"] == episode["problem"]), None)
    try:
        _require_confirmation_data(problem, m, episode["environment"], match)
    except ValueError as error:
        _save_measurement_once(m)
        raise ValueError(f"Repeat measurement recorded. {error}") from error
    updated = deepcopy(episode)
    if match is not None:
        updated.update(status="active", severity=match["severity"],
                       current_node=config.load_protocol(episode["problem"])["start"])
        if "symptoms" in match:
            updated["symptoms"] = deepcopy(match["symptoms"])
    else:
        updated.update(status="dismissed", closed_at=now.isoformat())
        if "symptoms" in problem:
            latest = dict(data.latest_values(m["astronaut"]))
            latest[m["indicator"]] = m["value"]
            updated["symptoms"] = triggers._symptom_levels(problem, {
                "astronaut": m["astronaut"], "environment": episode["environment"], "latest": latest,
            })
    pending = data.load_pending()
    new_pending = _pending_items(pending, matches, m, episode["problem"])
    _save_measurement_once(m)
    # Keep confirmation retryable until its queue changes have been saved.
    if new_pending != pending:
        data.save_pending(new_pending)
    data.save_episode(updated)
    return updated


def get_pending(astronaut: str) -> list[dict]:
    """Read pending items by descending severity, preserving queue order on ties.

    This function never opens episodes. Use accept_pending to begin a new
    confirmation wait for the highest-priority pending alert.
    """
    return sorted(data.load_pending(astronaut), key=lambda item: _priority(item["severity"]), reverse=True)


def accept_pending(astronaut: str, environment: str) -> dict | None:
    """Accept the most severe pending alert, starting confirmation at mission.now().

    Additive public contract for Check-in. Ties preserve queue order. Returns
    the existing open episode without changing storage if one is already open,
    or None if there are no real pending alerts for this astronaut. The supplied
    current environment is used because pending records have no environment.
    Original evidence is preserved; accepting never records a new measurement,
    confirms an alert or runs a protocol. Other pending items remain untouched.
    """
    if not isinstance(astronaut, str) or not astronaut.strip():
        raise ValueError("Accepting an alert requires an astronaut.")
    stored = data.load_episodes()
    opened = _open(stored, astronaut)
    if opened is not None:
        return deepcopy(opened)
    pending = data.load_pending()
    candidates = [(index, item) for index, item in enumerate(pending)
                  if item["astronaut"] == astronaut and not item["problem"].startswith("_")]
    if not candidates:
        return None
    index, chosen = max(candidates, key=lambda pair: _priority(pair[1]["severity"]))
    if not isinstance(environment, str) or environment not in config.load_environments():
        raise ValueError("Accepting an alert requires a configured mission environment.")
    if chosen["problem"] not in config.load_problems():
        raise ValueError("The pending problem is unavailable in the configuration.")
    indicator = chosen.get("indicator")
    if not isinstance(indicator, str) or indicator.startswith("_") or indicator not in config.load_indicators():
        raise ValueError("The pending indicator is unavailable in the configuration.")
    if not _finite(chosen.get("value")) or (chosen.get("z") is not None and not _finite(chosen["z"])):
        raise ValueError("The pending measurement contains invalid numeric evidence.")
    now = mission.now()
    measured_at = _at(chosen.get("measured_at"))
    if measured_at > now:
        raise ValueError("Pending evidence cannot be later than the mission clock.")
    opened = _new_episode(stored, astronaut, environment, chosen, measured_at.isoformat(), now)
    # Save the episode first so a storage failure cannot silently discard the alert.
    data.save_episode(opened)
    data.save_pending(pending[:index] + pending[index + 1:])
    return opened
