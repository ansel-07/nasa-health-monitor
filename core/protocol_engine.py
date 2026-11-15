# AI-assisted: generated with Claude Code and Codex, reviewed by Javi.
"""Run a protocol flowchart for an active episode. Owner: Javi."""
import json
from copy import deepcopy
from datetime import datetime
from math import isfinite

from core import conditions, data, episodes, mission, triggers
from core.config import load_environments, load_indicators, load_problems, load_protocol
from core.models import NODE_TYPES, OUTCOMES, PROBLEM_STATES, SEVERITIES, TODO_MARK


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

def _severity_names(problem: dict) -> list[str]:
    """Names set_severity may use, as in the config validator (AGENTS.md 5.3, TRANSITION).

    Symptom-based problems use PROBLEM_STATES, legacy problems SEVERITIES; a problem
    with both formats (like _example) accepts both. Unknown problems stay legacy.
    """
    names = (PROBLEM_STATES if "symptoms" in problem else []) + (SEVERITIES if "triggers" in problem else [])
    return names or SEVERITIES

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

    Call submit(episode, None) first to process automatic nodes. Flight surgeon
    contacts include response_delay_min (round-trip signal time; crew medical officer
    contacts are on board and have none); measure steps include their configured unit.
    """
    protocol = load_protocol(episode["problem"])
    _require_complete(protocol)
    node_id = episode.get("current_node") or protocol["start"]
    node = {**deepcopy(protocol["nodes"][node_id]), "id": node_id}
    if node["type"] == "action":
        # Practice runs do not wait: no mission time passes in a tutorial (AGENTS.md 16.4).
        node["remaining_wait_min"] = 0.0 if episode.get("practice") else _remaining_wait(node, episode, mission.now())
    if node["type"] == "measure":
        indicator = load_indicators()[node["indicator"]]
        node["unit"] = indicator["unit"]
        node.setdefault("text", f"Measure {indicator['name']} ({indicator['unit']}).")
    else:
        node.setdefault("text", "")
    if node["type"] == "contact" and node.get("target") == "flight_surgeon":
        # Earth signal travel time only (#141): the crew medical officer is on board, no delay.
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
    A valid measurement is saved as soon as it is accepted, so the symptom
    levels used by later decision nodes (symptom-based problems) include it.
    It is saved through episodes.on_new_measurement() (AGENTS.md 10, rules 1
    and 5) while this episode is still open in storage: its own problem is
    suppressed, other problems go to pending, even if this submit then ends.
    Only newly accepted readings are routed; submit(None) never replays one.
    The caller must use the returned episode on subsequent submissions.

    Practice mode (tutorials, AGENTS.md 16.4): if episode["practice"] is true the
    same flow runs in memory only. Nothing is saved: no episode, no measurement,
    no detection. Measured values only go to vars and the decision context, and
    action waits are not enforced. Symptom levels still come from stored data.
    """
    if episode["status"] in OUTCOMES:
        return deepcopy(episode)
    if episode["status"] != "active":
        raise ValueError("Only active episodes can run a protocol.")
    if user_input is not None and not isinstance(user_input, dict):
        raise ValueError("Protocol input must be a dictionary or None.")

    updated = deepcopy(episode)
    practice = bool(updated.get("practice"))
    protocol = load_protocol(updated["problem"])
    _require_complete(protocol)
    var_indicators = _var_indicators(protocol)
    problem = load_problems(include_examples=True).get(updated["problem"], {})
    severity_names = _severity_names(problem)
    updated["current_node"] = updated.get("current_node") or protocol["start"]
    updated.setdefault("vars", {})
    updated.setdefault("answers", {})
    updated.setdefault("log", [])
    at = mission.now()
    timestamp = at.isoformat()
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
            if "symptoms" in problem:
                # Recomputed at every decision so it reflects measurements saved above.
                ctx["symptoms"] = triggers.symptom_levels(
                    updated["problem"], updated["astronaut"], updated["environment"])
            target = node["default"]
            for branch in node["branches"]:
                if conditions.check(branch["if"], ctx):
                    target = branch["next"]
                    break
        elif kind == "set_severity":
            if node["severity"] not in severity_names:
                raise ValueError(f"Invalid protocol severity for this problem: {node['severity']}")
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
                remaining = 0.0 if practice else _remaining_wait({**node, "id": node_id}, updated, at)
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
                if not practice:
                    # Detection suppresses the problem of the astronaut's open episode, so
                    # that stored episode must be this one; otherwise it could reopen it.
                    stored_open = data.get_open_episode(updated["astronaut"])
                    if not stored_open or stored_open["id"] != updated["id"]:
                        raise ValueError("This episode is not the astronaut's open episode in storage.")
                    episodes.on_new_measurement({
                        "timestamp": timestamp, "astronaut": updated["astronaut"],
                        "indicator": node["indicator"], "value": value, "unit": unit,
                        "phase": "mission", "source": "protocol"}, updated["environment"])
                updated["vars"][node["save_as"]] = value
                latest[node["indicator"]] = value
                recorded_input = value
                target = node["next"]
            user_input = None
            # Revisiting an interactive step after a response is a valid loop.
            visited.clear()
        updated["log"].append({"at": timestamp, "node": node_id, "input": recorded_input})
        updated["current_node"] = target

    if not practice:
        data.save_episode(updated)
    return updated


