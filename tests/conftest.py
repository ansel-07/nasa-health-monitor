# AI-assisted: generated with Claude Code and reviewed by Ansel.
# Lets `pytest` import the `core` package from the repo root.
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import models  # noqa: E402


@pytest.fixture(autouse=True)
def _no_session_data(monkeypatch):
    """Tests use the paths they patch in core.models, never per-session folders.

    tests/test_session_data.py turns session data back on explicitly.
    """
    monkeypatch.setattr(models, "SESSION_DATA", False)
