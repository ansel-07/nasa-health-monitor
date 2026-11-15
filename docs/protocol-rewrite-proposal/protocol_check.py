#!/usr/bin/env python3
# AI-assisted: written with Claude; human review pending.
"""Checks for config/protocols/*.json and PROTOCOL_FLOWCHARTS.md. Standard library only.

  python protocol_check.py validate  <protocol.json> [...]      structure + graph + paths
  python protocol_check.py mermaid   <protocol.json>            print the Mermaid block for one protocol
  python protocol_check.py sync      <FLOWCHARTS.md> <protocol.json> [...]   diagram == JSON ?

Structure rules come from ESTRUCTURA.md sections 4.6 and 4.7. Three constructs that are not in
ESTRUCTURA.md but are already used by the protocol files in the repository are accepted and
reported as "repo extensions": a `source` string on any node, the `symptom` + `level_is`
condition, and the `medical_urgency` severity.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------- ESTRUCTURA.md 4.7
NODE_FIELDS = {  # type: (required, optional)
    "info": ({"text", "next"}, set()),
    "action": ({"text", "next", "source"}, {"wait_min", "next_if_cannot"}),
    "measure": ({"indicator", "save_as", "next"}, {"text"}),
    "question": ({"text", "save_as", "options"}, set()),
    "decision": ({"branches", "default"}, set()),
    "set_severity": ({"severity", "next"}, set()),
    "contact": ({"target", "text", "next"}, set()),
    "end": ({"outcome", "text"}, set()),
}
CONTACT_TARGETS = {"crew_medical_officer", "flight_surgeon"}
END_OUTCOMES = {"resolved", "monitoring", "handed_over"}
SPEC_SEVERITIES = {"inactive", "mild", "moderate", "severe"}
REPO_SEVERITIES = {"medical_urgency"}          # repo extension (two-state triage of the guide)
TOP_LEVEL = {"problem", "start", "nodes"}
TOP_LEVEL_META = {"_ai_assisted", "_integration_status"}   # present in the repository files
COMPARATORS = {"above", "below", "z_above", "z_below"}
ENVIRONMENTS = ["iss", "moon", "mars"]          # ESTRUCTURA.md 4.4
AUTOMATIC = {"decision", "set_severity"}        # nodes the astronaut never sees
URGENT = "medical_urgency"


def check_condition(cond, where, errors, notes):
    if not isinstance(cond, dict) or not cond:
        errors.append(f"{where}: condition must be a non-empty object")
        return
    keys = set(cond)
    if keys == {"all"} or keys == {"any"}:
        items = cond[next(iter(keys))]
        if not isinstance(items, list) or not items:
            errors.append(f"{where}: all/any needs a non-empty list")
            return
        for i, sub in enumerate(items):
            check_condition(sub, f"{where}[{i}]", errors, notes)
    elif "indicator" in keys or "var" in keys:
        rest = keys - {"indicator", "var"}
        if len(keys & {"indicator", "var"}) != 1 or len(rest) != 1 or not rest <= COMPARATORS:
            errors.append(f"{where}: indicator/var needs exactly one of {sorted(COMPARATORS)}")
    elif keys == {"severity_at_least"} or keys == {"severity_is"}:
        sev = cond[next(iter(keys))]
        if sev in REPO_SEVERITIES:
            notes.add(f"severity '{sev}' (repo extension, not in ESTRUCTURA.md)")
        elif sev not in SPEC_SEVERITIES:
            errors.append(f"{where}: unknown severity {sev!r}")
    elif keys == {"environment_in"}:
        envs = cond["environment_in"]
        if not isinstance(envs, list) or not envs or not set(envs) <= set(ENVIRONMENTS):
            errors.append(f"{where}: environment_in must list known environments")
    elif keys == {"answer", "equals"}:
        pass
    elif keys == {"symptom", "level_is"}:
        notes.add("condition 'symptom' + 'level_is' (repo extension, not in ESTRUCTURA.md 4.6)")
    else:
        errors.append(f"{where}: unsupported condition keys {sorted(keys)}")


def validate_structure(proto):
    errors, notes = [], set()
    extra = set(proto) - TOP_LEVEL - TOP_LEVEL_META
    if extra:
        errors.append(f"unsupported top-level keys {sorted(extra)}")
    for key in TOP_LEVEL:
        if key not in proto:
            errors.append(f"missing top-level key {key!r}")
    nodes = proto.get("nodes", {})
    if proto.get("start") not in nodes:
        errors.append("start does not name an existing node")
    for nid, node in nodes.items():
        ntype = node.get("type")
        if ntype not in NODE_FIELDS:
            errors.append(f"{nid}: unknown type {ntype!r}")
            continue
        required, optional = NODE_FIELDS[ntype]
        keys = set(node) - {"type"}
        if required - keys:
            errors.append(f"{nid}: missing fields {sorted(required - keys)}")
        unknown = keys - required - optional - {"source"}
        if unknown:
            errors.append(f"{nid}: unsupported fields {sorted(unknown)}")
        if "source" in keys and "source" not in required:
            notes.add("'source' on non-action nodes (repo extension; ESTRUCTURA.md rule: every "
                      "node with health content carries a source)")
        if not str(node.get("source", "")).strip():
            errors.append(f"{nid}: empty or missing source")
        for field in ("text", "source"):
            if "TODO" in str(node.get(field, "")):
                errors.append(f"{nid}: {field} still contains a TODO marker")
        for field in ("next", "next_if_cannot", "default"):
            if field in node and node[field] not in nodes:
                errors.append(f"{nid}: {field} -> {node[field]!r} does not exist")
        if ntype == "question":
            opts = node.get("options")
            if not isinstance(opts, dict) or len(opts) < 2:
                errors.append(f"{nid}: a question needs at least two options")
            else:
                for value, target in opts.items():
                    if target not in nodes:
                        errors.append(f"{nid}: option {value!r} -> {target!r} does not exist")
        if ntype == "decision":
            branches = node.get("branches")
            if not isinstance(branches, list) or not branches:
                errors.append(f"{nid}: a decision needs at least one branch")
            else:
                for i, branch in enumerate(branches):
                    if set(branch) != {"if", "next"}:
                        errors.append(f"{nid}: branch {i} must have exactly 'if' and 'next'")
                        continue
                    if branch["next"] not in nodes:
                        errors.append(f"{nid}: branch {i} -> {branch['next']!r} does not exist")
                    check_condition(branch["if"], f"{nid}.branches[{i}].if", errors, notes)
        if ntype == "set_severity":
            sev = node.get("severity")
            if sev in REPO_SEVERITIES:
                notes.add(f"severity '{sev}' (repo extension, not in ESTRUCTURA.md)")
            elif sev not in SPEC_SEVERITIES:
                errors.append(f"{nid}: unknown severity {sev!r}")
        if ntype == "contact" and node.get("target") not in CONTACT_TARGETS:
            errors.append(f"{nid}: contact target must be one of {sorted(CONTACT_TARGETS)}")
        if ntype == "end" and node.get("outcome") not in END_OUTCOMES:
            errors.append(f"{nid}: end outcome must be one of {sorted(END_OUTCOMES)}")
        if "wait_min" in node and not isinstance(node["wait_min"], (int, float)):
            errors.append(f"{nid}: wait_min must be a number")
        if "text" in node:
            sentences = [s for s in re.split(r"(?<=[.?!])\s+", node["text"].strip()) if s]
            if len(sentences) > 2:
                errors.append(f"{nid}: text has {len(sentences)} sentences (repo convention: two)")
    return errors, sorted(notes)


# ---------------------------------------------------------------- graph
def branch_label(cond):
    if "severity_is" in cond or "severity_at_least" in cond:
        return str(next(iter(cond.values()))).replace("_", " ").capitalize()
    if "environment_in" in cond:
        return ", ".join(cond["environment_in"])
    if "any" in cond or "all" in cond:
        subs = cond.get("any") or cond.get("all")
        levels = {s.get("level_is") for s in subs}
        if len(levels) == 1 and None not in levels:
            return levels.pop().capitalize()
    return json.dumps(cond, sort_keys=True)


def edges(nid, node):
    """Outgoing edges as (label, target, kind)."""
    ntype = node["type"]
    if ntype == "end":
        return []
    if ntype == "question":
        return [(value, target, "option") for value, target in node["options"].items()]
    if ntype == "decision":
        out = [(branch_label(b["if"]), b["next"], "branch") for b in node["branches"]]
        return out + [("Otherwise", node["default"], "default")]
    if ntype == "action":
        out = [("Done", node["next"], "done")]
        if "next_if_cannot" in node:
            hold = node["next_if_cannot"] == nid
            out.append(("I cannot confirm" if hold else "I cannot", node["next_if_cannot"], "cannot"))
        return out
    return [("Continue", node["next"], "next")]


def reachable(nodes, start):
    seen, stack = set(), [start]
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        stack.extend(t for _, t, _ in edges(nid, nodes[nid]))
    return seen


def cycles(nodes):
    """Self-loops and longer cycles (as node lists)."""
    found = [[nid] for nid, node in nodes.items() if any(t == nid for _, t, _ in edges(nid, node))]
    colour = {}

    def visit(nid, trail):
        colour[nid] = 1
        for _, target, _ in edges(nid, nodes[nid]):
            if target == nid:
                continue
            if colour.get(target) == 1:
                found.append(trail[trail.index(target):] + [target])
            elif target not in colour:
                visit(target, trail + [target])
        colour[nid] = 2

    for nid in nodes:
        if nid not in colour:
            visit(nid, [nid])
    return found


def routing_signature(nodes, nid):
    """What a node does apart from its wording: type, addressee/outcome and where it leads."""
    node = nodes[nid]
    return (node["type"], node.get("target"), node.get("outcome"), node.get("severity"),
            tuple(sorted(t for _, t, _ in edges(nid, node))))


def fork_findings(nodes):
    """Forks whose outcomes do not differ in routing (candidates for redundancy)."""
    void, text_only = [], []
    for nid, node in nodes.items():
        out = [(lab, t) for lab, t, _ in edges(nid, node) if t != nid]
        if len(out) < 2:
            continue
        targets = {t for _, t in out}
        if len(targets) == 1:
            void.append((nid, sorted(lab for lab, _ in out), targets.pop()))
            continue
        groups = defaultdict(list)
        for lab, target in out:
            groups[routing_signature(nodes, target)].append((lab, target))
        for sig, members in groups.items():
            if len({t for _, t in members}) > 1:
                text_only.append((nid, members, sig))
    return void, text_only


# ---------------------------------------------------------------- path enumeration
def holds(cond, ctx):
    if "any" in cond:
        return any(holds(c, ctx) for c in cond["any"])
    if "all" in cond:
        return all(holds(c, ctx) for c in cond["all"])
    if "severity_is" in cond:
        return ctx["severity"] == cond["severity_is"]
    if "environment_in" in cond:
        return ctx["environment"] in cond["environment_in"]
    if "symptom" in cond:
        return ctx["concern"] and cond["level_is"] == "concern"
    raise ValueError(f"path enumeration does not model condition {cond}")


def enumerate_paths(proto):
    """Every start-to-end walk for every entry scenario. The handover hold (self-loop) is
    walked zero times: it repeats the same task and adds no new route."""
    nodes, paths, used = proto["nodes"], [], set()

    def walk(nid, ctx, trail, inputs):
        node = nodes[nid]
        trail = trail + [nid]
        if node["type"] == "end":
            paths.append({"scenario": ctx["scenario"], "nodes": trail, "inputs": inputs,
                          "outcome": node["outcome"], "severity": ctx["severity"]})
            return
        if node["type"] == "decision":
            for branch in node["branches"]:
                if holds(branch["if"], ctx):
                    used.add((nid, branch_label(branch["if"])))
                    return walk(branch["next"], ctx, trail, inputs)
            used.add((nid, "Otherwise"))
            return walk(node["default"], ctx, trail, inputs)
        if node["type"] == "set_severity":
            ctx = dict(ctx, severity=node["severity"])
        for label, target, _ in edges(nid, node):
            used.add((nid, label))
            if target == nid:
                continue
            step = inputs + [(nid, label)] if node["type"] in ("question", "action") else inputs
            walk(target, ctx, trail, step)

    for entry in ("watch", URGENT):
        for concern in (False, True):
            for env in ENVIRONMENTS:
                ctx = {"severity": entry, "concern": concern, "environment": env,
                       "scenario": (entry, concern, env)}
                walk(proto["start"], ctx, [], [])
    return paths, used


def path_facts(nodes, path):
    seq = path["nodes"]
    contacts = [nodes[n]["target"] for n in seq if nodes[n]["type"] == "contact"]
    return {
        "shown": sum(1 for n in seq if nodes[n]["type"] not in AUTOMATIC),
        "fs": "flight_surgeon" in contacts,
        "cmo": "crew_medical_officer" in contacts,
        "cmo_contacts": contacts.count("crew_medical_officer"),
        "back_to_back": any(
            nodes[a]["type"] == nodes[b]["type"] == "contact" and nodes[a]["target"] == nodes[b]["target"]
            for a, b in zip(seq, seq[1:])),
    }


def classify(nodes, seq):
    """Clinical response tier of a route, read from the nodes it passes through."""
    if any(nodes[n]["type"] == "set_severity" and nodes[n]["severity"] == URGENT for n in seq) \
            or seq[1].startswith("u_"):
        return "immediate medical escalation"
    if "w_priority_review" in seq:
        return "priority clinician review, then supervised management"
    return "routine notification, supervised management and monitoring"


def analyse(path_json):
    proto = json.loads(Path(path_json).read_text(encoding="utf-8"))
    nodes = proto["nodes"]
    name = proto.get("problem", path_json)
    print(f"\n=== {name}  ({path_json}) ===")
    ok = True

    errors, notes = validate_structure(proto)
    print(f"[structure] {len(nodes)} nodes, types: "
          + ", ".join(f"{t}={c}" for t, c in sorted(Counter(n['type'] for n in nodes.values()).items())))
    for note in notes:
        print(f"  note: {note}")
    for err in errors:
        ok = False
        print(f"  ERROR: {err}")
    if not errors:
        print("  OK: fields, targets, outcomes, conditions and references are valid")
    if errors and any("does not exist" in e or "unknown type" in e for e in errors):
        return False

    seen = reachable(nodes, proto["start"])
    orphans = sorted(set(nodes) - seen)
    ends = {n for n, v in nodes.items() if v["type"] == "end"}
    dead = sorted(n for n in seen if not (reachable(nodes, n) & ends))
    loops = cycles(nodes)
    allowed = [c for c in loops if c == ["u_handover"]]
    other = [c for c in loops if c != ["u_handover"]]
    print(f"[graph] unreachable nodes: {orphans or 'none'}; nodes that cannot reach an end: {dead or 'none'}")
    print(f"  cycles: intentional handover hold={len(allowed)}, other={other or 'none'}")
    ok &= not orphans and not dead and not other

    void, text_only = fork_findings(nodes)
    print(f"[forks] forks whose outcomes all reach the same node: {void or 'none'}")
    if text_only:
        for nid, members, sig in text_only:
            print(f"  outcomes of {nid} that differ only in wording: {members} -> {sig[0]}"
                  f"{'/' + sig[1] if sig[1] else ''} then {list(sig[4])}")
    else:
        print("  forks whose outcomes differ only in wording: none")

    paths, used = enumerate_paths(proto)
    all_edges = {(nid, lab) for nid, node in nodes.items() for lab, _, _ in edges(nid, node)}
    unused = sorted(all_edges - used)
    print(f"[paths] edges never taken in any scenario (iss/moon/mars x concern x entry severity): "
          f"{unused or 'none'}")
    ok &= not unused

    unique = {}
    for p in paths:
        unique.setdefault(tuple(p["nodes"]), p)
    facts = {seq: path_facts(nodes, p) for seq, p in unique.items()}
    total = len(unique)
    by_outcome = Counter(p["outcome"] for p in unique.values())
    fs = sum(f["fs"] for f in facts.values())
    cmo = sum(f["cmo"] for f in facts.values())
    twice = sum(f["cmo_contacts"] > 1 for f in facts.values())
    b2b = sum(f["back_to_back"] for f in facts.values())
    print(f"  distinct routes: {total}  (scenario x answer combinations walked: {len(paths)})")
    print("  end outcome: " + ", ".join(f"{k}={v} ({v / total:.0%})" for k, v in sorted(by_outcome.items())))
    print(f"  routes with a flight-surgeon contact: {fs}/{total} ({fs / total:.0%})")
    print(f"  routes with a crew-medical-officer contact: {cmo}/{total} ({cmo / total:.0%}); "
          f"with more than one: {twice}; with two in a row: {b2b}")
    tiers = Counter(classify(nodes, seq) for seq in unique)
    for tier, count in sorted(tiers.items()):
        print(f"  tier: {tier}: {count} ({count / total:.0%})")
    for env in ENVIRONMENTS:
        urgent = {tuple(p["nodes"]) for p in paths
                  if p["scenario"][2] == env and p["severity"] == URGENT}
        with_fs = sum(facts[s]["fs"] for s in urgent)
        print(f"  urgent routes on {env}: {len(urgent)}, with flight-surgeon contact: {with_fs}")
    watch = [s for s, p in unique.items() if p["severity"] != URGENT]
    print(f"  non-urgent routes: {len(watch)}, with flight-surgeon contact: "
          f"{sum(facts[s]['fs'] for s in watch)}")
    shown = [facts[s]["shown"] for s in unique]
    print(f"  steps shown to the astronaut per route: min {min(shown)}, max {max(shown)}; "
          f"non-urgent routes: {sorted(facts[s]['shown'] for s in watch)}")

    bad = [p for p in unique.values()
           if (p["severity"] == URGENT) != (p["outcome"] == "handed_over")]
    mixed = [p for p in unique.values()
             if any(n.startswith("w_") and nodes[n]["type"] not in AUTOMATIC
                    for n in p["nodes"][max((i for i, n in enumerate(p["nodes"])
                                             if nodes[n]["type"] == "set_severity"), default=len(p["nodes"])):])]
    print(f"[consistency] urgent routes not ending handed_over, or non-urgent ones that do: {len(bad)}; "
          f"watch steps shown after escalation: {len(mixed)}")
    ok &= not bad and not mixed
    print(f"RESULT {name}: {'PASS' if ok else 'FAIL'}")
    return ok


# ---------------------------------------------------------------- Mermaid
LABELS = {
    "sans": {
        "route": "Already medical urgency?",
        "w_red_flags": "Urgent eye or neurological symptoms?",
        "w_escalate": "Set medical urgency",
        "w_concern": "Any concern-level finding?",
        "w_priority_review": "Ask medical officer for priority review",
        "w_review_outcome": "Clinician declared medical urgency?",
        "w_notify": "Notify medical officer; agree check-ups",
        "w_acuity": "Review each eye: acuity, OCT, fields",
        "w_missing_data": "Not evaluable: complete missing tests",
        "w_symptoms": "Mild gradual focusing difficulty?",
        "w_correction": "Use prescribed optical correction",
        "w_end": "Monitoring: check-ups, habitat procedures, limits",
        "u_stop": "Stop risky tasks and EVA; alert local care now",
        "u_local": "Immediate local ocular and neurological assessment",
        "u_env": "Mission environment?",
        "u_moon": "Moon: care on board; clinician evaluates transfer",
        "u_earth": "ISS, Mars: send case to flight surgeons; local care continues",
        "u_handover": "Confirm clinician review and accepted care",
        "u_end": "Handed over after clinical review",
    },
    "muscle_atrophy": {
        "route": "Already medical urgency?",
        "w_red_flags": "Urgent symptoms?",
        "w_escalate": "Set medical urgency",
        "w_concern": "Any concern-level finding?",
        "w_limits": "Unexpected worsening or task limitation?",
        "w_priority_review": "Ask medical officer for priority assessment",
        "w_review_outcome": "Clinician declared medical urgency?",
        "w_report": "Tell medical officer; review symptoms and load",
        "w_exercise": "Supervised training and nutrition review",
        "w_end": "Monitoring: daily log, comparable strength tests",
        "u_stop": "Stop exercise and risky tasks; alert local care now",
        "u_local": "Immediate local assessment and stabilization",
        "u_env": "Mission environment?",
        "u_moon": "Moon: care on board; clinician evaluates transfer",
        "u_earth": "ISS, Mars: send case to flight surgeons; local care continues",
        "u_handover": "Confirm clinician review and accepted care",
        "u_end": "Handed over after clinical review",
    },
}
DIAMOND = {"decision", "question"}


def mermaid(proto):
    labels = LABELS[proto["problem"]]
    lines = ["flowchart TD"]
    for nid, node in proto["nodes"].items():
        text = labels[nid]
        lines.append(f'    {nid}{{"{text}"}}' if node["type"] in DIAMOND else f'    {nid}["{text}"]')
    for nid, node in proto["nodes"].items():
        for label, target, _ in edges(nid, node):
            lines.append(f'    {nid} -->|"{label}"| {target}')
    return "\n".join(lines)


NODE_RE = re.compile(r'^\s*(\w+)(\{"|\[")(.*?)("\}|"\])\s*$')
EDGE_RE = re.compile(r'^\s*(\w+)\s*-->\|"(.*?)"\|\s*(\w+)\s*$')


def parse_mermaid(block):
    shapes, links = {}, set()
    for line in block.splitlines()[1:]:
        if not line.strip():
            continue
        node, edge = NODE_RE.match(line), EDGE_RE.match(line)
        if node:
            shapes[node.group(1)] = "diamond" if node.group(2) == '{"' else "box"
        elif edge:
            links.add(edge.groups())
        else:
            raise ValueError(f"unparsed Mermaid line: {line!r}")
    return shapes, links


def sync(md_path, json_paths):
    blocks = re.findall(r"```mermaid\n(.*?)```", Path(md_path).read_text(encoding="utf-8"), re.S)
    ok = len(blocks) == len(json_paths)
    if not ok:
        print(f"ERROR: {len(blocks)} Mermaid blocks for {len(json_paths)} protocols")
    parsed = [parse_mermaid(b) for b in blocks]
    for path_json in json_paths:
        proto = json.loads(Path(path_json).read_text(encoding="utf-8"))
        nodes = proto["nodes"]
        want_shapes = {n: "diamond" if v["type"] in DIAMOND else "box" for n, v in nodes.items()}
        want_links = {(n, lab, t) for n, v in nodes.items() for lab, t, _ in edges(n, v)}
        match = [(s, l) for s, l in parsed if set(s) == set(nodes)]
        if len(match) != 1:
            ok = False
            print(f"{proto['problem']}: no diagram has exactly this node set")
            for s, _ in parsed:
                print(f"   diagram-only: {sorted(set(s) - set(nodes))}  json-only: {sorted(set(nodes) - set(s))}")
            continue
        shapes, links = match[0]
        problems = []
        problems += [f"shape of {n}" for n in nodes if shapes[n] != want_shapes[n]]
        problems += [f"diagram-only edge {e}" for e in sorted(links - want_links)]
        problems += [f"json-only edge {e}" for e in sorted(want_links - links)]
        ok &= not problems
        print(f"{proto['problem']}: {len(nodes)} nodes, {len(want_links)} edges -> "
              + ("IDENTICAL to the diagram (nodes, shapes, edges, edge labels)" if not problems
                 else "MISMATCH: " + "; ".join(problems)))
    return ok


def main(argv):
    if len(argv) >= 3 and argv[1] == "validate":
        return 0 if all([analyse(p) for p in argv[2:]]) else 1
    if len(argv) == 3 and argv[1] == "mermaid":
        print(mermaid(json.loads(Path(argv[2]).read_text(encoding="utf-8"))))
        return 0
    if len(argv) >= 4 and argv[1] == "sync":
        return 0 if sync(argv[2], argv[3:]) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
