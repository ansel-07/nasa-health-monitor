# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Simulated mission clock. Owner: Fran.

STUBS with the final signatures (AGENTS.md, section 6).
"""
from datetime import datetime

from core.config import load_mission


def now() -> datetime:
    # STUB (Fran): current simulated mission time (store it so it survives reruns)
    return datetime.fromisoformat(load_mission()["start"])


def advance(hours: int = 24) -> list[dict]:
    # STUB (Fran): move the clock forward and return the simulated measurements
    # that become visible. The caller passes each one to episodes.on_new_measurement().
    return []
