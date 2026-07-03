import functools
import json, os
from datetime import date, timedelta

_MODULE_DIR = os.path.dirname(__file__)
DEFAULT = os.path.join(_MODULE_DIR, "..", "..", "..", "data", "rainfall", "onset.json")

def _resolve_path(data_path: str) -> str:
    """Resolve a potentially relative data_path to an absolute path."""
    return data_path if os.path.isabs(data_path) else os.path.join(_MODULE_DIR, data_path)

def planting_scheduler(region: str, season: str, data_path: str = DEFAULT) -> dict:
    resolved = _resolve_path(data_path)
    with open(resolved) as fh:
        data = json.load(fh)
    entry = data[region][season]  # KeyError if unknown
    onset = date.fromisoformat(entry["onset_week"])
    std = entry["std_days"]
    offsets = [(-std, "early (risk hedge)", 30), (0, "main planting", 50), (std, "late (safety)", 20)]
    windows = [{"label": lbl, "start": (onset + timedelta(days=d)).isoformat(), "share_pct": pct}
               for d, lbl, pct in offsets]
    return {"region": region, "season": season, "onset_week": entry["onset_week"], "windows": windows}

@functools.lru_cache(maxsize=None)
def available_regions_seasons(data_path: str = DEFAULT) -> dict:
    """Return {region: [seasons]} from the bundled rainfall data."""
    resolved = _resolve_path(data_path)
    with open(resolved) as fh:
        data = json.load(fh)
    return {region: list(seasons) for region, seasons in data.items()}
