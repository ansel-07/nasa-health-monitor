# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Simulated mission clock. Owner: Rol 4.

STUBS with the final signatures (AGENTS.md, section 6).
"""
from datetime import datetime

from core.config import load_mission


def now() -> datetime:
    # STUB (Rol 4): current simulated mission time (store it so it survives reruns)
    return datetime.fromisoformat(load_mission()["start"])


def advance(hours: int = 24) -> list[dict]:
    # STUB (Rol 4): move the clock forward and return the simulated measurements
    # that become visible. The caller passes each one to episodes.on_new_measurement().
    return []
