import math
from itertools import combinations
from gesa.agronomy import SPACING, COMPANION

def intercrop_planner(area_m2: float, crops: list[str]) -> dict:
    """Plan intercropping layout with per-crop rows and plant counts.

    Returns dict with area_m2, compatibility flag, and per-crop layout (rows/plants/spacing).
    """
    for c in crops:
        if c not in SPACING:
            raise ValueError(f"unknown crop: {c!r}")
    if not crops:
        raise ValueError("crops must not be empty")
    if len(crops) != len(set(crops)):
        raise ValueError(f"duplicate crops: {crops}")
    compatible = all(frozenset(p) in COMPANION for p in combinations(crops, 2)) if len(crops) > 1 else True
    share = area_m2 / len(crops)
    layout = {}
    for c in crops:
        s = SPACING[c]
        cell_m2 = (s["row_cm"] / 100) * (s["plant_cm"] / 100)
        plants = math.floor(share / cell_m2)
        rows = math.floor((share ** 0.5) / (s["row_cm"] / 100))
        layout[c] = {"rows": rows, "plants": plants,
                     "row_cm": s["row_cm"], "plant_cm": s["plant_cm"]}
    return {"area_m2": area_m2, "compatible": compatible, "layout": layout}
