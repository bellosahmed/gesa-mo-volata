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

class RecordingModel:
    """Fake model that records the prompt of each call and returns scripted output."""
    def __init__(self, scripted):
        self.scripted = list(scripted); self.i = 0; self.prompts = []
    def complete(self, prompt, grammar=None, max_tokens=256):
        self.prompts.append(prompt)
        out = self.scripted[self.i]; self.i += 1; return out

def test_answer_language_in_prompt_ff():
    import json
    scripted = [json.dumps({"tool": "final", "args": {"answer": "done"}})]
    m = RecordingModel(scripted)
    run("hello", m, lang="ff")
    assert "Fulfulde" in m.prompts[0]

def test_answer_language_defaults_to_english():
    import json
    scripted = [json.dumps({"tool": "final", "args": {"answer": "done"}})]
    m = RecordingModel(scripted)
    run("hello", m)  # no lang -> en
    assert "English" in m.prompts[0]

def test_system_prompt_lists_all_registered_tools():
    import json
    from gesa.tools.registry import TOOLS
    scripted = [json.dumps({"tool": "final", "args": {"answer": "done"}})]
    m = RecordingModel(scripted)
    run("hello", m)
    for name in TOOLS:
        assert name in m.prompts[0]
