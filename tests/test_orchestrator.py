import json
from gesa.orchestrator import run

class FakeModel:
    def __init__(self, scripted): self.scripted = list(scripted); self.i = 0
    def complete(self, prompt, grammar=None, max_tokens=256):
        out = self.scripted[self.i]; self.i += 1; return out

def test_single_tool_then_final():
    scripted = [
        json.dumps({"tool": "planting_scheduler", "args": {"region": "east_africa", "season": "long_rains"}}),
        json.dumps({"tool": "final", "args": {"answer": "Plant in three windows around March 10."}}),
    ]
    r = run("when do I plant?", FakeModel(scripted))
    assert r["steps"][0]["tool"] == "planting_scheduler"
    assert r["steps"][0]["result"]["onset_week"] == "2026-03-10"
    assert "three windows" in r["answer"]

def test_step_cap_enforced():
    loop = json.dumps({"tool": "planting_scheduler", "args": {"region": "east_africa", "season": "long_rains"}})
    r = run("x", FakeModel([loop] * 10), max_steps=2)
    assert len(r["steps"]) <= 2
