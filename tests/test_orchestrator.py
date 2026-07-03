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
    assert len(r["steps"]) == 2

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

def test_system_prompt_includes_arg_names():
    import json
    scripted = [json.dumps({"tool": "final", "args": {"answer": "done"}})]
    m = RecordingModel(scripted)
    run("hello", m)
    assert "area_m2" in m.prompts[0]
    assert "region" in m.prompts[0]

def test_malformed_json_does_not_crash():
    scripted = [
        "not json",
        json.dumps({"tool": "final", "args": {"answer": "recovered"}}),
    ]
    r = run("x", FakeModel(scripted))
    assert r["steps"] == []
    assert r["answer"] == "recovered"

def test_unknown_crop_recovers():
    scripted = [
        json.dumps({"tool": "intercrop_planner", "args": {"area_m2": 1000, "crops": ["mango"]}}),
        json.dumps({"tool": "final", "args": {"answer": "recovered"}}),
    ]
    r = run("x", FakeModel(scripted))
    assert r["steps"] == []
    assert r["answer"] == "recovered"

def test_missing_arg_recovers():
    scripted = [
        json.dumps({"tool": "intercrop_planner", "args": {"area_m2": 1000}}),
        json.dumps({"tool": "final", "args": {"answer": "recovered"}}),
    ]
    r = run("x", FakeModel(scripted))
    assert r["steps"] == []
    assert r["answer"] == "recovered"

def test_advisory_planting_windows_appended():
    scripted = [
        json.dumps({"tool": "planting_scheduler", "args": {"region": "east_africa", "season": "long_rains"}}),
        json.dumps({"tool": "final", "args": {"answer": "ok"}}),
    ]
    r = run("when do I plant?", FakeModel(scripted))
    assert "3 staggered windows" in r["answer"]

def test_advisory_insufficient_urea_appended():
    scripted = [
        json.dumps({"tool": "input_allocator", "args": {"area_m2": 4046.86, "crops": ["maize"], "urea_kg": 1}}),
        json.dumps({"tool": "final", "args": {"answer": "ok"}}),
    ]
    r = run("how much urea?", FakeModel(scripted))
    assert "You need more urea for this plan." in r["answer"]

def test_no_advisory_when_not_applicable():
    scripted = [
        json.dumps({"tool": "intercrop_planner", "args": {"area_m2": 1000, "crops": ["maize", "beans"]}}),
        json.dumps({"tool": "final", "args": {"answer": "ok"}}),
    ]
    r = run("intercrop plan", FakeModel(scripted))
    assert r["answer"] == "ok"

def test_system_prompt_lists_scheduler_regions_and_example():
    scripted = [json.dumps({"tool": "final", "args": {"answer": "done"}})]
    m = RecordingModel(scripted)
    run("hello", m)
    assert "east_africa" in m.prompts[0]
    assert "long_rains" in m.prompts[0]
    assert "Example" in m.prompts[0]
