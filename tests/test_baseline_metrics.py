# AI-assisted: generated with Codex and reviewed by Juan Carlos.
"""Synthetic boundary cases supplied by Edu in #48; these are not normal ranges."""
from copy import deepcopy

import pytest

from core import conditions, data, models, triggers


@pytest.mark.parametrize("selector", ["indicator", "var"])
@pytest.mark.parametrize("metric,mean,std,bounds,value,expected", [
    ("baseline_fraction", 500, 10, {"below": .80}, 399, True),
    ("baseline_fraction", 500, 10, {"below": .80}, 400, False),
    ("baseline_fraction", 500, 10, {"below": .80}, 401, False),
    *[("baseline_delta", 300, 2, {"at_least": 20, "below": 55}, x, 320 <= x < 355)
      for x in (319, 320, 354, 355, 356)],
    *[("baseline_delta", 300, 2, {"at_least": 55}, x, x >= 355)
      for x in (319, 320, 354, 355, 356)],
    *[("baseline_delta", 0, .1, {"above": .50}, x, x > .50)
      for x in (.49, .50, .51, -.51)],
    *[("z_score", 10, 2, {"at_least": z}, 10 + 2*z, True) for z in (-3, -2, 2, 3)],
    *[("z_score", 10, 2, {"at_most": z}, 10 + 2*z, True) for z in (-3, -2, 2, 3)],
    *[("abs_z_score", 10, 2, {"at_least": abs(z)}, 10 + 2*z, True) for z in (-3, -2, 2, 3)],
    ("raw", 10, 2, {"at_most": 5}, 5, True),
])
def test_exact_boundaries_and_saved_variables(monkeypatch, selector, metric, mean, std, bounds, value, expected):
    calls = []

    def baseline(astronaut, indicator):
        calls.append((astronaut, indicator))
        return {"mean": mean, "std": std, "n": 3}

    monkeypatch.setattr(data, "get_baseline", baseline)
    ctx = {"astronaut": "a1", "latest": {"left": value if selector == "indicator" else -999},
           "vars": {"after": value}, "var_indicators": {"after": "left"}}
    original = deepcopy(ctx)
    cond = {selector: "left" if selector == "indicator" else "after", "metric": metric, **bounds}
    assert conditions.check(cond, ctx) is expected
    assert ctx == original
    assert calls == ([] if metric == "raw" else [("a1", "left")])


@pytest.mark.parametrize("metric", ["baseline_fraction", "baseline_delta", "z_score", "abs_z_score"])
@pytest.mark.parametrize("baseline", [None, {}, {"mean": 10, "std": 2, "n": 1},
    {"mean": 10, "std": 0, "n": 3}, {"mean": 10, "std": -1, "n": 3},
    {"mean": float("nan"), "std": 2, "n": 3}, {"mean": 10, "std": float("inf"), "n": 3},
    {"mean": 10, "std": 2, "n": True}])
def test_invalid_reference_is_not_satisfied(monkeypatch, metric, baseline):
    monkeypatch.setattr(data, "get_baseline", lambda *args: baseline)
    assert not conditions.check({"indicator": "left", "metric": metric, "above": -1000},
                                {"astronaut": "a1", "latest": {"left": 20}})


@pytest.mark.parametrize("mean", [0, -10])
def test_fraction_requires_positive_mean(monkeypatch, mean):
    monkeypatch.setattr(data, "get_baseline", lambda *args: {"mean": mean, "std": 2, "n": 3})
    assert not conditions.check({"indicator": "left", "metric": "baseline_fraction", "below": 1},
                                {"astronaut": "a1", "latest": {"left": 0}})


@pytest.mark.parametrize("value", [None, True, float("nan"), float("inf"), "20"])
def test_missing_or_invalid_reading_is_not_satisfied(value):
    assert not conditions.check({"indicator": "left", "metric": "baseline_delta", "above": 0},
                                {"astronaut": "a1", "latest": {"left": value}})


@pytest.mark.parametrize("cond", [
    {"indicator": "left", "metric": "unknown", "above": 0},
    {"indicator": "left", "metric": "raw", "z_above": 0},
    {"indicator": "left", "metric": "z_score", "z_below": 0},
    {"indicator": "left", "metric": "baseline_delta"},
])
def test_invalid_metrics_are_rejected_even_in_skipped_branches(cond):
    with pytest.raises(ValueError):
        conditions.check({"any": [{"environment_in": ["mars"]}, cond]}, {"environment": "mars"})


def test_metric_variable_requires_mapping_even_in_skipped_branch():
    with pytest.raises(ValueError, match="var_indicators"):
        conditions.check({"any": [{"environment_in": ["mars"]},
            {"var": "after", "metric": "baseline_delta", "above": 0}]}, {"environment": "mars"})