def practice_episode(astronaut: str, problem_id: str, environment: str) -> dict:
    """In-memory episode for a tutorial (AGENTS.md 16.4): run it with submit(); nothing is saved.

    Starts at the lowest severity that opens an episode: "mild" while the problem still
    has legacy triggers (AGENTS.md 5.3, TRANSITION), "watch" for symptom-based ones.
    """
    problem = load_problems(include_examples=True)[problem_id]
    severity = SEVERITIES[1] if "triggers" in problem else PROBLEM_STATES[1]
    return {"id": f"practice-{problem_id}", "practice": True, "astronaut": astronaut,
            "problem": problem_id, "environment": environment, "status": "active",
            "severity_initial": severity, "severity": severity, "current_node": None,
            "vars": {}, "answers": {}, "log": [], "opened_at": mission.now().isoformat(),
            "closed_at": None, "outcome": None}


# ---------------------------------------------------------------- flowchart (AGENTS.md 8, #69)

_CONTACT_LABELS = {"crew_medical_officer": "crew medical officer", "flight_surgeon": "flight surgeon"}
_OPERATORS = {"above": ">", "below": "<", "at_least": "≥", "at_most": "≤", "z_above": "z >", "z_below": "z <"}
# (fill, border) on the dark app theme (docs/UI_STYLE.md): current step in the cyan accent,
# done in the "normal" green, ahead muted.
_CURRENT, _VISITED, _AHEAD = ("#0E3A44", "#5EF2FF"), ("#0F2E25", "#3DDC97"), ("#131C2E", "#3A4A66")
_NODE_TEXT, _EDGE_AHEAD = "#E6EDF7", "#7C8BA5"


def _readable(name) -> str:
    return str(name).replace("_", " ").capitalize()


def _short(text: str, limit: int = 34) -> str:
    """First sentence of a step text, cut to `limit` characters."""
    sentence = str(text).split(". ")[0].rstrip(".")
    return sentence if len(sentence) <= limit else sentence[:limit - 1].rstrip() + "…"


def _wrap(text: str, width: int = 18, max_lines: int | None = None) -> str:
    """Break text into lines of about `width` characters; with max_lines, end in "…" at a word."""
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1].rstrip("…").rstrip(" ,;:")
        while last and len(last) + 1 > width:
            last = last.rsplit(" ", 1)[0] if " " in last else last[:width - 1]
        lines[-1] = last.rstrip(" ,;:") + "…"
    return "\n".join(lines)


# Focused view (#188, #233): step labels on up to three lines that end at a whole word, instead of
# being cut at 34 characters, so the current step can be read on a projector.
_FOCUS_LABEL, _FOCUS_WRAP, _FOCUS_LINES = 200, 18, 3


