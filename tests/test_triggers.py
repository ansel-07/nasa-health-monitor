# AI-assisted: generated with Codex and reviewed by Juan Carlos (review pending).
"""Trigger integration tests with synthetic rules, not medical thresholds."""
from copy import deepcopy

import pytest

from core import triggers


def rule(severity="mild", when=None, **extra):
    return {
        "severity": severity,
        "when": {"indicator": "x", "above": 10} if when is None else when,
        **extra,
    }


@pytest.fixture
def setup(monkeypatch):
    measurement = {
        "timestamp": "2027-04-10T08:00:00", "astronaut": "a1", "indicator": "x",
        "value": 20, "unit": "example", "phase": "mission", "source": "manual",
    }
    problems = {"problem_a": {"triggers": [rule()]}}
    latest = {"x": 0, "y": 30}
    monkeypatch.setattr(triggers.config, "load_problems", lambda: problems)

    def latest_values(astronaut):
        assert astronaut == "a1"
        return latest

    monkeypatch.setattr(triggers.data, "latest_values", latest_values)
    monkeypatch.setattr(triggers.data, "z_score", lambda *args: None)

    def unexpected_write(*args, **kwargs):
        pytest.fail("Trigger evaluation must not write measurements, episodes or pending items.")

    for name in ("add_measurement", "save_episode", "save_pending"):
        monkeypatch.setattr(triggers.data, name, unexpected_write)
    return measurement, problems, latest


def test_result_contract_and_no_mutation(setup, monkeypatch):
    measurement, problems, latest = setup
    original = deepcopy(setup)
    calls = []

    def z_score(*args):
        calls.append(args)
        return 3.0

    monkeypatch.setattr(triggers.data, "z_score", z_score)
    assert triggers.evaluate(measurement, "mars") == [{
        "problem": "problem_a", "severity": "mild", "indicator": "x", "value": 20, "z": 3.0,
    }]
    assert calls == [("a1", "x", 20)]
    assert (measurement, problems, latest) == original


@pytest.mark.parametrize("symptoms", [False, True])
def test_assessment_issues_focuses_selected_indicator_and_counts_unique_others(setup, monkeypatch, symptoms):
    _, problems, latest = setup
    latest.clear()
    latest["x"] = 20
    rules = [rule(when={"indicator": "x", "metric": "baseline_delta", "above": 5}),
             rule(when={"all": [{"indicator": "x", "above": 5}, {"indicator": "y", "above": 5}]}),
             rule(when={"indicator": "y", "above": 10}),
             rule(when={"any": [{"indicator": "z", "above": 5}, {"environment_in": ["mars"]}]}),
             rule(when={"indicator": "moon_only", "above": 5}, environments=["moon"])]
    problems["problem_a"] = ({"symptoms": {str(i): {"levels": [{"level": "watch", **r}]}
                                            for i, r in enumerate(rules)}} if symptoms else {"triggers": rules})
    problems["unrelated"] = {"triggers": [rule(when={"indicator": "unrelated", "above": 5})]}
    problems["_example"] = {"triggers": [rule(when={"all": [
        {"indicator": "x", "above": 5}, {"indicator": "fixture", "above": 5}]})]}
    monkeypatch.setattr(triggers.data, "get_baseline", lambda *args: None)
    before = deepcopy((problems, latest))

    issues = triggers.assessment_issues(problems, "a1", "x", "mars")

    assert len(issues) == 2
    assert "Cannot evaluate x: no valid pre-flight baseline" in issues[0]
    assert issues[1] == "2 other indicators have incomplete assessments."
    assert (problems, latest) == before


def test_assessment_issues_does_not_call_selected_indicator_unevaluable_when_only_another_is_missing(setup):
    _, problems, _ = setup
    problems["problem_a"]["triggers"].append(rule(when={"indicator": "missing", "above": 5}))
    assert triggers.assessment_issues(problems, "a1", "x", "mars") == [
        "1 other indicator has an incomplete assessment."]


def test_assessment_issues_only_selected_missing_and_complete_readings(setup):
    _, problems, latest = setup
    assert triggers.assessment_issues(problems, "a1", "x", "mars") == []
    del latest["x"]
    assert triggers.assessment_issues(problems, "a1", "x", "mars") == [
        "Cannot evaluate x: a measurement is unavailable."]


def test_highest_severity_per_problem_and_configuration_order(setup):
    measurement, problems, _ = setup
    problems["problem_a"]["triggers"] = [rule("moderate"), rule("severe"), rule("mild")]
    problems["problem_b"] = {"triggers": [rule("moderate"), rule("moderate")]}
    results = triggers.evaluate(measurement, "mars")
    assert [(r["problem"], r["severity"]) for r in results] == [
        ("problem_a", "severe"), ("problem_b", "moderate"),
    ]


def test_higher_severity_requires_its_own_condition_to_match(setup):
    measurement, problems, _ = setup
    problems["problem_a"]["triggers"] += [rule(
        "severe", when={"indicator": "x", "above": 30},
    )]
    assert triggers.evaluate(measurement, "mars")[0]["severity"] == "mild"


@pytest.mark.parametrize("environment,expected", [("mars", "severe"), ("iss", "mild")])
def test_environment_restriction(setup, environment, expected):
    measurement, problems, _ = setup
    problems["problem_a"]["triggers"] += [rule("severe", environments=["mars"])]
    assert triggers.evaluate(measurement, environment)[0]["severity"] == expected