def test_real_references_are_personal_and_independent_by_eye_and_site(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    monkeypatch.setattr(data, "load_indicators", lambda: {key: {} for key in ("left", "right", "site_a", "site_b")})
    for astronaut, indicator, mean in (("a1", "left", 100), ("a1", "right", 200),
                                     ("a1", "site_a", 300), ("a1", "site_b", 400),
                                     ("a2", "left", 500)):
        for day, value in enumerate((mean-1, mean+1), start=1):
            data.add_measurement({"timestamp": f"2027-03-{day:02d}T08:00:00", "astronaut": astronaut,
                "indicator": indicator, "value": value, "unit": "synthetic", "phase": "preflight", "source": "simulated"})
    cond = {"indicator": "left", "metric": "baseline_delta", "above": .50}
    ctx = {"astronaut": "a1", "latest": {"left": 100.51}}
    assert conditions.check(cond, ctx)
    for other in ("right", "site_a", "site_b", "missing"):
        assert not conditions.check({**cond, "indicator": other},
                                    {**ctx, "latest": {other: 100.51}})
    assert not conditions.check(cond, {**ctx, "astronaut": "a2"})
    data.add_measurement({"timestamp": "2027-04-01T08:00:00", "astronaut": "a1", "indicator": "left",
        "value": 999, "unit": "synthetic", "phase": "mission", "source": "manual"})
    assert conditions.check(cond, ctx)  # Mission rows never change the pre-flight reference.


@pytest.mark.parametrize("threshold", [-3, -2, 2, 3])
@pytest.mark.parametrize("operator", ["at_least", "at_most"])
def test_inclusive_z_boundaries_distinguish_both_sides(monkeypatch, threshold, operator):
    monkeypatch.setattr(data, "get_baseline", lambda *args: {"mean": 10, "std": 2, "n": 3})
    for offset in (-.001, 0, .001):
        value = 10 + 2 * (threshold + offset)
        expected = offset >= 0 if operator == "at_least" else offset <= 0
        assert conditions.check({"indicator": "left", "metric": "z_score", operator: threshold},
            {"astronaut": "a1", "latest": {"left": value}}) is expected


@pytest.mark.parametrize("selector", ["indicator", "var"])
@pytest.mark.parametrize("metric,mean,std,value,boundary", [
    ("baseline_fraction", .1, .01, .3, 3),
    ("baseline_delta", .2, .1, .7, .5),
    ("z_score", 0, .1, .3, 3),
    ("abs_z_score", 0, .1, -.3, 3),
])
@pytest.mark.parametrize("operator,expected", [
    ("above", False), ("below", False), ("at_least", True), ("at_most", True),
])
def test_derived_roundoff_preserves_boundary_operators(
        monkeypatch, selector, metric, mean, std, value, boundary, operator, expected):
    monkeypatch.setattr(data, "get_baseline", lambda *args: {"mean": mean, "std": std, "n": 3})
    ctx = {"astronaut": "a1", "latest": {"left": value}, "vars": {"after": value},
           "var_indicators": {"after": "left"}}
    assert conditions.check({selector: "left" if selector == "indicator" else "after",
                             "metric": metric, operator: boundary}, ctx) is expected


@pytest.mark.parametrize("selector", ["indicator", "var"])
@pytest.mark.parametrize("operator,sign", [("z_above", 1), ("z_below", -1)])
def test_legacy_z_roundoff_keeps_strict_boundary(monkeypatch, selector, operator, sign):
    monkeypatch.setattr(data, "z_score", lambda *args: sign * 3.0000000000000004)
    ctx = {"astronaut": "a1", "latest": {"left": .3}, "vars": {"after": .3},
           "var_indicators": {"after": "left"}}
    cond = {selector: "left" if selector == "indicator" else "after", operator: sign * 3}
    assert not conditions.check(cond, ctx)
    monkeypatch.setattr(data, "z_score", lambda *args: sign * 3.000001)
    assert conditions.check(cond, ctx)


@pytest.mark.parametrize("metric", [None, "raw"])
def test_raw_values_are_not_rounded(metric):
    cond = {"indicator": "left", "above": .5}
    if metric:
        cond["metric"] = metric
    assert conditions.check(cond, {"latest": {"left": .5000000001}})


@pytest.mark.parametrize("indicator,preflight,value,expected", [
    ("visual_acuity_left", (-.1, 0, .1), .3, "concern"),
    ("visual_acuity_left", (-.1, 0, .1), .299999, "watch"),
    ("visual_acuity_left", (-.1, 0, .1), .2, "watch"),
    ("visual_acuity_left", (-.1, 0, .1), .199999, "not_present"),
    ("refraction_left", (-.2, -.1, 0), .4, "not_present"),
    ("refraction_left", (-.2, -.1, 0), .400001, "watch"),
    ("refraction_left", (-.2, -.1, 0), .399999, "not_present"),
])
def test_configured_vision_boundaries_with_real_csv_rows(
        tmp_path, monkeypatch, indicator, preflight, value, expected):
    monkeypatch.setattr(models, "MEASUREMENTS_FILE", tmp_path / "measurements.csv")
    for day, reading in enumerate(preflight, start=1):
        data.add_measurement({"timestamp": f"2027-03-{day:02d}T08:00:00", "astronaut": "a1",
            "indicator": indicator, "value": reading, "unit": "logMAR" if "acuity" in indicator else "D",
            "phase": "preflight", "source": "simulated"})
    data.add_measurement({"timestamp": "2027-04-01T08:00:00", "astronaut": "a1",
        "indicator": indicator, "value": value, "unit": "logMAR" if "acuity" in indicator else "D",
        "phase": "mission", "source": "manual"})
    assert triggers.symptom_levels("sans", "a1", "iss")[indicator] == expected
    assert data.latest_values("a1")[indicator] == value
