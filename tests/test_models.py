# AI-assisted: generated with Claude Code and reviewed by Ansel.
from core.models import SEVERITIES, max_severity, severity_rank


def test_severity_order():
    assert severity_rank(SEVERITIES[0]) == 0
    assert max_severity(SEVERITIES[0], SEVERITIES[-1]) == SEVERITIES[-1]
    assert max_severity(SEVERITIES[-1], SEVERITIES[0]) == SEVERITIES[-1]


def test_symptom_levels_and_problem_states_start_with_the_default():
    from core.models import PROBLEM_STATES, SYMPTOM_LEVELS
    assert SYMPTOM_LEVELS == ["not_present", "watch", "concern"]
    assert PROBLEM_STATES == ["no_concern", "watch", "medical_urgency"]
