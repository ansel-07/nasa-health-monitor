# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Shared condition evaluator for triggers and protocol decisions. Owner: Juan Carlos.

Condition language: AGENTS.md, section 6.
ctx = {"astronaut", "environment", "severity", "vars", "answers", "latest": {indicator: value}}
Numeric indicator and variable conditions also accept at_least (>=) and
at_most (<=). These compare raw values, not percentages, baseline deltas or z-scores.

Variable z-scores additionally require ctx["var_indicators"] = {save_as: indicator}.
The protocol engine supplies this mapping from measure nodes. Numeric values
remain in vars; no changes to condition JSON or the check signature are needed.
Rebuild the mapping from the protocol on each execution so restored episodes
also work. Each save_as must refer to a single indicator; the caller must reject
conflicting measure definitions. The mapping need not be persisted in episodes.
"""
from math import isfinite
from numbers import Real
from operator import ge, gt, le, lt

from core import data
from core.models import PROBLEM_STATES, SEVERITIES, SYMPTOM_LEVELS


_COMPARISONS = {
    "above": gt, "below": lt, "at_least": ge, "at_most": le,
    "z_above": gt, "z_below": lt,
}


def _is_number(value) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)


def _validate_name(value) -> None:
    if not isinstance(value, str) or not value.strip() or value.startswith("TODO"):
        raise ValueError("Condition names must be non-empty strings without TODO placeholders.")


def _validate(cond: dict) -> None:
    """Validate every branch, including branches evaluation would otherwise skip."""
    if not isinstance(cond, dict) or not cond:
        raise ValueError("A condition must be a non-empty object.")
    keys = set(cond)
    if "count_at_least" in cond or "of" in cond:
        count, items = cond.get("count_at_least"), cond.get("of")
        if (keys != {"count_at_least", "of"} or not isinstance(items, list) or not items
                or not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= len(items)):
            raise ValueError("count_at_least requires an integer from 1 to the size of a non-empty of list.")
        for child in items:
            _validate(child)
        return
    for operator in ("all", "any"):
        if operator in cond:
            if keys != {operator} or not isinstance(cond[operator], list) or not cond[operator]:
                raise ValueError(f"'{operator}' requires a non-empty list and no other keys.")
            for child in cond[operator]:
                _validate(child)
            return
    if "indicator" in cond or "var" in cond:
        selectors = keys & {"indicator", "var"}
        comparisons = keys & _COMPARISONS.keys()
        if len(selectors) != 1 or not comparisons or keys != selectors | comparisons:
            raise ValueError("Use one indicator or var with numeric comparisons only.")
        _validate_name(cond[next(iter(selectors))])
        for operator in comparisons:
            if not _is_number(cond[operator]):
                raise ValueError(f"'{operator}' requires a finite numeric threshold; resolve any TODO first.")
        return
    if keys in ({"severity_is"}, {"severity_at_least"}):
        if next(iter(cond.values())) not in SEVERITIES + PROBLEM_STATES:
            raise ValueError("Condition severity must be a known severity or problem state.")
        return
    if keys in ({"symptom", "level_is"}, {"symptom", "level_at_least"}):
        _validate_name(cond["symptom"])
        level = cond.get("level_is", cond.get("level_at_least"))
        if level not in SYMPTOM_LEVELS:
            raise ValueError("Condition symptom level must be a value from SYMPTOM_LEVELS.")
        return
    if keys == {"environment_in"}:
        environments = cond["environment_in"]
        if not isinstance(environments, list) or not environments:
            raise ValueError("'environment_in' requires a non-empty list of names.")
        for environment in environments:
            _validate_name(environment)
        return
    if keys == {"answer", "equals"}:
        _validate_name(cond["answer"])
        expected = cond["equals"]
        if isinstance(expected, str) and expected.startswith("TODO"):
            raise ValueError("Resolve the TODO answer before evaluating the condition.")
        if expected is not None and not isinstance(expected, (str, bool)) and not _is_number(expected):
            raise ValueError("'equals' requires a finite JSON scalar value.")
        return
    raise ValueError("Unknown or ambiguous condition; combine separate conditions with all or any.")


def _validate_variable_indicators(cond: dict, ctx: dict) -> None:
    """Require explicit mappings, including inside branches evaluation may skip."""
    for operator in ("all", "any", "of"):
        if operator in cond:
            for child in cond[operator]:
                _validate_variable_indicators(child, ctx)
            return
    if "var" in cond and {"z_above", "z_below"}.intersection(cond):
        mapping = ctx.get("var_indicators")
        indicator = mapping.get(cond["var"]) if isinstance(mapping, dict) else None
        if not isinstance(indicator, str) or not indicator.strip() or indicator.startswith("TODO"):
            raise ValueError(
                f"Variable '{cond['var']}' requires an explicit variable-to-indicator "
                "mapping in ctx['var_indicators']."
            )


def _evaluate(cond: dict, ctx: dict) -> bool:
    if "count_at_least" in cond:
        return sum(_evaluate(child, ctx) for child in cond["of"]) >= cond["count_at_least"]
    if "symptom" in cond:
        level = ctx.get("symptoms", {}).get(cond["symptom"])
        if level is None:
            return False
        if level not in SYMPTOM_LEVELS:
            raise ValueError("Context symptom level must be a value from SYMPTOM_LEVELS.")
        if "level_is" in cond:
            return level == cond["level_is"]
        return SYMPTOM_LEVELS.index(level) >= SYMPTOM_LEVELS.index(cond["level_at_least"])
    if "all" in cond:
        return all(_evaluate(child, ctx) for child in cond["all"])
    if "any" in cond:
        return any(_evaluate(child, ctx) for child in cond["any"])
    if "indicator" in cond or "var" in cond:
        selector = "indicator" if "indicator" in cond else "var"
        name = cond[selector]
        values = ctx.get("latest" if selector == "indicator" else "vars", {})
        value = values.get(name)
        if not _is_number(value):
            return False
        z = None
        comparisons = _COMPARISONS.keys() & cond.keys()
        if comparisons & {"z_above", "z_below"}:
            astronaut = ctx.get("astronaut")
            if not astronaut:
                return False
            indicator = ctx["var_indicators"][name] if selector == "var" else name
            z = data.z_score(astronaut, indicator, value)
            if not _is_number(z):
                return False
        for operator in comparisons:
            actual = z if operator.startswith("z_") else value
            if not _COMPARISONS[operator](actual, cond[operator]):
                return False
        return True
    if "severity_is" in cond or "severity_at_least" in cond:
        severity = ctx.get("severity")
        if severity is None:
            return False
        required = cond.get("severity_is", cond.get("severity_at_least"))
        order = PROBLEM_STATES if required in PROBLEM_STATES else SEVERITIES
        if severity not in order:
            raise ValueError("Context severity must use the same severity vocabulary as the condition.")
        if "severity_is" in cond:
            return severity == cond["severity_is"]
        return order.index(severity) >= order.index(required)
    if "environment_in" in cond:
        return ctx.get("environment") in cond["environment_in"]
    answers = ctx.get("answers", {})
    return cond["answer"] in answers and answers[cond["answer"]] == cond["equals"]


def check(cond: dict, ctx: dict) -> bool:
    """Check a condition without writing data.

    Missing or non-finite numeric data does not satisfy a condition. Invalid
    conditions raise ValueError, even inside an otherwise skipped branch.
    Variable z-scores use ctx['var_indicators'][save_as] for the baseline and
    ctx['vars'][save_as] for the measured value, never the latest indicator value.
    Missing/invalid mappings raise ValueError; missing values or baselines return
    False. Absolute variable comparisons need no mapping. Context is not mutated.
    """
    _validate(cond)
    _validate_variable_indicators(cond, ctx)
    return _evaluate(cond, ctx)
