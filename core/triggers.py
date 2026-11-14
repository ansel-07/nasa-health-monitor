# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Evaluate a new measurement against the problems in config/problems.json. Owner: Juan Carlos.

Rules: AGENTS.md, sections 5.3, 7 and 10.
"""
from math import isfinite
from numbers import Real

from core import conditions, config, data
from core.models import SEVERITIES, max_severity


def _indicator_ids(cond: dict) -> set[str]:
    """Collect dependencies from an already validated condition."""
    for operator in ("all", "any"):
        if operator in cond:
            return set().union(*(_indicator_ids(child) for child in cond[operator]))
    if "indicator" in cond:
        return {cond["indicator"]}
    if "environment_in" in cond:
        return set()
    raise ValueError("Triggers only support indicators, environments, all and any.")


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
    In an any condition, another indicator's branch may supply the match.
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
