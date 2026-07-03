_TO_M2 = {"m2": 1.0, "acre": 4046.86, "hectare": 10000.0, "plot": 225.0}

def normalize_area(value: float, unit: str) -> float:
    key = unit.strip().lower()
    if key not in _TO_M2:
        raise ValueError(f"unknown area unit: {unit!r}")
    return value * _TO_M2[key]
