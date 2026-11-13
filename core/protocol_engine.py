# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Run a protocol flowchart for an active episode. Owner: Rol 6.

Node types: AGENTS.md, section 7. Build and test it with config/protocols/_example.json.
"""
from core.config import load_protocol


def current_step(episode: dict) -> dict:
    # STUB (Rol 6): return the current node with its id and display-ready text.
    protocol = load_protocol(episode["problem"])
    node_id = episode.get("current_node") or protocol["start"]
    return {"id": node_id, **protocol["nodes"][node_id]}


def submit(episode: dict, user_input: dict | None) -> dict:
    # STUB (Rol 6): apply the input, run decision/set_severity nodes automatically,
    # save protocol measurements, close on `end`, save the episode. Returns the updated episode.
    return episode
