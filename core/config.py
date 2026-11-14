# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Load and validate the JSON files in config/. Owner: Ansel.

Run `python -m core.config` to validate everything and print the errors.
Files are read on every call (no cache) so edits show up when Streamlit reruns.
"""
import json
import sys

from core.models import (
    CONFIG_DIR,
    CONTACT_TARGETS,
    NODE_TYPES,
    OUTCOMES,
    CONDITION_METRICS,
    PROBLEM_STATES,
    PROTOCOLS_DIR,
    SEVERITIES,
    SYMPTOM_LEVELS,
    TODO_MARK,
)


def _read_json(path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_mission() -> dict:
    return _read_json(CONFIG_DIR / "mission.json")


def load_indicators() -> dict:
    return _read_json(CONFIG_DIR / "indicators.json")


def load_environments() -> dict:
    return _read_json(CONFIG_DIR / "environments.json")


def load_problems(include_examples: bool = False) -> dict:
    """Problems by id. Ids starting with "_" are test fixtures and are hidden by default."""
    problems = _read_json(CONFIG_DIR / "problems.json")
    if include_examples:
        return problems
    return {pid: p for pid, p in problems.items() if not pid.startswith("_")}


def load_checkins(include_examples: bool = False) -> dict:
    """Check-ins (groups of indicators measured together) by id; "_" ids are test fixtures."""
    checkins = _read_json(CONFIG_DIR / "checkins.json")
    if include_examples:
        return checkins
    return {cid: c for cid, c in checkins.items() if not cid.startswith("_")}


def load_subjective_issues(include_examples: bool = False) -> dict:
    """{"settings": {...}, "issues": {issue_id: {"label", "check_ins"}}}; "_" issues are fixtures."""
    content = _read_json(CONFIG_DIR / "subjective_issues.json")
    if not include_examples:
        content = {**content, "issues": {i: v for i, v in content.get("issues", {}).items()
                                         if not i.startswith("_")}}
    return content


def load_protocol(problem_id: str) -> dict:
    problem = load_problems(include_examples=True)[problem_id]
    return _read_json(CONFIG_DIR / problem["protocol"])


# ---------------------------------------------------------------- validation

def _node_targets(node: dict) -> list:
    """All node ids a node can jump to."""
    targets = []
    for key in ("next", "next_if_cannot", "default"):
        if key in node:
            targets.append(node[key])
    if isinstance(node.get("options"), dict):
        targets.extend(node["options"].values())
    for branch in node.get("branches", []) or []:
        if isinstance(branch, dict) and "next" in branch:
            targets.append(branch["next"])
    return targets


def _leaf_conditions(cond):
    """Every simple condition inside `cond`, looking through all / any / of."""
    if not isinstance(cond, dict):
        return
    nested = False
    for key in ("all", "any", "of"):
        if isinstance(cond.get(key), list):
            nested = True
            for child in cond[key]:
                yield from _leaf_conditions(child)
    if not nested:
        yield cond


def _check_condition_refs(cond, where: str, indicators: dict, symptoms) -> list:
    """Unknown indicators, symptoms and symptom levels used by a condition.

    symptoms=None means symptom conditions are not allowed here.
    """
    errors = []
    if isinstance(cond, dict) and "count_at_least" in cond:
        if not isinstance(cond.get("of"), list) or not cond["of"]:
            errors.append(f"{where}: 'count_at_least' needs a non-empty 'of' list")
        elif isinstance(cond["count_at_least"], int) and not 1 <= cond["count_at_least"] <= len(cond["of"]):
            errors.append(f"{where}: 'count_at_least' must be between 1 and the size of 'of'")
    for leaf in _leaf_conditions(cond):
        if "indicator" in leaf and leaf["indicator"] not in indicators:
            errors.append(f"{where}: unknown indicator '{leaf['indicator']}'")
        if "metric" in leaf:
            if leaf["metric"] not in CONDITION_METRICS:
                errors.append(f"{where}: unknown metric '{leaf['metric']}'")
            if "indicator" not in leaf and "var" not in leaf:
                errors.append(f"{where}: 'metric' needs an 'indicator' or 'var'")
            if "z_above" in leaf or "z_below" in leaf:
                errors.append(f"{where}: do not mix 'metric' with z_above / z_below; use metric z_score")
        if "symptom" in leaf:
            if symptoms is None:
                errors.append(f"{where}: symptom conditions are not allowed here")
            elif leaf["symptom"] not in symptoms:
                errors.append(f"{where}: unknown symptom '{leaf['symptom']}'")
            for key in ("level_at_least", "level_is"):
                if key in leaf and leaf[key] not in SYMPTOM_LEVELS:
                    errors.append(f"{where}: unknown symptom level '{leaf[key]}'")
    return errors


def validate_symptoms(problem: dict, where: str, indicators: dict, environments: dict) -> list:
    """Check the `symptoms` and `states` of a symptom-based problem (AGENTS.md, 5.3)."""
    errors = []
    symptoms = problem.get("symptoms")
    states = problem.get("states")
    if not isinstance(symptoms, dict) or not symptoms:
        return [f"{where}: 'symptoms' must be a non-empty object"]
    if not isinstance(states, list) or not states:
        errors.append(f"{where}: 'states' must be a non-empty list")
        states = []

    for sid, symptom in symptoms.items():
        swhere = f"{where}.symptoms[{sid}]"
        if not isinstance(symptom, dict):
            errors.append(f"{swhere}: must be an object")
            continue
        if "name" not in symptom:
            errors.append(f"{swhere}: missing 'name'")
        levels = symptom.get("levels")
        if not isinstance(levels, list) or not levels:
            errors.append(f"{swhere}: 'levels' must be a non-empty list")
            continue
        for i, rule in enumerate(levels):
            rwhere = f"{swhere}.levels[{i}]"
            if not isinstance(rule, dict) or "when" not in rule:
                errors.append(f"{rwhere}: needs 'level' and 'when'")
                continue
            if rule.get("level") not in SYMPTOM_LEVELS[1:]:
                errors.append(f"{rwhere}: level must be one of {SYMPTOM_LEVELS[1:]}")
            for env in rule.get("environments", []):
                if env not in environments:
                    errors.append(f"{rwhere}: unknown environment '{env}'")
            if not any("indicator" in leaf for leaf in _leaf_conditions(rule["when"])):
                errors.append(f"{rwhere}: 'when' must use at least one indicator")
            errors.extend(_check_condition_refs(rule["when"], rwhere, indicators, None))

    for i, rule in enumerate(states):
        rwhere = f"{where}.states[{i}]"
        if not isinstance(rule, dict) or "when" not in rule:
            errors.append(f"{rwhere}: needs 'state' and 'when'")
            continue
        if rule.get("state") not in PROBLEM_STATES[1:]:
            errors.append(f"{rwhere}: state must be one of {PROBLEM_STATES[1:]}")
        errors.extend(_check_condition_refs(rule["when"], rwhere, indicators, symptoms))
    return errors


def validate_protocol(protocol: dict, where: str, indicators: dict, symptoms: dict | None = None,
                      severities: list | None = None) -> list:
    errors = []
    allowed = SEVERITIES if severities is None else severities
    nodes = protocol.get("nodes")
    start = protocol.get("start")
    if not isinstance(nodes, dict) or not nodes:
        return [f"{where}: 'nodes' is missing or empty"]
    if start not in nodes:
        errors.append(f"{where}: start node '{start}' does not exist")

    for nid, node in nodes.items():
        ntype = node.get("type")
        if ntype not in NODE_TYPES:
            errors.append(f"{where}: node '{nid}' has unknown type '{ntype}'")
            continue
        for field in NODE_TYPES[ntype]:
            if field not in node:
                errors.append(f"{where}: node '{nid}' ({ntype}) is missing '{field}'")
        for target in _node_targets(node):
            if target not in nodes:
                errors.append(f"{where}: node '{nid}' points to missing node '{target}'")
        if ntype == "measure" and node.get("indicator") not in indicators:
            errors.append(f"{where}: node '{nid}' uses unknown indicator '{node.get('indicator')}'")
        if ntype == "set_severity" and node.get("severity") not in allowed:
            errors.append(f"{where}: node '{nid}' uses unknown severity '{node.get('severity')}'")
        if ntype == "end" and node.get("outcome") not in OUTCOMES:
            errors.append(f"{where}: node '{nid}' uses unknown outcome '{node.get('outcome')}'")
        if ntype == "contact" and node.get("target") not in CONTACT_TARGETS:
            errors.append(f"{where}: node '{nid}' uses unknown contact target '{node.get('target')}'")
        for i, branch in enumerate(node.get("branches", []) if ntype == "decision" else []):
            if isinstance(branch, dict):
                errors.extend(_check_condition_refs(
                    branch.get("if"), f"{where}: node '{nid}' branch {i}", indicators, symptoms))

    # Reachability from the start node.
    if start in nodes:
        seen, stack = set(), [start]
        while stack:
            nid = stack.pop()
            if nid in seen or nid not in nodes:
                continue
            seen.add(nid)
            stack.extend(_node_targets(nodes[nid]))
        for nid in nodes:
            if nid not in seen:
                errors.append(f"{where}: node '{nid}' is unreachable from start")
        if not any(nodes[n].get("type") == "end" for n in seen):
            errors.append(f"{where}: no 'end' node is reachable from start")
    return errors


def _contains_todo(value) -> bool:
    if isinstance(value, str):
        return value.startswith(TODO_MARK)
    if isinstance(value, dict):
        return any(_contains_todo(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_todo(v) for v in value)
    return False


def _positive_or_todo(value) -> bool:
    if isinstance(value, str):
        return value.startswith(TODO_MARK)
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def validate_activities(indicators: dict, problems: dict) -> list:
    """checkins.json, subjective_issues.json and the tutorial interval of each problem (AGENTS.md 5.6)."""
    errors = []
    try:
        checkins = load_checkins(include_examples=True)
        subjective = load_subjective_issues(include_examples=True)
    except (OSError, json.JSONDecodeError) as e:
        return [f"config: cannot read an activity file: {e}"]
    owner = {}
    for cid, checkin in checkins.items():
        where = f"checkins.json[{cid}]"
        if "name" not in checkin:
            errors.append(f"{where}: missing 'name'")
        ids = checkin.get("indicators")
        if not isinstance(ids, list) or not ids:
            errors.append(f"{where}: 'indicators' must be a non-empty list")
            ids = []
        for ind in ids:
            if ind not in indicators:
                errors.append(f"{where}: unknown indicator '{ind}'")
            elif ind in owner:
                errors.append(f"{where}: indicator '{ind}' is already in check-in '{owner[ind]}'")
            else:
                owner[ind] = cid
        if not _positive_or_todo(checkin.get("bar_full_hours")):
            errors.append(f"{where}: 'bar_full_hours' must be a positive number")
    settings = subjective.get("settings", {})
    for key in ("persistence_days", "speed_multiplier"):
        if not _positive_or_todo(settings.get(key)):
            errors.append(f"subjective_issues.json[settings]: '{key}' must be a positive number")
    for iid, issue in subjective.get("issues", {}).items():
        where = f"subjective_issues.json[{iid}]"
        if "label" not in issue:
            errors.append(f"{where}: missing 'label'")
        for cid in issue.get("check_ins", []):
            if cid not in checkins:
                errors.append(f"{where}: unknown check-in '{cid}'")
        if issue.get("alarm"):
            if not issue.get("action"):
                errors.append(f"{where}: an alarm needs an 'action'")
            if issue.get("check_ins"):
                errors.append(f"{where}: an alarm is not linked to check-ins")
    for pid, problem in problems.items():
        if "tutorial_bar_full_days" in problem and not _positive_or_todo(problem["tutorial_bar_full_days"]):
            errors.append(f"problems.json[{pid}]: 'tutorial_bar_full_days' must be a positive number")
    return errors


def validate_all(strict: bool = False) -> list:
    """Check every config file. Returns a list of error messages (empty = OK).

    strict=True also reports values still marked TODO in real (non-"_") problems,
    their protocols, indicators and environments. Use it before the demo.
    """
    errors = []
    try:
        indicators = load_indicators()
        environments = load_environments()
        problems = load_problems(include_examples=True)
        mission = load_mission()
    except (OSError, json.JSONDecodeError) as e:
        return [f"config: cannot read a file: {e}"]

    if mission.get("environment") not in environments:
        errors.append(f"mission.json: unknown environment '{mission.get('environment')}'")

    for pid, problem in problems.items():
        where = f"problems.json[{pid}]"
        for field in ("name", "protocol", "confirm_wait_min"):
            if field not in problem:
                errors.append(f"{where}: missing '{field}'")
        # TRANSITION: a problem uses the legacy 'triggers' or the new 'symptoms' + 'states'.
        if "symptoms" in problem or "states" in problem:
            errors.extend(validate_symptoms(problem, where, indicators, environments))
        elif "triggers" not in problem:
            errors.append(f"{where}: needs 'symptoms' and 'states' (or legacy 'triggers')")
        for i, trig in enumerate(problem.get("triggers", [])):
            if trig.get("severity") not in SEVERITIES:
                errors.append(f"{where}.triggers[{i}]: unknown severity '{trig.get('severity')}'")
            for env in trig.get("environments", []):
                if env not in environments:
                    errors.append(f"{where}.triggers[{i}]: unknown environment '{env}'")
            ind = (trig.get("when") or {}).get("indicator")
            if ind is not None and ind not in indicators:
                errors.append(f"{where}.triggers[{i}]: unknown indicator '{ind}'")
        path = PROTOCOLS_DIR.parent / problem.get("protocol", "")
        if not path.is_file():
            errors.append(f"{where}: protocol file '{problem.get('protocol')}' not found")
            continue
        protocol = _read_json(path)
        symptoms = problem.get("symptoms") if isinstance(problem.get("symptoms"), dict) else None
        # TRANSITION: symptom-based problems use PROBLEM_STATES, legacy ones SEVERITIES.
        severities = (PROBLEM_STATES if symptoms is not None else []) + (SEVERITIES if "triggers" in problem else [])
        errors.extend(validate_protocol(protocol, problem["protocol"], indicators, symptoms, severities))
        if strict and not pid.startswith("_"):
            if _contains_todo(problem):
                errors.append(f"{where}: still has TODO values")
            if _contains_todo(protocol):
                errors.append(f"{problem['protocol']}: still has TODO values")

    errors.extend(validate_activities(indicators, problems))

    if strict:
        for name, content in (("indicators.json", indicators), ("environments.json", environments)):
            for key, value in content.items():
                if not key.startswith("_") and _contains_todo(value):
                    errors.append(f"{name}[{key}]: still has TODO values")
        for cid, checkin in load_checkins().items():
            if _contains_todo(checkin):
                errors.append(f"checkins.json[{cid}]: still has TODO values")
    return errors


if __name__ == "__main__":
    strict = "--strict" in sys.argv
    problems_found = validate_all(strict=strict)
    for message in problems_found:
        print("ERROR:", message)
    print("OK" if not problems_found else f"{len(problems_found)} error(s)")
    sys.exit(1 if problems_found else 0)
