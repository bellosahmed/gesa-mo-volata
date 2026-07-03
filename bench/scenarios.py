"""Benchmark scenarios for Gesa Mo Volata.

Each scenario pairs a realistic farmer request with the deterministic tool
call that answers it correctly. Ground truth is never hand-written: it is
always produced by calling the real tool via `dispatch`, so it can't drift
from the actual agronomy logic and can't encode a mistake independently of
the tool it is meant to check.
"""
from gesa.tools.registry import dispatch

SCENARIOS: list[dict] = [
    {
        "name": "intercrop_maize_beans_half_hectare",
        "request": "I have 500 square meters and want to intercrop maize and beans. How should I lay it out?",
        "lang": "en",
        "expected_tool": "intercrop_planner",
        "expected_args": {"area_m2": 500, "crops": ["maize", "beans"]},
    },
    {
        "name": "intercrop_cassava_cowpea",
        "request": "Planning to intercrop cassava and cowpea on a 300 square meter plot, what layout do you suggest?",
        "lang": "en",
        "expected_tool": "intercrop_planner",
        "expected_args": {"area_m2": 300, "crops": ["cassava", "cowpea"]},
    },
    {
        "name": "urea_allocation_maize_beans",
        "request": "I have 50kg of urea for 1000 square meters of maize and beans intercrop. How should I split it?",
        "lang": "en",
        "expected_tool": "input_allocator",
        "expected_args": {"area_m2": 1000, "crops": ["maize", "beans"], "urea_kg": 50},
    },
    {
        "name": "urea_allocation_cassava_cowpea",
        "request": "80kg of urea across 2000 square meters of cassava and cowpea, what allocation should I use?",
        "lang": "en",
        "expected_tool": "input_allocator",
        "expected_args": {"area_m2": 2000, "crops": ["cassava", "cowpea"], "urea_kg": 80},
    },
    {
        "name": "planting_window_east_africa_long_rains",
        "request": "When should I plant for the long rains in East Africa?",
        "lang": "en",
        "expected_tool": "planting_scheduler",
        "expected_args": {"region": "east_africa", "season": "long_rains"},
    },
    {
        "name": "planting_window_sahel_long_rains_ff",
        "request": "Ana ndi ma acci gese e ndungu ngoowaari e Sahel?",
        "lang": "ff",
        "expected_tool": "planting_scheduler",
        "expected_args": {"region": "sahel", "season": "long_rains"},
    },
]


def ground_truth(scenario: dict) -> dict:
    """Compute the correct answer for a scenario by calling the deterministic
    tool directly, bypassing the model entirely."""
    return dispatch(scenario["expected_tool"], scenario["expected_args"])
