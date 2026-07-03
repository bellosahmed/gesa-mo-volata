# src/gesa/agronomy.py
# Sources: national extension spacing guides (maize/beans/cowpea/cassava).
SPACING = {
    "maize":   {"row_cm": 75, "plant_cm": 25, "legume": False, "n_need_kg_ha": 60.0},
    "beans":   {"row_cm": 45, "plant_cm": 10, "legume": True,  "n_need_kg_ha": 20.0},
    "cowpea":  {"row_cm": 60, "plant_cm": 20, "legume": True,  "n_need_kg_ha": 15.0},
    "cassava": {"row_cm": 100, "plant_cm": 100, "legume": False, "n_need_kg_ha": 40.0},
}
COMPANION = {
    frozenset({"maize", "beans"}),
    frozenset({"maize", "cowpea"}),
    frozenset({"cassava", "cowpea"}),
}
LEGUME_N_CREDIT_KG_HA = 30.0
