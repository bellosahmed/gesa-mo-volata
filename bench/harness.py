"""Benchmark harness for Gesa Mo Volata, run under 7 GB RAM emulation
(see bench/emulate.sh).

This module scores an agent run against the competition formula::

    S = 0.50*Accuracy + 0.30*Speed + 0.20*Efficiency - ThermalPenalty

IMPORTANT: every sub-score below other than Accuracy is a local ESTIMATE for
development-time feedback, not the official scoring formula used by the
competition. The proxies are:

  - Accuracy: fraction of scenarios where the orchestrator's tool call
    matches ground truth exactly (see `score_accuracy`). This part is real,
    not a proxy: it reuses the deterministic tools as an oracle.
  - Speed sub-score: min(1.0, tokens_per_sec / 20). tokens_per_sec itself is
    approximated as ~4 characters per generated token (a common rough
    heuristic for English text), divided by wall-clock seconds spent in
    `model.complete`. There is no real token count available through the
    `ModelClient` protocol, so this is only a rough proxy for throughput.
  - Efficiency sub-score: max(0, 1 - peak_rss_mb / 7000), i.e. how much of
    the 7 GB memory budget was left unused at peak.
  - Thermal penalty: a flat 0.1 if the maximum observed core temperature is
    >= 85 C, else 0. Temperature is read best-effort via the `sensors`
    command (lm-sensors) and is `None` when unavailable (e.g. this dev
    container), in which case no thermal penalty is applied.

This module intentionally does NOT import llama_cpp at module level, so it
can be imported and unit-tested with a fake `ModelClient` with no model or
native dependencies installed. `main()` imports the real model lazily.
"""
import json
import os
import resource
import shutil
import subprocess
import time

from gesa import orchestrator
from bench.scenarios import SCENARIOS, ground_truth

CHARS_PER_TOKEN_ESTIMATE = 4.0
SPEED_TARGET_TOKENS_PER_SEC = 20.0
EFFICIENCY_BUDGET_MB = 7000.0
THERMAL_LIMIT_C = 85.0
THERMAL_PENALTY = 0.1


class _TokenCountingModel:
    """Wraps a ModelClient to approximate total generated tokens.

    The ModelClient protocol only returns text, not a token count, so we
    approximate using ~4 characters per token (see module docstring).
    """

    def __init__(self, inner):
        self._inner = inner
        self.total_chars = 0
        self.calls = 0

    def complete(self, prompt, grammar=None, max_tokens=256):
        text = self._inner.complete(prompt, grammar=grammar, max_tokens=max_tokens)
        self.total_chars += len(text)
        self.calls += 1
        return text


def score_accuracy(model, scenarios) -> float:
    """Fraction (0..1) of scenarios where the orchestrator's run executed the
    scenario's expected tool and got a result matching ground truth exactly.

    Ground truth comes from `bench.scenarios.ground_truth`, which calls the
    real deterministic tool directly -- never a hand-written expected value.
    """
    if not scenarios:
        return 0.0
    correct = 0
    for scenario in scenarios:
        result = orchestrator.run(scenario["request"], model, lang=scenario.get("lang", "en"))
        expected = ground_truth(scenario)
        hit = any(
            step["tool"] == scenario["expected_tool"] and step["result"] == expected
            for step in result["steps"]
        )
        if hit:
            correct += 1
    return correct / len(scenarios)


def _read_max_temp_c():
    """Best-effort max CPU core temperature via `sensors -j` (lm-sensors).

    Returns None (never raises) if `sensors` is not installed, fails, or its
    output can't be parsed -- callers must treat None as "unknown", not 0.
    """
    if shutil.which("sensors") is None:
        return None
    try:
        proc = subprocess.run(
            ["sensors", "-j"], capture_output=True, text=True, timeout=5, check=True
        )
        data = json.loads(proc.stdout)
    except Exception:
        return None

    temps = []

    def _walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key.endswith("_input") and isinstance(value, (int, float)):
                    temps.append(float(value))
                else:
                    _walk(value)

    _walk(data)
    return max(temps) if temps else None


def measure_run(model, scenarios) -> dict:
    """Run the full scenario suite once and report accuracy, throughput,
    peak memory, thermal, and an S-formula estimate. See module docstring
    for what is exact vs. an estimate."""
    wrapped = _TokenCountingModel(model)

    start = time.perf_counter()
    accuracy = score_accuracy(wrapped, scenarios)
    elapsed_s = time.perf_counter() - start

    approx_tokens = wrapped.total_chars / CHARS_PER_TOKEN_ESTIMATE
    tokens_per_sec = (approx_tokens / elapsed_s) if elapsed_s > 0 else None

    peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0  # KiB -> MB (Linux)

    max_temp_c = _read_max_temp_c()

    speed_score = min(1.0, tokens_per_sec / SPEED_TARGET_TOKENS_PER_SEC) if tokens_per_sec is not None else 0.0
    efficiency_score = max(0.0, 1.0 - peak_rss_mb / EFFICIENCY_BUDGET_MB)
    thermal_penalty = THERMAL_PENALTY if (max_temp_c is not None and max_temp_c >= THERMAL_LIMIT_C) else 0.0

    s_estimate = 0.50 * accuracy + 0.30 * speed_score + 0.20 * efficiency_score - thermal_penalty

    return {
        "accuracy": accuracy,
        "tokens_per_sec": tokens_per_sec,
        "peak_rss_mb": peak_rss_mb,
        "max_temp_c": max_temp_c,
        "s_estimate": s_estimate,
    }


def main():
    # Imported lazily so this module (and its tests) never require llama_cpp.
    from gesa.model import LlamaModel

    model_path = os.environ["GESA_MODEL"]
    model = LlamaModel(model_path)

    report = measure_run(model, SCENARIOS)

    print("=== Gesa Mo Volata benchmark report (S sub-scores are ESTIMATES) ===")
    print(f"accuracy       : {report['accuracy']:.2%}")
    tps = report["tokens_per_sec"]
    print(f"tokens/sec (~) : {tps:.2f}" if tps is not None else "tokens/sec (~) : n/a")
    print(f"peak RSS (MB)  : {report['peak_rss_mb']:.1f}")
    temp = report["max_temp_c"]
    print(f"max temp (C)   : {temp:.1f}" if temp is not None else "max temp (C)   : n/a (sensors unavailable)")
    print(f"S estimate     : {report['s_estimate']:.4f}")

    assert report["peak_rss_mb"] < EFFICIENCY_BUDGET_MB, (
        f"peak RSS {report['peak_rss_mb']:.1f} MB exceeded the {EFFICIENCY_BUDGET_MB:.0f} MB budget"
    )
    if temp is not None and temp >= THERMAL_LIMIT_C:
        print(f"WARNING: max core temperature {temp:.1f}C >= {THERMAL_LIMIT_C:.0f}C -- thermal throttling risk")


if __name__ == "__main__":
    main()
