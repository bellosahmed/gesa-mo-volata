import pytest
from gesa.units import normalize_area

def test_acre_to_m2():
    assert normalize_area(1, "acre") == pytest.approx(4046.86, rel=1e-4)

def test_half_acre():
    assert normalize_area(0.5, "acre") == pytest.approx(2023.43, rel=1e-4)

def test_local_plot_unit():
    assert normalize_area(2, "plot") == 450.0

def test_unknown_unit_raises():
    with pytest.raises(ValueError):
        normalize_area(1, "furlong")
