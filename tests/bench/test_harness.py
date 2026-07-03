import json

import bench.harness as harness
from bench.scenarios import SCENARIOS


class ScriptedToolModel:
    """Fake model that plays back a scripted sequence of tool-call JSON strings."""

    def __init__(self, scripted):
        self.scripted = list(scripted)
        self.i = 0

    def complete(self, prompt, grammar=None, max_tokens=256):
        out = self.scripted[self.i]
        self.i += 1
        return out


class AlwaysFinalModel:
    """Fake model that answers immediately without ever calling a tool."""

    def complete(self, prompt, grammar=None, max_tokens=256):
        return json.dumps({"tool": "final", "args": {"answer": "ok"}})


def _scripted_for(scenario):
    return [
        json.dumps({"tool": scenario["expected_tool"], "args": scenario["expected_args"]}),
        json.dumps({"tool": "final", "args": {"answer": "ok"}}),
    ]


def test_score_accuracy_is_1_when_expected_tool_called_correctly():
    scenario = SCENARIOS[0]
    model = ScriptedToolModel(_scripted_for(scenario))
    assert harness.score_accuracy(model, [scenario]) == 1.0


def test_score_accuracy_is_0_when_model_never_calls_the_tool():
    scenario = SCENARIOS[0]
    model = AlwaysFinalModel()
    assert harness.score_accuracy(model, [scenario]) == 0.0


def test_measure_run_returns_all_keys_and_positive_rss():
    scenario = SCENARIOS[0]
    model = ScriptedToolModel(_scripted_for(scenario))
    report = harness.measure_run(model, [scenario])
    assert set(report) == {"accuracy", "tokens_per_sec", "peak_rss_mb", "max_temp_c", "s_estimate"}
    assert report["peak_rss_mb"] > 0
    assert report["accuracy"] == 1.0
