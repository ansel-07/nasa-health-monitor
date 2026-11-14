# AI-assisted: generated with Claude Code and reviewed by Ansel.
"""Shared constants and small helpers. Owner: Ansel.

Every other module imports from here. Do not change names without asking Ansel.
"""
import os
import shutil
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
PROTOCOLS_DIR = CONFIG_DIR / "protocols"
DATA_DIR = ROOT / "data"
SEED_DIR = DATA_DIR / "seed"

MEASUREMENTS_FILE = DATA_DIR / "measurements.csv"
ASTRONAUTS_FILE = DATA_DIR / "astronauts.csv"
EPISODES_FILE = DATA_DIR / "episodes.json"
MISSION_STATE_FILE = DATA_DIR / "mission_state.json"

# Per-session data (AGENTS.md, section 5.5). Inside the Streamlit app every browser session
# works on its own copy of data/seed/, so people using the deployed app at the same time
# never see or reset each other's data. Scripts and tests (no Streamlit session) use data/.
SESSION_DATA = True
SESSIONS_DIR = Path(tempfile.gettempdir()) / "astronaut-health-monitor-sessions"
SESSION_MAX_AGE_HOURS = 24


def _session_id() -> str | None:
    """Id of the current Streamlit browser session, or None outside the app."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        return None
    ctx = get_script_run_ctx(suppress_warning=True)
    return getattr(ctx, "session_id", None)


def _remove_old_sessions() -> None:
    limit = time.time() - SESSION_MAX_AGE_HOURS * 3600
    for folder in SESSIONS_DIR.iterdir():
        try:
            if folder.is_dir() and folder.stat().st_mtime < limit:
                shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            pass


def _create_session_dir(folder: Path) -> None:
    """Copy data/seed/ into a new session folder (atomically: a half-copied folder is never used)."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _remove_old_sessions()
    tmp = Path(tempfile.mkdtemp(dir=SESSIONS_DIR, prefix=".new-"))
    try:
        if SEED_DIR.is_dir():
            for seed_file in SEED_DIR.iterdir():
                if seed_file.is_file():
                    shutil.copyfile(seed_file, tmp / seed_file.name)
        os.rename(tmp, folder)
    except OSError:
        shutil.rmtree(tmp, ignore_errors=True)
        if not folder.is_dir():
            raise


def data_dir() -> Path:
    """Folder with the runtime data of the current session (DATA_DIR outside the app)."""
    session = _session_id() if SESSION_DATA else None
    if session is None:
        return DATA_DIR
    folder = SESSIONS_DIR / session
    if not folder.is_dir():
        _create_session_dir(folder)
    return folder


def data_file(default: Path) -> Path:
    """Where to read or write a runtime data file, e.g. data_file(MEASUREMENTS_FILE).

    Outside the app it returns `default` unchanged; inside the app, the file with the
    same name in this session's folder.
    """
    folder = data_dir()
    return default if folder == DATA_DIR else folder / default.name

# Ordered from least to most severe. Provisional: the final list comes from Edu.
# TRANSITION: will be replaced by PROBLEM_STATES once every owner has migrated (AGENTS.md, 5.3).
SEVERITIES = ["inactive", "mild", "moderate", "severe"]

# Symptom-based problems (AGENTS.md, section 5.3). Both lists go from least to most serious.
# The first value of each list is the default when no rule matches.
SYMPTOM_LEVELS = ["not_present", "watch", "concern"]
PROBLEM_STATES = ["no_concern", "watch", "medical_urgency"]

# Value compared by a numeric condition (AGENTS.md, section 6). mu / sigma = pre-flight baseline.
#   raw: x · baseline_fraction: x / mu · baseline_delta: x - mu (signed)
#   z_score: (x - mu) / sigma · abs_z_score: |(x - mu) / sigma|
CONDITION_METRICS = ["raw", "baseline_fraction", "baseline_delta", "z_score", "abs_z_score"]

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
