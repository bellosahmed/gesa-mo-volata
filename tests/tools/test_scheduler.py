import pytest
from gesa.tools.scheduler import planting_scheduler, available_regions_seasons

def test_available_regions_seasons():
    r = available_regions_seasons()
    assert "long_rains" in r["east_africa"]
    assert "sahel" in r

def test_three_staggered_windows():
    r = planting_scheduler("east_africa", "long_rains")
    assert r["onset_week"] == "2026-03-10"
    assert len(r["windows"]) == 3
    assert sum(w["share_pct"] for w in r["windows"]) == 100

def test_unknown_region_raises():
    with pytest.raises(KeyError):
        planting_scheduler("atlantis", "long_rains")

def test_unknown_season_raises():
    with pytest.raises(KeyError):
        planting_scheduler("east_africa", "monsoon")