@pytest.mark.parametrize("value", [0, 10])
def test_no_matching_trigger(setup, value):
    measurement, _, _ = setup
    measurement["value"] = value
    assert triggers.evaluate(measurement, "mars") == []


def test_ignores_other_indicators_and_fixtures(setup):
    measurement, problems, _ = setup
    problems["problem_a"]["triggers"] = [rule(when={"indicator": "y", "above": 10})]
    problems["_example"] = {"triggers": [rule()]}
    problems["_invalid_fixture"] = None
    assert triggers.evaluate(measurement, "mars") == []


def test_no_problems(setup):
    measurement, problems, _ = setup
    problems.clear()
    assert triggers.evaluate(measurement, "mars") == []


def test_nested_conditions_use_new_and_latest_measurements(setup):
    measurement, problems, latest = setup
    problems["problem_a"]["triggers"] = [rule(when={"all": [
        {"environment_in": ["mars"]},
        {"any": [{"indicator": "x", "above": 10}, {"indicator": "z", "above": 10}]},
        {"indicator": "y", "above": 20},
    ]})]
    assert triggers.evaluate(measurement, "mars")
    assert not triggers.evaluate(measurement, "iss")
    del latest["y"]
    assert not triggers.evaluate(measurement, "mars")


def test_any_may_match_another_indicators_branch(setup):
    measurement, problems, _ = setup
    measurement["value"] = 0
    problems["problem_a"]["triggers"] = [rule(when={"any": [
        {"indicator": "x", "above": 10}, {"indicator": "y", "above": 20},
    ]})]
    result = triggers.evaluate(measurement, "mars")[0]
    assert result["indicator"] == "x"
    assert result["value"] == 0


@pytest.mark.parametrize("operator,z,expected", [
    ("z_above", 3, True), ("z_above", 2, False),
    ("z_below", -3, True), ("z_below", -2, False),
    ("z_above", None, False),
])
def test_z_score_conditions(setup, monkeypatch, operator, z, expected):
    measurement, problems, _ = setup
    threshold = 2 if operator == "z_above" else -2
    problems["problem_a"]["triggers"] = [rule(when={"indicator": "x", operator: threshold})]
    monkeypatch.setattr(triggers.data, "z_score", lambda *args: z)
    results = triggers.evaluate(measurement, "mars")
    assert bool(results) is expected
    if results:
        assert results[0]["z"] == z


@pytest.mark.parametrize("z", [None, float("nan"), float("inf"), True])
def test_absolute_threshold_works_without_valid_z_score(setup, monkeypatch, z):
    measurement, _, _ = setup
    monkeypatch.setattr(triggers.data, "z_score", lambda *args: z)
    assert triggers.evaluate(measurement, "mars")[0]["z"] is None


@pytest.mark.parametrize("source", ["manual", "protocol", "simulated"])
def test_all_new_measurement_sources_are_evaluated(setup, source):
    measurement, _, _ = setup
    measurement["source"] = source
    assert triggers.evaluate(measurement, "mars")


@pytest.mark.parametrize("when", [
    {"var": "x", "above": 10}, {"answer": "x", "equals": "yes"},
    {"severity_is": "mild"}, {"severity_at_least": "mild"},
    {"all": [{"indicator": "x", "above": 10}, {"severity_is": "mild"}]},
    {"environment_in": ["mars"]},
    {"any": [{"indicator": "x", "above": 10}, {"answer": "x", "equals": "yes"}]},
])
def test_protocol_context_and_indicator_free_triggers_are_rejected(setup, when):
    measurement, problems, _ = setup
    problems["problem_a"]["triggers"] = [rule(when=when)]
    with pytest.raises(ValueError, match="Problem 'problem_a', trigger 0"):
        triggers.evaluate(measurement, "mars")


@pytest.mark.parametrize("invalid", [
    None, {}, {"severity": "mild"}, rule("unknown"),
    rule(when={"indicator": "x", "above": "TODO_EDU"}),
    rule(when={"any": [{"indicator": "x", "above": 10}, {"typo": 1}]}),
    rule(environments="mars"), rule(environments=[None]),
])
def test_invalid_configuration_reports_problem_and_trigger(setup, invalid):
    measurement, problems, _ = setup
    problems["problem_a"]["triggers"] = [invalid]
    with pytest.raises(ValueError, match="Problem 'problem_a', trigger 0"):
        triggers.evaluate(measurement, "mars")


def test_invalid_rules_are_not_hidden_by_environment_or_indicator_filter(setup):
    measurement, problems, _ = setup
    problems["problem_a"]["triggers"] = [rule(
        when={"indicator": "y", "above": "TODO_EDU"}, environments=["iss"],
    )]
    with pytest.raises(ValueError, match="TODO"):
        triggers.evaluate(measurement, "mars")


@pytest.mark.parametrize("problem", [None, {}, {"triggers": None}])
def test_invalid_problem_configuration(setup, problem):
    measurement, problems, _ = setup
    problems["problem_a"] = problem
    with pytest.raises(ValueError, match="Problem 'problem_a'"):
        triggers.evaluate(measurement, "mars")


@pytest.mark.parametrize("field,value", [
    ("astronaut", None), ("indicator", ""), ("value", None),
    ("value", "20"), ("value", True), ("value", float("nan")), ("value", float("inf")),
])
def test_invalid_measurements(setup, field, value):
    measurement, _, _ = setup
    measurement[field] = value
    with pytest.raises(ValueError, match="Measurement"):
        triggers.evaluate(measurement, "mars")
