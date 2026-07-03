import pytest
from gesa.tools.scheduler import planting_scheduler

def test_three_staggered_windows():
    r = planting_scheduler("east_africa", "long_rains")
    assert r["onset_week"] == "2026-03-10"
    assert len(r["windows"]) == 3
    assert sum(w["share_pct"] for w in r["windows"]) == 100

def test_unknown_region_raises():
    with pytest.raises(KeyError):
        planting_scheduler("atlantis", "long_rains")
