# AI-assisted: generated with Codex and reviewed by Juan Carlos.
"""Condition language tests using synthetic values, not medical thresholds."""
from copy import deepcopy
from math import nextafter

import pytest

from core import conditions
from core.models import PROBLEM_STATES, SEVERITIES, SYMPTOM_LEVELS


@pytest.mark.parametrize("actual", SYMPTOM_LEVELS)
@pytest.mark.parametrize("required", SYMPTOM_LEVELS)
def test_symptom_level_conditions(actual, required):
    context = {"symptoms": {"a": actual}}
    assert conditions.check({"symptom": "a", "level_is": required}, context) is (actual == required)
    assert conditions.check({"symptom": "a", "level_at_least": required}, context) is (
        SYMPTOM_LEVELS.index(actual) >= SYMPTOM_LEVELS.index(required))


@pytest.mark.parametrize("actual", PROBLEM_STATES)
@pytest.mark.parametrize("required", PROBLEM_STATES)
def test_problem_state_severity_conditions(actual, required):
    assert conditions.check({"severity_is": required}, {"severity": actual}) is (actual == required)
    assert conditions.check({"severity_at_least": required}, {"severity": actual}) is (
        PROBLEM_STATES.index(actual) >= PROBLEM_STATES.index(required))


def test_count_nested_symptoms_and_environment():
    context = {"symptoms": {"a": "concern", "b": "watch"}, "environment": "mars"}
    items = [{"symptom": "a", "level_at_least": "watch"},
             {"symptom": "b", "level_is": "concern"}, {"environment_in": ["mars"]}]
    assert conditions.check({"count_at_least": 2, "of": items}, context)
    assert not conditions.check({"count_at_least": 3, "of": items}, context)
    assert not conditions.check({"symptom": "missing", "level_is": "not_present"}, context)


@pytest.mark.parametrize("condition", [
    {"count_at_least": True, "of": [{"environment_in": ["mars"]}]},
    {"count_at_least": 0, "of": [{"environment_in": ["mars"]}]},
    {"count_at_least": 2, "of": [{"environment_in": ["mars"]}]},
    {"count_at_least": 1, "of": []}, {"count_at_least": 1, "of": [{}]},
    {"symptom": "a", "level_is": "unknown"},
    {"symptom": "a", "level_is": "watch", "level_at_least": "watch"},
])
def test_invalid_symptom_conditions(condition):
    with pytest.raises(ValueError):
        conditions.check(condition, {})


def test_count_validates_all_children_and_variable_mappings():
    with pytest.raises(ValueError, match="var_indicators"):
        conditions.check({"count_at_least": 1, "of": [
            {"environment_in": ["mars"]}, {"var": "after", "z_above": 2}]}, {"environment": "mars"})
    with pytest.raises(ValueError, match="Context symptom"):
        conditions.check({"symptom": "a", "level_is": "watch"}, {"symptoms": {"a": "invalid"}})


@pytest.fixture
def ctx():
    return {
        "astronaut": "a1", "environment": "mars", "severity": "moderate",
        "latest": {"_example_indicator": 20}, "vars": {"value_after": 20},
        "answers": {"has_symptom": "yes"},
    }


@pytest.mark.parametrize("selector", ["indicator", "var"])
@pytest.mark.parametrize("operator,threshold,expected", [
    ("above", 10, True), ("above", 20, False), ("above", 30, False),
    ("below", 30, True), ("below", 20, False), ("below", 10, False),
])
def test_strict_numeric_comparisons(ctx, selector, operator, threshold, expected):
    name = "_example_indicator" if selector == "indicator" else "value_after"
    assert conditions.check({selector: name, operator: threshold}, ctx) is expected


def test_multiple_comparisons_require_all(ctx):
    assert conditions.check({"var": "value_after", "above": 10, "below": 30}, ctx)
    assert not conditions.check({"var": "value_after", "above": 10, "below": 20}, ctx)


@pytest.mark.parametrize("operator,z,expected", [
    ("z_above", 3, True), ("z_above", 2, False), ("z_above", 1, False),
    ("z_below", 1, True), ("z_below", 2, False), ("z_below", 3, False),
])
def test_z_score_uses_data_contract(ctx, monkeypatch, operator, z, expected):
    calls = []

    def z_score(*args):
        calls.append(args)
        return z

    monkeypatch.setattr(conditions.data, "z_score", z_score)
    assert conditions.check({"indicator": "_example_indicator", operator: 2}, ctx) is expected
    assert calls == [("a1", "_example_indicator", 20)]


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), "20", True])
@pytest.mark.parametrize("selector,section,name", [
    ("indicator", "latest", "_example_indicator"), ("var", "vars", "value_after"),
])
def test_unavailable_or_invalid_measurements(ctx, value, selector, section, name):
    ctx[section][name] = value
    assert not conditions.check({selector: name, "above": 10}, ctx)


