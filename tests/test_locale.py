from gesa.locale import t

def test_english_lookup():
    assert t("plant_windows", lang="en", n=3) == "Plant in 3 staggered windows."

def test_fulfulde_lookup():
    assert t("plant_windows", lang="ff", n=3) != t("plant_windows", lang="en", n=3)

def test_missing_key_falls_back_to_key():
    assert t("nonexistent", lang="en") == "nonexistent"
