# AI-assisted: generated with Claude Code and reviewed by Rol 3.
"""Config files are valid and the example protocol covers every node type."""
from core import config
from core.models import NODE_TYPES


def test_all_config_is_valid():
    assert config.validate_all() == []


def test_example_protocol_uses_every_node_type():
    protocol = config.load_protocol("_example")
    used = {node["type"] for node in protocol["nodes"].values()}
    assert used == set(NODE_TYPES)


def test_examples_hidden_by_default():
    assert "_example" not in config.load_problems()
    assert "_example" in config.load_problems(include_examples=True)


def test_validator_catches_broken_protocol():
    broken = {
        "start": "a",
        "nodes": {
            "a": {"type": "info", "text": "x", "next": "missing"},
            "orphan": {"type": "end", "outcome": "resolved", "text": "x"},
        },
    }
    errors = config.validate_protocol(broken, "broken", config.load_indicators())
    assert any("missing node" in e for e in errors)
    assert any("unreachable" in e for e in errors)
    assert any("no 'end'" in e for e in errors)
