import pytest
from gesa.tools.registry import TOOLS, dispatch

def test_registry_lists_three_tools():
    assert set(TOOLS) == {"intercrop_planner", "input_allocator", "planting_scheduler"}

def test_dispatch_calls_tool():
    r = dispatch("planting_scheduler", {"region": "east_africa", "season": "long_rains"})
    assert r["region"] == "east_africa"

def test_dispatch_rejects_unknown_arg():
    with pytest.raises(ValueError):
        dispatch("planting_scheduler", {"region": "x", "season": "y", "bogus": 1})
