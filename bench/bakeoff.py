"""Model bake-off for Gesa Mo Volata.

Runs the fixed grammar-guarded, tool-calling + multilingual scenario suite
(`bench.scenarios.SCENARIOS`) against each candidate GGUF model and reports
tokens/sec, peak RSS, tool-call accuracy, and the local `s_estimate` proxy
(see `bench.harness` for what that formula does and does not measure), so a
model can be picked for the constrained laptop.

This module intentionally does NOT import `llama_cpp` (or `gesa.model`) at
module level, so it can be imported with no native dependencies or GGUF
files present. The real model is constructed lazily inside `run_bakeoff`,
only for paths that actually exist on disk.

The live bake-off run itself is deferred until candidate GGUF files are
downloaded into `models/` (gitignored) -- see the task brief / README.
"""
import os

from bench.harness import measure_run
from bench.scenarios import SCENARIOS

# Intended bake-off candidates (filenames relative to `models/`). These are
# the models we intend to compare; not all of them may be downloaded yet on
# any given machine -- `run_bakeoff` skips whichever are missing.
CANDIDATES: list[str] = [
    "qwen2.5-3b-instruct-q4_k_m.gguf",
    "qwen2.5-1.5b-instruct-q4_k_m.gguf",
    "gemma-2-2b-it-Q4_K_M.gguf",
]


def run_bakeoff(model_paths: list[str]) -> list[dict]:
    """Measure every candidate model that exists on disk.

    For each path in `model_paths` that exists, builds a `LlamaModel`,
    runs `bench.harness.measure_run` against `SCENARIOS`, and collects a
    result dict. Paths that do not exist are skipped with a printed note
    (no crash) -- this lets the bake-off run partially before all
    candidate GGUFs have been downloaded.
    """
    # Imported lazily so this module (and its tests) never require llama_cpp.
    from gesa.model import LlamaModel

    results = []
    for path in model_paths:
        if not os.path.exists(path):
            print(f"skipping {path}: file not found")
            continue

        model = LlamaModel(path)
        report = measure_run(model, SCENARIOS)
        results.append({
            "model": os.path.basename(path),
            "accuracy": report["accuracy"],
            "tokens_per_sec": report["tokens_per_sec"],
            "peak_rss_mb": report["peak_rss_mb"],
            "s_estimate": report["s_estimate"],
        })
    return results


def _print_table(results: list[dict]) -> None:
    header = f"{'model':<40} {'accuracy':>10} {'tok/s':>10} {'peak RSS MB':>12} {'S estimate':>11}"
    print(header)
    print("-" * len(header))
    for r in results:
        tps = f"{r['tokens_per_sec']:.2f}" if r["tokens_per_sec"] is not None else "n/a"
        print(
            f"{r['model']:<40} {r['accuracy']:>10.2%} {tps:>10} "
            f"{r['peak_rss_mb']:>12.1f} {r['s_estimate']:>11.4f}"
        )


def main():
    models_dir = os.path.join(os.getcwd(), "models")
    candidate_paths = [os.path.join(models_dir, name) for name in CANDIDATES]

    existing = [p for p in candidate_paths if os.path.exists(p)]
    if not existing:
        print("No candidate GGUF models found in 'models/'.")
        print("Download one or more of the following into models/ before running the bake-off:")
        for name in CANDIDATES:
            print(f"  - {name}")
        return

    results = run_bakeoff(candidate_paths)
    if not results:
        print("No models could be measured.")
        return

    results.sort(key=lambda r: r["s_estimate"], reverse=True)

    print("=== Gesa Mo Volata model bake-off (S sub-scores are ESTIMATES) ===")
    _print_table(results)
    winner = results[0]
    print(f"\nWinner: {winner['model']} (S estimate = {winner['s_estimate']:.4f})")


if __name__ == "__main__":
    main()