@pytest.mark.parametrize("z", [None, float("nan"), float("inf")])
def test_unavailable_baseline(ctx, monkeypatch, z):
    monkeypatch.setattr(conditions.data, "z_score", lambda *args: z)
    assert not conditions.check({"indicator": "_example_indicator", "z_above": 2}, ctx)


@pytest.mark.parametrize("cond", [
    {"indicator": "missing", "above": 10}, {"var": "missing", "below": 30},
    {"answer": "missing", "equals": None}, {"severity_is": "mild"},
    {"environment_in": ["mars"]}, {"indicator": "_example_indicator", "z_above": 2},
])
def test_missing_context_does_not_match(cond):
    assert conditions.check(cond, {}) is False


@pytest.mark.parametrize("actual", SEVERITIES)
@pytest.mark.parametrize("required", SEVERITIES)
def test_severity_order(ctx, actual, required):
    ctx["severity"] = actual
    assert conditions.check({"severity_is": required}, ctx) is (actual == required)
    assert conditions.check({"severity_at_least": required}, ctx) is (
        SEVERITIES.index(actual) >= SEVERITIES.index(required)
    )


def test_environment_and_answers(ctx):
    assert conditions.check({"environment_in": ["iss", "mars"]}, ctx)
    assert not conditions.check({"environment_in": ["iss"]}, ctx)
    assert conditions.check({"answer": "has_symptom", "equals": "yes"}, ctx)
    assert not conditions.check({"answer": "has_symptom", "equals": "no"}, ctx)
    ctx["answers"]["has_symptom"] = False
    assert conditions.check({"answer": "has_symptom", "equals": False}, ctx)


def test_nested_conditions_and_no_context_mutation(ctx):
    original = deepcopy(ctx)
    cond = {"all": [
        {"environment_in": ["mars"]},
        {"any": [{"severity_is": "severe"}, {"answer": "has_symptom", "equals": "yes"}]},
    ]}
    assert conditions.check(cond, ctx)
    assert ctx == original
    ctx["environment"] = "iss"
    assert not conditions.check(cond, ctx)
    assert not conditions.check({"any": [{"severity_is": "mild"}, {"severity_is": "severe"}]}, ctx)


@pytest.mark.parametrize("cond", [
    {}, None, [], {"unknown": 1}, {"all": []}, {"any": []}, {"all": {}},
    {"all": [{"severity_is": "mild"}], "severity_is": "mild"},
    {"indicator": "x"}, {"indicator": "x", "above": 1, "typo": 2},
    {"indicator": "x", "var": "x", "above": 1},
    {"indicator": "x", "above": "TODO_EDU"},
    {"indicator": "x", "above": True}, {"indicator": "x", "above": float("nan")},
    {"indicator": "x", "below": float("inf")}, {"indicator": "", "above": 1},
    {"severity_is": "unknown"}, {"severity_at_least": "TODO_EDU"},
    {"environment_in": "mars"}, {"environment_in": []}, {"environment_in": [None]},
    {"answer": "x"}, {"answer": "x", "equals": "TODO_EDU"},
    {"answer": "x", "equals": []},
    {"severity_is": "mild", "environment_in": ["mars"]},
])
def test_invalid_conditions_raise_even_when_context_is_empty(cond):
    with pytest.raises(ValueError):
        conditions.check(cond, {})


@pytest.mark.parametrize("operator", ["z_above", "z_below"])
def test_variable_z_score_requires_mapping(ctx, operator):
    with pytest.raises(ValueError, match="variable-to-indicator"):
        conditions.check({"var": "value_after", operator: 2}, ctx)


@pytest.mark.parametrize("operator,first", [("all", "mild"), ("any", "moderate")])
def test_invalid_branches_are_not_hidden_by_short_circuit(ctx, operator, first):
    with pytest.raises(ValueError):
        conditions.check({operator: [{"severity_is": first}, {"typo": 1}]}, ctx)


def test_invalid_context_severity(ctx):
    ctx["severity"] = "unknown"
    with pytest.raises(ValueError, match="Context severity"):
        conditions.check({"severity_at_least": "mild"}, ctx)


@pytest.mark.parametrize("selector", ["indicator", "var"])
@pytest.mark.parametrize("operator,threshold,expected", [
    ("at_least", nextafter(20.0, float("-inf")), True),
    ("at_least", 20, True),
    ("at_least", nextafter(20.0, float("inf")), False),
    ("at_most", nextafter(20.0, float("-inf")), False),
    ("at_most", 20, True),
    ("at_most", nextafter(20.0, float("inf")), True),
])
def test_inclusive_comparisons_at_and_immediately_around_boundary(ctx, selector, operator, threshold, expected):
    name = "_example_indicator" if selector == "indicator" else "value_after"
    assert conditions.check({selector: name, operator: threshold}, ctx) is expected


