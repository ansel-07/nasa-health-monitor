# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Measurement domains and units (#236): config.measurement_errors and validate_indicator_domains."""
import math

import pytest

from core import config

INDICATORS = {
    "trt": {"name": "Retina thickness", "unit": "µm", "valid": {"min": 0}},
    "grade": {"name": "Swelling grade", "unit": "grade", "valid": {"min": 0, "max": 5, "integer": True}},
    "acuity": {"name": "Vision sharpness", "unit": "logMAR"},
}


def m(indicator, value, unit):
    return {"indicator": indicator, "value": value, "unit": unit}


@pytest.mark.parametrize("measurement", [
    m("trt", 300.5, "µm"), m("trt", 0, "µm"), m("grade", 2, "grade"), m("grade", 3.0, "grade"),
    m("acuity", -0.2, "logMAR"),   # signed values stay valid without a domain
])
def test_valid_measurements_have_no_errors(measurement):
    assert config.measurement_errors(measurement, INDICATORS) == []


@pytest.mark.parametrize("measurement,fragment", [
    (m("trt", -1, "µm"), "cannot be below 0"),
    (m("grade", 0.5, "grade"), "whole number"),
    (m("grade", 6, "grade"), "cannot be above 5"),
    (m("trt", 300, "mm"), "must be entered in µm"),
    (m("trt", math.nan, "µm"), "finite number"),
    (m("trt", True, "µm"), "finite number"),
    (m("nope", 1, "x"), "Unknown indicator"),
])
def test_invalid_measurements_are_explained(measurement, fragment):
    errors = config.measurement_errors(measurement, INDICATORS)
    assert errors and any(fragment in e for e in errors)


@pytest.mark.parametrize("valid,fragment", [
    ({"min": "0"}, "must be a number"),
    ({"integer": "yes"}, "true or false"),
    ({"min": 5, "max": 1}, "greater than"),
    ({"minimum": 0}, "only 'min', 'max', 'integer'"),
])
def test_domain_format_is_validated(valid, fragment):
    errors = config.validate_indicator_domains({"x": {"name": "X", "unit": "u", "valid": valid}})
    assert any(fragment in e for e in errors)


def test_real_config_domains_are_well_formed():
    assert config.validate_indicator_domains(config.load_indicators()) == []


@pytest.mark.parametrize("bound", ["min", "max"])
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_domain_bounds_are_rejected(bound, value):
    assert config.validate_indicator_domains({"x": {"valid": {bound: value}}})


@pytest.mark.parametrize("domain", [{"min": math.nan}, {"max": math.inf}, {"min": "0"}, [0],
                                   {"integer": "yes"}, {"min": 5, "max": 1}])
def test_runtime_measurement_validation_rejects_invalid_domains(domain):
    assert config.measurement_errors(m("x", 2, "u"), {"x": {"unit": "u", "valid": domain}})
