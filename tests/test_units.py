import pytest
from gesa.units import normalize_area, resolve_area_m2

def test_acre_to_m2():
    assert normalize_area(1, "acre") == pytest.approx(4046.86, rel=1e-4)

def test_half_acre():
    assert normalize_area(0.5, "acre") == pytest.approx(2023.43, rel=1e-4)

def test_local_plot_unit():
    assert normalize_area(2, "plot") == 450.0

def test_unknown_unit_raises():
    with pytest.raises(ValueError):
        normalize_area(1, "furlong")

def test_resolve_from_value_unit():
    assert resolve_area_m2(area_value=0.5, area_unit="acre") == pytest.approx(2023.43, rel=1e-4)

def test_resolve_from_area_m2():
    assert resolve_area_m2(area_m2=1000) == 1000.0

def test_resolve_requires_something():
    with pytest.raises(ValueError):
        resolve_area_m2()
