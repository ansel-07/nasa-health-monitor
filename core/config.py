# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Load and validate the JSON files in config/. Owner: Rol 3.

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
    PROTOCOLS_DIR,
    SEVERITIES,
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


def validate_protocol(protocol: dict, where: str, indicators: dict) -> list:
    errors = []
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
        if ntype == "set_severity" and node.get("severity") not in SEVERITIES:
            errors.append(f"{where}: node '{nid}' uses unknown severity '{node.get('severity')}'")
        if ntype == "end" and node.get("outcome") not in OUTCOMES:
            errors.append(f"{where}: node '{nid}' uses unknown outcome '{node.get('outcome')}'")
        if ntype == "contact" and node.get("target") not in CONTACT_TARGETS:
            errors.append(f"{where}: node '{nid}' uses unknown contact target '{node.get('target')}'")

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
        for field in ("name", "protocol", "triggers", "confirm_wait_min"):
            if field not in problem:
                errors.append(f"{where}: missing '{field}'")
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
        errors.extend(validate_protocol(protocol, problem["protocol"], indicators))
        if strict and not pid.startswith("_"):
            if _contains_todo(problem):
                errors.append(f"{where}: still has TODO values")
            if _contains_todo(protocol):
                errors.append(f"{problem['protocol']}: still has TODO values")

    if strict:
        for name, content in (("indicators.json", indicators), ("environments.json", environments)):
            for key, value in content.items():
                if not key.startswith("_") and _contains_todo(value):
                    errors.append(f"{name}[{key}]: still has TODO values")
    return errors


if __name__ == "__main__":
    strict = "--strict" in sys.argv
    problems_found = validate_all(strict=strict)
    for message in problems_found:
        print("ERROR:", message)
    print("OK" if not problems_found else f"{len(problems_found)} error(s)")
    sys.exit(1 if problems_found else 0)
