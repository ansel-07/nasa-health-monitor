# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Shared constants and small helpers. Owner: Ansel.

Every other module imports from here. Do not change names without asking Ansel.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
PROTOCOLS_DIR = CONFIG_DIR / "protocols"
DATA_DIR = ROOT / "data"
SEED_DIR = DATA_DIR / "seed"

MEASUREMENTS_FILE = DATA_DIR / "measurements.csv"
ASTRONAUTS_FILE = DATA_DIR / "astronauts.csv"
EPISODES_FILE = DATA_DIR / "episodes.json"

# Ordered from least to most severe. Provisional: the final list comes from Edu.
# TRANSITION: will be replaced by PROBLEM_STATES once every owner has migrated (AGENTS.md, 5.3).
SEVERITIES = ["inactive", "mild", "moderate", "severe"]

# Symptom-based problems (AGENTS.md, section 5.3). Both lists go from least to most serious.
# The first value of each list is the default when no rule matches.
SYMPTOM_LEVELS = ["not_present", "watch", "concern"]
PROBLEM_STATES = ["no_concern", "watch", "medical_urgency"]

EPISODE_STATUSES = [
    "pending_confirmation",
    "active",
    "resolved",
    "monitoring",
    "handed_over",
    "dismissed",
]
OPEN_STATUSES = ["pending_confirmation", "active"]
OUTCOMES = ["resolved", "monitoring", "handed_over"]

PHASES = ["preflight", "mission"]
SOURCES = ["simulated", "manual", "protocol"]
MEASUREMENT_COLUMNS = ["timestamp", "astronaut", "indicator", "value", "unit", "phase", "source"]

CONTACT_TARGETS = ["crew_medical_officer", "flight_surgeon"]

# Mascot expressions. Provisional: the team decides the final list and when each one is used.
MOODS = ["happy", "neutral", "thinking", "worried", "serious"]
MASCOT_SIZES = ["large", "small"]

# Node type -> required fields. Optional fields are listed in AGENTS.md, section 7.
NODE_TYPES = {
    "info": ["text", "next"],
    "action": ["text", "next"],
    "measure": ["indicator", "save_as", "next"],
    "question": ["text", "save_as", "options"],
    "decision": ["branches", "default"],
    "set_severity": ["severity", "next"],
    "contact": ["target", "text", "next"],
    "end": ["outcome", "text"],
}

# Values that still have to be written by a person (Edu or Gonzalo) start with this mark.
TODO_MARK = "TODO"


def severity_rank(severity: str) -> int:
    """Position of a severity in SEVERITIES (0 = least severe)."""
    return SEVERITIES.index(severity)


def max_severity(a: str, b: str) -> str:
    """The more severe of two severities."""
    return a if severity_rank(a) >= severity_rank(b) else b
