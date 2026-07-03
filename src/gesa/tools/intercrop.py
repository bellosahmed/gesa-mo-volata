import math
from itertools import combinations
from gesa.agronomy import SPACING, COMPANION

def intercrop_planner(area_m2: float, crops: list[str]) -> dict:
    for c in crops:
        if c not in SPACING:
            raise ValueError(f"unknown crop: {c!r}")
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
