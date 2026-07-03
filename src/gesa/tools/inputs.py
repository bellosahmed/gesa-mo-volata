from gesa.agronomy import SPACING, LEGUME_N_CREDIT_KG_HA

UREA_N_FRACTION = 0.46

def input_allocator(area_m2: float, crops: list[str], urea_kg: float) -> dict:
    """Allocate available urea across crops in proportion to nitrogen need.

    Applies legume N-credit to intercropped non-legumes and flags whether the available nitrogen is sufficient.
    """
    for c in crops:
        if c not in SPACING:
            raise ValueError(f"unknown crop: {c!r}")
    ha = area_m2 / 10000.0
    has_legume = any(SPACING[c]["legume"] for c in crops)
    needs = {}
    for c in crops:
        need = SPACING[c]["n_need_kg_ha"] * ha
        if not SPACING[c]["legume"] and has_legume:
            need = max(0.0, need - LEGUME_N_CREDIT_KG_HA * ha)
        needs[c] = need
    required = sum(needs.values())
    available_n = urea_kg * UREA_N_FRACTION
    # Avoid division-by-zero when total need is 0 (e.g., zero area); in that case every allocation is 0.
    total_need = required or 1.0
    allocation = {c: round((needs[c] / total_need) * urea_kg, 2) for c in crops}
    return {"required_n_kg": required, "urea_available_n_kg": available_n,
            "sufficient": available_n >= required, "allocation": allocation}
