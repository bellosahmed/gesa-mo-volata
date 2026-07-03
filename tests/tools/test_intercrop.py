import pytest
from gesa.tools.intercrop import intercrop_planner

def test_maize_beans_layout_on_half_acre():
    r = intercrop_planner(2023.43, ["maize", "beans"])
    assert r["compatible"] is True
    # maize share 1011.7 m2 / (0.75*0.25=0.1875) -> 5395 plants
    assert r["layout"]["maize"]["plants"] == 5395
    assert r["layout"]["beans"]["plants"] == 22482  # /(0.45*0.10=0.045)

def test_incompatible_pair_flagged():
    r = intercrop_planner(1000, ["maize", "cassava"])
    assert r["compatible"] is False

def test_unknown_crop_raises():
    with pytest.raises(ValueError):
        intercrop_planner(1000, ["maize", "quinoa"])

def test_single_crop_is_compatible():
    r = intercrop_planner(1000, ["maize"])
    assert r["compatible"] is True

def test_empty_crops_raises():
    with pytest.raises(ValueError):
        intercrop_planner(1000, [])

def test_duplicate_crops_raises():
    with pytest.raises(ValueError):
        intercrop_planner(1000, ["maize", "maize"])
