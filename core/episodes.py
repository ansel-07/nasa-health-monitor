# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Episode lifecycle: open, confirm, dismiss, pending list. Owner: Rol 5.

Rules: AGENTS.md, section 8. Storage goes through core/data.py only.
"""


def on_new_measurement(measurement: dict, environment: str) -> dict | None:
    # STUB (Rol 5): save the measurement, evaluate triggers, open an episode
    # (pending_confirmation) or add to pending; return the open episode if any.
    return None


def confirm(episode_id: str, measurement: dict) -> dict:
    # STUB (Rol 5): repeat measurement -> "active" (severity from this measurement) or "dismissed".
    return {"id": episode_id, "status": "dismissed"}


def get_pending(astronaut: str) -> list[dict]:
    # STUB (Rol 5): pending triggers for this astronaut, most severe first.
    return []
