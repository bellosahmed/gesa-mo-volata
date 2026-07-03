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
