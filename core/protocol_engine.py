# AI-assisted: generated with Claude Code and Codex; human review pending.
"""Run a protocol flowchart for an active episode. Owner: Javi."""
from copy import deepcopy
from datetime import datetime
from math import isfinite

from core import conditions, data, mission
from core.config import load_environments, load_indicators, load_protocol
from core.models import NODE_TYPES, OUTCOMES, SEVERITIES, TODO_MARK


def _require_complete(value, path: str = "protocol") -> None:
    """Reject placeholders anywhere in a protocol before any execution effects."""
    if isinstance(value, str) and value.startswith(TODO_MARK):
        raise ValueError(f"{path}: still has TODO content.")
    if isinstance(value, dict):
        for key, child in value.items():
            _require_complete(key, f"{path} key")
            _require_complete(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _require_complete(child, f"{path}[{index}]")

def _var_indicators(protocol: dict) -> dict[str, str]:
    """Build variable-to-indicator metadata from the protocol on each run."""
    mapping = {}
    for node in protocol["nodes"].values():
        if node.get("type") != "measure":
            continue
        name, indicator = node.get("save_as"), node.get("indicator")
        if name in mapping and mapping[name] != indicator:
            raise ValueError(f"Protocol variable '{name}' maps to multiple indicators.")
        mapping[name] = indicator
    return mapping

def _remaining_wait(node: dict, episode: dict, at: datetime) -> float:
    """Use a persisted log entry so reloads and earlier confirmation time do not count."""
    wait = node.get("wait_min", 0)
    if isinstance(wait, bool) or not isinstance(wait, (int, float)) or not isfinite(wait) or wait < 0:
        raise ValueError("Action wait_min is missing or invalid in the protocol.")
    log = episode.get("log", [])
    if not log or log[-1]["node"] != node["id"] or log[-1]["input"] != "wait_started":
        return float(wait)
    elapsed = (at - datetime.fromisoformat(log[-1]["at"])).total_seconds() / 60
    return max(0.0, wait - max(0.0, elapsed))


def current_step(episode: dict) -> dict:
    """Return a detached node for display, without changing or saving the episode.

    Call submit(episode, None) first to process automatic nodes. Contact steps
    include response_delay_min; measure steps include their configured unit.
    """
    protocol = load_protocol(episode["problem"])
    _require_complete(protocol)
    node_id = episode.get("current_node") or protocol["start"]
    node = {**deepcopy(protocol["nodes"][node_id]), "id": node_id}
    if node["type"] == "action":
        node["remaining_wait_min"] = _remaining_wait(node, episode, mission.now())
    if node["type"] == "measure":
        indicator = load_indicators()[node["indicator"]]
        node["unit"] = indicator["unit"]
        node.setdefault("text", f"Measure {indicator['name']} ({indicator['unit']}).")
    else:
        node.setdefault("text", "")
    if node["type"] == "contact":
        delay = load_environments()[episode["environment"]]["comm_delay_min"]
        if isinstance(delay, bool) or not isinstance(delay, (int, float)) or not isfinite(delay) or delay < 0:
            raise ValueError("Contact response delay is missing or invalid in config/environments.json.")
        node["response_delay_min"] = 2 * delay
    if str(node["text"]).startswith("TODO") or str(node.get("unit", "")).startswith("TODO"):
        raise ValueError(f"Protocol step '{node_id}' still has TODO display content.")
    return node


def submit(episode: dict, user_input: dict | None) -> dict:
    """Apply one user response, process automatic nodes and save the result.

    Inputs: info/contact {"action": "continue"}; action {"action": "done"}
    or {"action": "cannot"}; measure {"value": finite number}; question
    {"answer": configured option}. None only processes automatic nodes.
    Call with None to initialize a timed action before submitting Done.
    Action wait_min is enforced with the mission clock, starting on arrival
    at the action; cannot remains available during the wait. This function
    does not advance the mission clock or simulate notifications.
    The caller must use the returned episode on subsequent submissions.
    """
    if episode["status"] in OUTCOMES:
        return deepcopy(episode)
    if episode["status"] != "active":
        raise ValueError("Only active episodes can run a protocol.")
    if user_input is not None and not isinstance(user_input, dict):
        raise ValueError("Protocol input must be a dictionary or None.")

    updated = deepcopy(episode)
    protocol = load_protocol(updated["problem"])
    _require_complete(protocol)
    var_indicators = _var_indicators(protocol)
    updated["current_node"] = updated.get("current_node") or protocol["start"]
    updated.setdefault("vars", {})
    updated.setdefault("answers", {})
    updated.setdefault("log", [])
    at = mission.now()
    timestamp = at.isoformat()
    measurements = []
    visited = set()
    latest = dict(data.latest_values(updated["astronaut"]))

    while True:
        node_id = updated["current_node"]
        if node_id in visited:
            raise ValueError("Protocol contains an automatic cycle.")
        visited.add(node_id)
        node = protocol["nodes"][node_id]
        kind = node["type"]
        if kind not in NODE_TYPES:
            raise ValueError(f"Unsupported protocol node type: {kind}")
        recorded_input = None
        if kind == "decision":
            ctx = {key: updated[key] for key in ("astronaut", "environment", "severity", "vars", "answers")}
            ctx["latest"] = latest
            ctx["var_indicators"] = var_indicators
            target = node["default"]
            for branch in node["branches"]:
                if conditions.check(branch["if"], ctx):
                    target = branch["next"]
                    break
        elif kind == "set_severity":
            if node["severity"] not in SEVERITIES:
                raise ValueError("Invalid protocol severity.")
            updated["severity"] = node["severity"]
            target = node["next"]
        elif kind == "end":
            if node["outcome"] not in OUTCOMES:
                raise ValueError("Invalid protocol outcome.")
            updated.update(status=node["outcome"], outcome=node["outcome"], closed_at=timestamp)
            updated["log"].append({"at": timestamp, "node": node_id, "input": None})
            break
        else:
            if kind == "action":
                remaining = _remaining_wait({**node, "id": node_id}, updated, at)
                if remaining > 0:
                    log = updated["log"]
                    if not log or log[-1]["node"] != node_id or log[-1]["input"] != "wait_started":
                        log.append({"at": timestamp, "node": node_id, "input": "wait_started"})
            if user_input is None:
                break
            if kind in ("info", "contact"):
                if user_input != {"action": "continue"}:
                    raise ValueError("This step requires action='continue'.")
                target = node["next"]
                recorded_input = "continue"
            elif kind == "action":
                action = user_input.get("action")
                if action == "done":
                    if remaining > 0:
                        raise ValueError(f"Action wait is not complete ({remaining:g} minutes remaining).")
                    target = node["next"]
                elif action == "cannot" and "next_if_cannot" in node:
                    target = node["next_if_cannot"]
                else:
                    raise ValueError("Action must be 'done' or a configured 'cannot' route.")
                recorded_input = action
            elif kind == "question":
                answer = user_input.get("answer")
                if not isinstance(answer, str) or answer not in node["options"]:
                    raise ValueError("Choose a configured question option.")
                updated["answers"][node["save_as"]] = answer
                target = node["options"][answer]
                recorded_input = answer
            elif kind == "measure":
                value = user_input.get("value")
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                    raise ValueError("Measurement must be a finite number.")
                indicator = load_indicators()[node["indicator"]]
                unit = indicator["unit"]
                if unit.startswith("TODO"):
                    raise ValueError("Measurement unit is still TODO in config/indicators.json.")
                measurements.append({"timestamp": timestamp, "astronaut": updated["astronaut"],
                                     "indicator": node["indicator"], "value": value, "unit": unit,
                                     "phase": "mission", "source": "protocol"})
                updated["vars"][node["save_as"]] = value
                latest[node["indicator"]] = value
                recorded_input = value
                target = node["next"]
            user_input = None
            # Revisiting an interactive step after a response is a valid loop.
            visited.clear()
        updated["log"].append({"at": timestamp, "node": node_id, "input": recorded_input})
        updated["current_node"] = target

    for measurement in measurements:
        data.add_measurement(measurement)
    data.save_episode(updated)
    return updated