def _node_label(node: dict, indicators: dict, limit: int = 34) -> str:
    kind = node["type"]
    if kind == "decision":
        return "Check"
    if kind == "set_severity":
        return f"Severity: {_readable(node['severity'])}"
    if kind == "contact":
        return f"Contact {_CONTACT_LABELS.get(node['target'], _readable(node['target']))}"
    if kind == "end":
        return f"End: {_readable(node['outcome'])}"
    if kind == "measure":
        name = indicators.get(node["indicator"], {}).get("name", "")
        return _short(f"Measure {name if name and not name.startswith(TODO_MARK) else _readable(node['indicator'])}", limit)
    return _short(node.get("text", ""), limit)


def _condition_label(cond: dict) -> str:
    """A few words for a decision branch; unknown forms fall back to "Condition met"."""
    if "environment_in" in cond:
        return " / ".join(env.upper() if len(env) <= 3 else env.capitalize() for env in cond["environment_in"])
    if "severity_is" in cond:
        return _readable(cond["severity_is"])
    if "severity_at_least" in cond:
        return f"{_readable(cond['severity_at_least'])} or worse"
    if "answer" in cond:
        return _readable(cond["equals"])
    operator = next((op for op in _OPERATORS if op in cond), None)
    if operator and ("var" in cond or "indicator" in cond):
        subject = "Value" if "var" in cond else _readable(cond["indicator"])
        return f"{subject} {_OPERATORS[operator]} {cond[operator]:g}"
    if "symptom" in cond:
        level = cond.get("level_is") or cond.get("level_at_least")
        return f"{_readable(cond['symptom'])}: {_readable(level)}"
    children = cond.get("any") or cond.get("all") or cond.get("of") or []
    levels = {child.get("level_is") or child.get("level_at_least") for child in children if "symptom" in child}
    if children and len(levels) == 1 and all("symptom" in child for child in children):
        how_many = "Any" if "any" in cond else "All" if "all" in cond else f"{cond['count_at_least']}+"
        return f"{how_many} finding{'' if how_many == 'Any' else 's'}: {_readable(levels.pop())}"
    return "Condition met"


def _edges(node: dict) -> list[tuple[str, str]]:
    """(target, label) for every way out of a node, in display order."""
    kind = node["type"]
    if kind == "question":
        return [(target, _readable(answer)) for answer, target in node["options"].items()]
    if kind == "decision":
        return [(b["next"], _condition_label(b["if"])) for b in node["branches"]] + [(node["default"], "Otherwise")]
    edges = [(node["next"], "Done" if kind == "action" and "next_if_cannot" in node else "")] if "next" in node else []
    if "next_if_cannot" in node:
        edges.append((node["next_if_cannot"], "I can't"))
    return edges


_RECENT_STEPS = 1      # visited steps kept before the current one in the focused view (#233)
_AUTOMATIC = ("decision", "set_severity")


def _destinations(protocol: dict, node_id: str) -> list[tuple[str, str]]:
    """(target, label) for every way out of a node, passing through automatic nodes.

    The astronaut never sees decision or set_severity nodes, so the focused chart
    skips them (#233): each option points at the step it really leads to, and its
    label joins the answer with the branch taken ("No · Any finding: Concern") or
    the severity set on the way ("Yes · Medical urgency"). Exits that reach the
    same step share one arrow.
    """
    found: dict[str, list[str]] = {}

    def follow(target: str, parts: list[str], seen: frozenset) -> None:
        node = protocol["nodes"][target]
        if node["type"] not in _AUTOMATIC or target in seen:   # seen: never loop on automatic cycles
            label = " · ".join(part for part in parts if part)
            found.setdefault(target, [])
            if label not in found[target]:
                found[target].append(label)
            return
        extra = [_readable(node["severity"])] if node["type"] == "set_severity" else []
        for nxt, label in _edges(node):
            follow(nxt, parts + extra + ([label] if node["type"] == "decision" else []), seen | {target})

    for target, label in _edges(protocol["nodes"][node_id]):
        follow(target, [label], frozenset({node_id}))
    return [(target, " / ".join(label for label in labels if label)) for target, labels in found.items()]