def test_inclusive_range_can_include_both_endpoints(ctx):
    assert conditions.check({"var": "value_after", "at_least": 20, "at_most": 20}, ctx)
    assert not conditions.check({"var": "value_after", "above": 20, "at_most": 30}, ctx)
    assert conditions.check({"all": [
        {"indicator": "_example_indicator", "at_least": 20},
        {"any": [{"var": "value_after", "at_most": 20}, {"environment_in": ["iss"]}]},
    ]}, ctx)


@pytest.mark.parametrize("operator", ["at_least", "at_most"])
@pytest.mark.parametrize("threshold", ["TODO_EDU", None, True, float("nan"), float("inf")])
def test_inclusive_thresholds_require_finite_numbers(ctx, operator, threshold):
    with pytest.raises(ValueError, match="finite numeric threshold"):
        conditions.check({"indicator": "_example_indicator", operator: threshold}, ctx)


@pytest.mark.parametrize("operator", ["at_least", "at_most"])
def test_inclusive_comparison_missing_data_is_false(ctx, operator):
    assert not conditions.check({"indicator": "missing", operator: 20}, ctx)
    assert not conditions.check({"var": "missing", operator: 20}, ctx)


@pytest.mark.parametrize("operator,z,threshold,expected", [
    ("z_above", 3, 2, True), ("z_above", 2, 2, False), ("z_above", 1, 2, False),
    ("z_below", -3, -2, True), ("z_below", -2, -2, False), ("z_below", -1, -2, False),
])
def test_variable_z_score_uses_explicit_indicator_and_saved_value(ctx, monkeypatch, operator, z, threshold, expected):
    ctx["var_indicators"] = {"value_after": "_example_indicator"}
    ctx["latest"]["_example_indicator"] = 99
    original = deepcopy(ctx)
    calls = []

    def z_score(*args):
        calls.append(args)
        return z

    monkeypatch.setattr(conditions.data, "z_score", z_score)
    assert conditions.check({"var": "value_after", operator: threshold}, ctx) is expected
    assert calls == [("a1", "_example_indicator", 20)]
    assert ctx == original


@pytest.mark.parametrize("mapping", [None, [], {}, {"value_after": ""},
                                      {"value_after": "TODO_EDU"}, {"value_after": 1}])
def test_invalid_variable_mapping_is_reported(ctx, mapping):
    ctx["var_indicators"] = mapping
    with pytest.raises(ValueError, match="variable-to-indicator"):
        conditions.check({"var": "value_after", "z_above": 2}, ctx)


@pytest.mark.parametrize("operator,first", [("all", "mild"), ("any", "moderate")])
def test_missing_variable_mapping_cannot_be_hidden_by_short_circuit(ctx, operator, first):
    with pytest.raises(ValueError, match="var_indicators"):
        conditions.check({operator: [
            {"severity_is": first}, {"var": "value_after", "z_above": 2},
        ]}, ctx)


@pytest.mark.parametrize("z", [None, float("nan"), float("inf")])
def test_variable_z_score_without_valid_baseline_is_false(ctx, monkeypatch, z):
    ctx["var_indicators"] = {"value_after": "_example_indicator"}
    monkeypatch.setattr(conditions.data, "z_score", lambda *args: z)
    assert not conditions.check({"var": "value_after", "z_above": 2}, ctx)


def test_variable_z_score_with_missing_value_does_not_use_latest(ctx):
    ctx["var_indicators"] = {"value_after": "_example_indicator"}
    del ctx["vars"]["value_after"]
    assert not conditions.check({"var": "value_after", "z_above": 2}, ctx)


def test_variable_z_score_uses_real_personal_baselines(tmp_path, monkeypatch):
    from core import data, models

    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    for astronaut, values in (("a1", (8, 10, 12)), ("a2", (14, 16, 18))):
        for index, value in enumerate(values, start=1):
            data.add_measurement({
                "timestamp": f"2027-03-{index:02d}T08:00:00", "astronaut": astronaut,
                "indicator": "_example_indicator", "value": value, "unit": "units",
                "phase": "preflight", "source": "simulated",
            })
    context = {"astronaut": "a1", "vars": {"value_after": 16},
               "var_indicators": {"value_after": "_example_indicator"},
               "latest": {"_example_indicator": 10}}
    condition = {"var": "value_after", "above": 12, "z_above": 2}
    assert conditions.check(condition, context)
    context["astronaut"] = "a2"
    assert not conditions.check(condition, context)
    context["astronaut"] = "a3"
    assert not conditions.check(condition, context)
