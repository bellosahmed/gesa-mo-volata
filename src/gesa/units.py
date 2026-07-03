_TO_M2 = {"m2": 1.0, "acre": 4046.86, "hectare": 10000.0, "plot": 225.0}

def normalize_area(value: float, unit: str) -> float:
    key = unit.strip().lower()
    if key not in _TO_M2:
        raise ValueError(f"unknown area unit: {unit!r}")
    return value * _TO_M2[key]

def resolve_area_m2(area_m2=None, area_value=None, area_unit=None) -> float:
    """Resolve a plot area to m². Prefers (area_value + area_unit) via normalize_area;
    falls back to a directly-supplied area_m2. Raises ValueError if neither is given."""
    if area_value is not None and area_unit is not None:
        return normalize_area(float(area_value), area_unit)
    if area_m2 is not None:
        return float(area_m2)
    raise ValueError("provide area_m2, or area_value with area_unit")
