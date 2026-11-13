# AI-assisted: generated with Claude Code and reviewed by Rol 3.
from core.models import SEVERITIES, max_severity, severity_rank


def test_severity_order():
    assert severity_rank(SEVERITIES[0]) == 0
    assert max_severity(SEVERITIES[0], SEVERITIES[-1]) == SEVERITIES[-1]
    assert max_severity(SEVERITIES[-1], SEVERITIES[0]) == SEVERITIES[-1]
