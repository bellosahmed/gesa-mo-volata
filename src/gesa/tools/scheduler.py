import json, os
from datetime import date, timedelta

DEFAULT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "rainfall", "onset.json")

def planting_scheduler(region: str, season: str, data_path: str = DEFAULT) -> dict:
    with open(os.path.abspath(data_path)) as fh:
        data = json.load(fh)
    entry = data[region][season]  # KeyError if unknown
    onset = date.fromisoformat(entry["onset_week"])
    std = entry["std_days"]
    offsets = [(-std, "early (risk hedge)", 30), (0, "main planting", 50), (std, "late (safety)", 20)]
    windows = [{"label": lbl, "start": (onset + timedelta(days=d)).isoformat(), "share_pct": pct}
               for d, lbl, pct in offsets]
    return {"region": region, "season": season, "onset_week": entry["onset_week"], "windows": windows}
