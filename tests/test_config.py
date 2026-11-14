# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Config files are valid and the example protocol covers every node type."""
from copy import deepcopy

from core import config
from core.models import NODE_TYPES


def test_all_config_is_valid():
    assert config.validate_all() == []


def test_example_protocol_uses_every_node_type():
    protocol = config.load_protocol("_example")
    used = {node["type"] for node in protocol["nodes"].values()}
    assert used == set(NODE_TYPES)


def test_examples_hidden_by_default():
    assert "_example" not in config.load_problems()
    assert "_example" in config.load_problems(include_examples=True)


def test_validator_catches_broken_protocol():
    broken = {
        "start": "a",
        "nodes": {
            "a": {"type": "info", "text": "x", "next": "missing"},
            "orphan": {"type": "end", "outcome": "resolved", "text": "x"},
        },
    }
    errors = config.validate_protocol(broken, "broken", config.load_indicators())
    assert any("missing node" in e for e in errors)
    assert any("unreachable" in e for e in errors)
    assert any("no 'end'" in e for e in errors)


# ------------------------------------------------ symptom-based problems (5.3)

def _symptom_problem(**changes):
    problem = deepcopy(config.load_problems(include_examples=True)["_example"])
    problem.pop("triggers")
    problem.update(changes)
    return problem


def _check(problem):
    return config.validate_symptoms(problem, "p", config.load_indicators(), config.load_environments())


def test_example_symptom_format_is_valid():
    assert _check(_symptom_problem()) == []


def test_symptom_validator_catches_bad_levels_and_states():
    problem = _symptom_problem()
    problem["symptoms"]["symptom_a"]["levels"][0]["level"] = "not_present"  # default, not a rule
    problem["symptoms"]["symptom_b"]["levels"][0]["when"] = {"indicator": "nope", "above": 1}
    problem["states"][0]["state"] = "no_concern"
    problem["states"][1]["when"]["of"][0]["symptom"] = "missing_symptom"
    problem["states"][1]["when"]["of"][1]["level_at_least"] = "severe"
    errors = " | ".join(_check(problem))
    assert "level must be one of" in errors
    assert "unknown indicator 'nope'" in errors
    assert "state must be one of" in errors
    assert "unknown symptom 'missing_symptom'" in errors
    assert "unknown symptom level 'severe'" in errors


def test_symptom_validator_catches_count_at_least_out_of_range():
    problem = _symptom_problem()
    problem["states"][1]["when"]["count_at_least"] = 3
    assert any("'count_at_least' must be between" in e for e in _check(problem))


def test_inclusive_comparisons_are_valid_in_symptom_levels():
    """at_least / at_most on an indicator are >= / <=, not the count_at_least operator."""
    problem = _symptom_problem()
    problem["symptoms"]["symptom_a"]["levels"][0]["when"] = {"indicator": "_example_indicator", "at_least": 30}
    problem["symptoms"]["symptom_b"]["levels"][1]["when"] = {"indicator": "_example_indicator_2", "at_most": 1}
    assert _check(problem) == []


def test_symptom_levels_cannot_depend_on_other_symptoms():
    problem = _symptom_problem()
    problem["symptoms"]["symptom_b"]["levels"][1]["when"] = {
        "all": [{"indicator": "_example_indicator_2", "above": 1},
                {"symptom": "symptom_a", "level_is": "watch"}]}
    assert any("not allowed here" in e for e in _check(problem))


def test_protocol_symptom_conditions_must_exist():
    protocol = {
        "start": "d",
        "nodes": {
            "d": {"type": "decision", "default": "end",
                  "branches": [{"if": {"symptom": "ghost", "level_is": "concern"}, "next": "end"}]},
            "end": {"type": "end", "outcome": "resolved", "text": "x"},
        },
    }
    indicators = config.load_indicators()
    assert any("not allowed here" in e for e in config.validate_protocol(protocol, "p", indicators))
    symptoms = _symptom_problem()["symptoms"]
    assert any("unknown symptom 'ghost'" in e
               for e in config.validate_protocol(protocol, "p", indicators, symptoms))


def test_symptom_levels_stub_returns_every_symptom():
    from core.models import SYMPTOM_LEVELS
    from core.triggers import symptom_levels
    levels = symptom_levels("_example", "a1", "iss")
    assert set(levels) == {"symptom_a", "symptom_b"}
    assert all(level in SYMPTOM_LEVELS for level in levels.values())
