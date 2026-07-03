from gesa.tools.intercrop import intercrop_planner
from gesa.tools.inputs import input_allocator
from gesa.tools.scheduler import planting_scheduler

TOOLS = {
    "intercrop_planner": {"fn": intercrop_planner, "args": ["area_m2", "crops", "area_value", "area_unit"]},
    "input_allocator":   {"fn": input_allocator, "args": ["area_m2", "crops", "urea_kg", "area_value", "area_unit"]},
    "planting_scheduler":{"fn": planting_scheduler, "args": ["region", "season"]},
}

def dispatch(name: str, args: dict) -> dict:
    if name not in TOOLS:
        raise ValueError(f"unknown tool: {name!r}")
    allowed = set(TOOLS[name]["args"])
    extra = set(args) - allowed
    if extra:
        raise ValueError(f"unexpected args for {name}: {extra}")
    return TOOLS[name]["fn"](**args)