def flowchart_dot(episode: dict, whole: bool = False) -> str:
    """Graphviz DOT text of the episode's protocol for st.graphviz_chart.

    By default only the area around the current step is drawn, sized for a
    projector (#233): the previous step, the current one and the step each
    option leads to. Automatic nodes (decision, set_severity) are skipped, so
    every box is something the astronaut sees; earlier steps become a caption
    above the chart. whole=True draws every node with short labels. The current
    node is highlighted, visited nodes are green and the connections taken are
    thicker. Reads only configuration.
    """
    protocol = load_protocol(episode["problem"])
    nodes = protocol["nodes"]
    indicators = load_indicators()
    current = episode.get("current_node") or protocol["start"]
    trace = [entry["node"] for entry in episode.get("log", [])
             if entry.get("input") != "wait_started"] + [current]
    if not whole:   # only what the astronaut saw (the current node is kept even if automatic)
        trace = [node for node in trace if node == current or nodes[node]["type"] not in _AUTOMATIC]
    trace = [node for i, node in enumerate(trace) if i == 0 or node != trace[i - 1]]
    taken, visited = set(zip(trace, trace[1:])), set(trace)
    quote = lambda value: json.dumps(value, ensure_ascii=False)  # Graphviz reads UTF-8, not \u escapes

    if whole:
        shown, hidden = list(nodes), 0
        arrows = [(node_id, target, label) for node_id in shown for target, label in _edges(nodes[node_id])]
    else:
        earlier = [node for node in dict.fromkeys(trace[:-1]) if node != current]
        recent = earlier[-_RECENT_STEPS:]
        hidden = len(earlier) - len(recent)
        shown = recent + [current]
        arrows = []
        for source, target in zip(trace, trace[1:]):   # the route taken, with the answer given
            if source in shown and target in shown:
                arrows.append((source, target, dict(_destinations(protocol, source)).get(target, "")))
        for target, label in _destinations(protocol, current):
            if target not in shown:
                shown.append(target)
            arrows.append((current, target, label))

    font, edge_font = (11, 9) if whole else (20, 11)
    lines = ["digraph protocol {",
             'graph [rankdir=LR, bgcolor="transparent", nodesep=0.3, ranksep=0.45];',
             f'node [shape=box, style="rounded,filled", fontname="IBM Plex Sans", fontcolor="{_NODE_TEXT}", '
             f'fontsize={font}, margin="0.14,0.08"];',
             f'edge [fontname="IBM Plex Sans", fontsize={edge_font}, arrowsize=0.7];']
    if hidden:   # a caption above the chart, so earlier steps do not take a column of their own
        caption = f"… {hidden} earlier step{'s' if hidden != 1 else ''}"
        lines.append(f'graph [label={quote(caption)}, labelloc=t, labeljust=l, fontname="IBM Plex Sans", '
                     f'fontsize={edge_font}, fontcolor="{_VISITED[1]}"];')
    for node_id in shown:
        node = nodes[node_id]
        fill, border = _CURRENT if node_id == current else _VISITED if node_id in visited else _AHEAD
        width = 2.5 if node_id == current else 1
        shape = "diamond" if node["type"] == "decision" else "box"
        label = (_wrap(_node_label(node, indicators)) if whole
                 else _wrap(_node_label(node, indicators, _FOCUS_LABEL), _FOCUS_WRAP, _FOCUS_LINES))
        lines.append(f"{quote(node_id)} [label={quote(label)}, shape={shape}, "
                     f'fillcolor="{fill}", color="{border}", penwidth={width}];')
    for source, target, label in arrows:
        color, width = (_VISITED[1], 2.5) if (source, target) in taken else (_EDGE_AHEAD, 1)
        lines.append(f"{quote(source)} -> {quote(target)} [label={quote(label)}, "
                     f'color="{color}", fontcolor="{color}", penwidth={width}];')
    lines.append("}")
    return "\n".join(lines)
