# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Evaluate a new measurement against the problems in config/problems.json. Owner: Juan Carlos.

Rules: AGENTS.md, sections 5.3, 7 and 10.
"""
from math import isfinite
from numbers import Real

from core import conditions, config, data
from core.models import PROBLEM_STATES, SEVERITIES, SYMPTOM_LEVELS, max_severity


def _indicator_ids(cond: dict) -> set[str]:
    """Collect dependencies from an already validated condition."""
    for operator in ("all", "any", "of"):
        if operator in cond:
            return set().union(*(_indicator_ids(child) for child in cond[operator]))
    if "indicator" in cond:
        return {cond["indicator"]}
    if "environment_in" in cond:
        return set()
    raise ValueError("Triggers only support indicators, environments, all and any.")


def _leaves(cond: dict):
    for key in ("all", "any", "of"):
        if key in cond:
            for child in cond[key]:
                yield from _leaves(child)
            return
    yield cond


def _validate_symptom_problem(problem: dict) -> set[str]:
    symptoms, states = problem.get("symptoms"), problem.get("states")
    if not isinstance(symptoms, dict) or not symptoms or not isinstance(states, list) or not states:
        raise ValueError("Symptom problems require non-empty symptoms and states.")
    indicators = set()
    for sid, symptom in symptoms.items():
        if not isinstance(symptom, dict) or not isinstance(symptom.get("levels"), list) or not symptom["levels"]:
            raise ValueError(f"Symptom '{sid}' requires a non-empty levels list.")
        for rule in symptom["levels"]:
            if not isinstance(rule, dict) or rule.get("level") not in SYMPTOM_LEVELS[1:] or "when" not in rule:
                raise ValueError(f"Symptom '{sid}' has an invalid level rule.")
            if "environments" in rule and (not isinstance(rule["environments"], list) or any(
                not isinstance(env, str) or not env.strip() or env.startswith("TODO") for env in rule["environments"]
            )):
                raise ValueError(f"Symptom '{sid}' has invalid environments.")
            conditions.check(rule["when"], {})
            referenced = _indicator_ids(rule["when"])
            if not referenced:
                raise ValueError(f"Symptom '{sid}' must reference an indicator.")
            indicators.update(referenced)
    for rule in states:
        if not isinstance(rule, dict) or rule.get("state") not in PROBLEM_STATES[1:] or "when" not in rule:
            raise ValueError("Problem state rules require a supported state and condition.")
        conditions.check(rule["when"], {})
        for leaf in _leaves(rule["when"]):
            if "symptom" in leaf:
                if leaf["symptom"] not in symptoms:
                    raise ValueError(f"Unknown symptom '{leaf['symptom']}' in state condition.")
            elif "environment_in" not in leaf:
                raise ValueError("Problem states only support symptom and environment conditions.")
    return indicators


def _symptom_levels(problem: dict, ctx: dict) -> dict:
    levels = {}
    for sid, symptom in problem["symptoms"].items():
        levels[sid] = SYMPTOM_LEVELS[0]
        for rule in symptom["levels"]:
            if "environments" in rule and ctx["environment"] not in rule["environments"]:
                continue
            if conditions.check(rule["when"], ctx):
                levels[sid] = rule["level"]
                break
    return levels


def _condition_evidence(cond: dict, ctx: dict) -> set[str]:
    """Indicators in true branches of an already validated, matching condition."""
    if not conditions.check(cond, ctx):
        return set()
    for operator in ("all", "any", "of"):
        if operator in cond:
            return set().union(*(_condition_evidence(child, ctx)
                                 for child in cond[operator]))
    if "indicator" in cond:
        return {cond["indicator"]}
    return set()


def _supports_symptom_alert(problem: dict, ctx: dict, levels: dict, indicator: str) -> bool:
    """The incoming indicator must feed a matching positive symptom level.

    A newly revealed normal row must not open or queue a confirmation based on
    another indicator's positive symptom. Only true branches of the first
    matching level rule supply evidence. The problem state still uses all latest
    symptom levels, including those supplied by other indicators.
    """
    for sid, symptom in problem["symptoms"].items():
        if levels[sid] == SYMPTOM_LEVELS[0] or not any(
            indicator in _indicator_ids(rule["when"]) for rule in symptom["levels"]
        ):
            continue
        for rule in symptom["levels"]:
            if "environments" in rule and ctx["environment"] not in rule["environments"]:
                continue
            if conditions.check(rule["when"], ctx):
                if indicator in _condition_evidence(rule["when"], ctx):
                    return True
                break
    return False


def assessment_issues(problems: dict, astronaut: str, indicator: str, environment: str) -> list[str]:
    """Read-only warnings for the selected indicator and related incomplete assessments.

    Takes the loaded problem configuration. Returns at most two messages: the
    selected indicator's reason, if unavailable, and a count of other unavailable
    indicators in related problems. Repeated rules count each indicator once.
    Environment restrictions and example exclusions match detection. This does
    not change detection results, measurements or episode state.
    """
    ctx = {"astronaut": astronaut, "environment": environment, "latest": data.latest_values(astronaut)}
    issues = {}
    for pid, problem in problems.items():
        if pid.startswith("_"):
            continue
        rules = ([rule for symptom in problem["symptoms"].values() for rule in symptom["levels"]]
                 if "symptoms" in problem else problem.get("triggers", []))
        rules = [rule for rule in rules if "environments" not in rule or environment in rule["environments"]]
        if not any(_indicator_ids(rule["when"]) & {indicator} for rule in rules):
            continue
        for rule in rules:
            for leaf in _leaves(rule["when"]):
                name = leaf.get("indicator")
                if name is None:
                    continue
                value = ctx["latest"].get(name)
                if not conditions._is_number(value):
                    issues[name] = f"Cannot evaluate {name}: a measurement is unavailable."
                elif conditions._metric_value(leaf, ctx) is None or (
                    {"z_above", "z_below"}.intersection(leaf)
                    and not conditions._is_number(data.z_score(astronaut, name, value))
                ):
                    issues[name] = (f"Cannot evaluate {name}: no valid pre-flight baseline "
                                  "(at least two measurements and positive standard deviation; "
                                  "baseline fractions also require a positive mean).")
    messages = [issues[indicator]] if indicator in issues else []
    others = len(issues.keys() - {indicator})
    if others:
        messages.append("1 other indicator has an incomplete assessment." if others == 1
                        else f"{others} other indicators have incomplete assessments.")
    return messages


def _validate_trigger(trigger: dict) -> set[str]:
    if not isinstance(trigger, dict) or not {"severity", "when"} <= trigger.keys():
        raise ValueError("A trigger requires severity and when fields.")
    if trigger["severity"] not in SEVERITIES:
        raise ValueError("Trigger severity must be a value from SEVERITIES.")
    if "environments" in trigger:
        environments = trigger["environments"]
        if not isinstance(environments, list) or any(
            not isinstance(env, str) or not env.strip() or env.startswith("TODO")
            for env in environments
        ):
            raise ValueError("Trigger environments must be a list of names without TODO placeholders.")
    # The public evaluator validates all branches before checking missing data.
    # An empty context makes this validation independent of stored measurements.
    conditions.check(trigger["when"], {})
    indicators = _indicator_ids(trigger["when"])
    if not indicators:
        raise ValueError("A trigger must reference at least one indicator.")
    return indicators


def evaluate(measurement: dict, environment: str) -> list[dict]:
    """Evaluate one new measurement without saving data or opening episodes.

    Callers supply only new mission measurements, including newly revealed
    simulated ones. History is never scanned here. Only rules referencing the
    new indicator are evaluated, using latest values for the other indicators.
    Symptom alerts require positive evidence from the incoming indicator's
    matching level rule. State still uses all latest values. Legacy any rules
    retain their existing behavior, including another indicator's matching branch.
    Results follow configuration order and describe the incoming measurement.
    Invalid configuration raises ValueError; missing baselines yield z=None.
    """
    if not isinstance(measurement, dict):
        raise ValueError("Measurement must be an object.")
    for field in ("astronaut", "indicator"):
        name = measurement.get(field)
        if not isinstance(name, str) or not name.strip() or name.startswith("TODO"):
            raise ValueError(f"Measurement {field} must be a name without TODO placeholders.")
    value = measurement.get("value")
    if not isinstance(value, Real) or isinstance(value, bool) or not isfinite(value):
        raise ValueError("Measurement value must be a finite number.")

    astronaut = measurement["astronaut"]
    indicator = measurement["indicator"]
    latest = dict(data.latest_values(astronaut))
    latest[indicator] = value
    ctx = {
        "astronaut": astronaut, "environment": environment, "severity": None,
        "vars": {}, "answers": {}, "latest": latest,
    }
    results = []
    for problem_id, problem in config.load_problems().items():
        if problem_id.startswith("_"):
            continue
        if isinstance(problem, dict) and ("symptoms" in problem or "states" in problem):
            try:
                referenced = _validate_symptom_problem(problem)
                if indicator not in referenced:
                    continue
                levels = _symptom_levels(problem, ctx)
                state_ctx = {**ctx, "symptoms": levels}
                state = next((rule["state"] for rule in problem["states"]
                              if conditions.check(rule["when"], state_ctx)), PROBLEM_STATES[0])
                if state != PROBLEM_STATES[0] and _supports_symptom_alert(problem, ctx, levels, indicator):
                    results.append({"problem": problem_id, "severity": state, "indicator": indicator,
                                    "value": value, "z": None, "symptoms": levels})
            except ValueError as error:
                raise ValueError(f"Problem '{problem_id}': {error}") from error
            continue
        if not isinstance(problem, dict) or not isinstance(problem.get("triggers"), list):
            raise ValueError(f"Problem '{problem_id}': triggers must be a list.")
        severity = None
        for index, trigger in enumerate(problem["triggers"]):
            try:
                indicators = _validate_trigger(trigger)
                if indicator not in indicators:
                    continue
                if "environments" in trigger and environment not in trigger["environments"]:
                    continue
                if conditions.check(trigger["when"], ctx):
                    severity = trigger["severity"] if severity is None else max_severity(
                        severity, trigger["severity"]
                    )
            except ValueError as error:
                raise ValueError(f"Problem '{problem_id}', trigger {index}: {error}") from error
        if severity is not None:
            results.append({
                "problem": problem_id, "severity": severity, "indicator": indicator,
                "value": value, "z": None,
            })
    if results:
        z = data.z_score(astronaut, indicator, value)
        if not isinstance(z, Real) or isinstance(z, bool) or not isfinite(z):
            z = None
        for result in results:
            result["z"] = z
    return results


def symptom_levels(problem_id: str, astronaut: str, environment: str) -> dict:
    """Current level of each symptom of a symptom-based problem: {symptom_id: level}.

    Contract: AGENTS.md, sections 5.3 and 7. Uses only the latest value of each
    indicator. Levels come from SYMPTOM_LEVELS; "not_present" when no rule matches.
    """
    problem = config.load_problems(include_examples=True)[problem_id]
    if "symptoms" not in problem and "states" not in problem:
        return {}
    _validate_symptom_problem(problem)
    return _symptom_levels(problem, {"astronaut": astronaut, "environment": environment,
                                     "latest": data.latest_values(astronaut)})
