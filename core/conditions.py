# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Shared condition evaluator for triggers and protocol decisions. Owner: Juan Carlos.

Condition language: AGENTS.md, section 6.
ctx = {"astronaut", "environment", "severity", "vars", "answers", "latest": {indicator: value}}
"""
from math import isfinite
from numbers import Real

from core import data
from core.models import SEVERITIES, severity_rank


_COMPARISONS = {"above", "below", "z_above", "z_below"}


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
    for operator in ("all", "any"):
        if operator in cond:
            if keys != {operator} or not isinstance(cond[operator], list) or not cond[operator]:
                raise ValueError(f"'{operator}' requires a non-empty list and no other keys.")
            for child in cond[operator]:
                _validate(child)
            return
    if "indicator" in cond or "var" in cond:
        selectors = keys & {"indicator", "var"}
        comparisons = keys & _COMPARISONS
        if len(selectors) != 1 or not comparisons or keys != selectors | comparisons:
            raise ValueError("Use one indicator or var with numeric comparisons only.")
        _validate_name(cond[next(iter(selectors))])
        for operator in comparisons:
            if not _is_number(cond[operator]):
                raise ValueError(f"'{operator}' requires a finite numeric threshold; resolve any TODO first.")
        if "var" in cond and comparisons & {"z_above", "z_below"}:
            raise ValueError("Variable z-scores require an agreed variable-to-indicator mapping.")
        return
    if keys in ({"severity_is"}, {"severity_at_least"}):
        if next(iter(cond.values())) not in SEVERITIES:
            raise ValueError("Condition severity must be a value from SEVERITIES.")
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


def _evaluate(cond: dict, ctx: dict) -> bool:
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
        if _COMPARISONS.intersection(cond) & {"z_above", "z_below"}:
            astronaut = ctx.get("astronaut")
            if not astronaut:
                return False
            z = data.z_score(astronaut, name, value)
            if not _is_number(z):
                return False
        for operator in _COMPARISONS.intersection(cond):
            actual = z if operator.startswith("z_") else value
            if operator.endswith("above"):
                if not actual > cond[operator]:
                    return False
            elif not actual < cond[operator]:
                return False
        return True
    if "severity_is" in cond or "severity_at_least" in cond:
        severity = ctx.get("severity")
        if severity is None:
            return False
        if severity not in SEVERITIES:
            raise ValueError("Context severity must be a value from SEVERITIES.")
        if "severity_is" in cond:
            return severity == cond["severity_is"]
        return severity_rank(severity) >= severity_rank(cond["severity_at_least"])
    if "environment_in" in cond:
        return ctx.get("environment") in cond["environment_in"]
    answers = ctx.get("answers", {})
    return cond["answer"] in answers and answers[cond["answer"]] == cond["equals"]


def check(cond: dict, ctx: dict) -> bool:
    """Check a condition without writing data.

    Missing or non-finite numeric data does not satisfy a condition. Invalid
    conditions raise ValueError, even inside an otherwise skipped branch.
    Variable z-score comparisons await a shared indicator mapping contract.
    """
    _validate(cond)
    return _evaluate(cond, ctx)
