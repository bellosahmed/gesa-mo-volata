import pytest
from gesa.tools.inputs import input_allocator

def test_sufficient_allocation_maize_beans():
    # 0.2 ha maize+beans. maize need 60*0.2=12kg N minus 30*0.2=6 credit =6kg; beans 20*0.2=4kg
    r = input_allocator(2000, ["maize", "beans"], urea_kg=25)
    assert r["required_n_kg"] == pytest.approx(10.0, rel=1e-3)
    assert r["urea_available_n_kg"] == pytest.approx(11.5, rel=1e-3)  # 25*0.46
    assert r["sufficient"] is True

def test_insufficient_flagged():
    r = input_allocator(4046.86, ["maize"], urea_kg=1)
    assert r["sufficient"] is False

def test_allocation_is_proportional():
    # 0.2 ha maize+beans. maize need 60*0.2=12 minus 30*0.2=6 credit = 6kg; beans 20*0.2=4kg
    # total need 10kg; maize gets 6/10*25=15.0, beans gets 4/10*25=10.0
    r = input_allocator(2000, ["maize", "beans"], urea_kg=25)
    assert r["allocation"] == {"maize": 15.0, "beans": 10.0}

def test_zero_area_no_division_error():
    # Zero area should not cause division-by-zero; all needs are 0, allocation is 0
    r = input_allocator(0, ["maize"], urea_kg=5)
    assert r["required_n_kg"] == 0.0
    assert r["allocation"]["maize"] == 0.0
    assert r["sufficient"] is True

def test_unknown_crop_raises():
    # Attempting to use an unknown crop should raise ValueError
    with pytest.raises(ValueError, match="unknown crop"):
        input_allocator(1000, ["mango"], urea_kg=5)

def test_empty_crops_raises():
    with pytest.raises(ValueError, match="crops must not be empty"):
        input_allocator(1000, [], urea_kg=5)

def test_duplicate_crops_raises():
    with pytest.raises(ValueError, match="duplicate crops"):
        input_allocator(1000, ["maize", "maize"], urea_kg=5)

def test_inputs_accepts_value_unit():
    r = input_allocator(crops=["maize", "beans"], urea_kg=25, area_value=0.2, area_unit="hectare")
    expected = input_allocator(2000, ["maize", "beans"], urea_kg=25)
    assert r["required_n_kg"] == expected["required_n_kg"]
