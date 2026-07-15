# Gesa Mo Volata 🌱

**An offline agriculture planning agent for African smallholder farmers.**
Submission to the [Africa Deep Tech Challenge 2026](https://africadeeptech.org/challenge-2026/) — Laptop LLM track, `agriculture` domain.

A small quantized language model (Qwen2.5-1.5B-Instruct, GGUF Q4_K_M via llama.cpp) interprets a farmer's request in natural language; **deterministic Python tools compute all the agronomy** — intercrop spacing and plant counts, fertilizer allocation with legume nitrogen credits, and rain-staggered planting windows from bundled offline rainfall data. The answer comes back in the farmer's language. Entirely offline, CPU-only, far under the 8 GB laptop profile.

**Thesis: think in language, calculate in code.** A 1–3B model on a CPU cannot be trusted with arithmetic, so it is trusted only with intent and phrasing; every number a farmer relies on comes from auditable deterministic code.

📄 Full technical writeup: [REPORT.md](REPORT.md) · Architecture diagram: `docs/superpowers/specs/architecture.html`

---

## Quick start

Requires Python 3.10+ on Linux/macOS (target profile: Ubuntu 22.04, 4 vCPU, 8 GB RAM, no GPU).

```bash
# 1. Set up the environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Download the model weights (~1.1 GB, public URL, idempotent)
bash download_model.sh

# 3. Run the offline web UI
GESA_MODEL=model/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  .venv/bin/uvicorn gesa.ui.app:app --app-dir src --port 8000
```

Open http://localhost:8000 — a fully self-contained page (no CDN, no external fonts, zero network calls) — and ask, for example:

> *I have half an acre and want to plant maize and beans together. How many plants of each can I fit?*

## Run the tests

```bash
.venv/bin/python -m pytest          # 44+ tests, no model download needed
```

## Run the benchmark (RAM-capped emulation)

```bash
# Runs the 6-scenario suite under a hard 7 GB cap (systemd-run, no swap)
PYTHONPATH=src:. GESA_MODEL=model/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  bash bench/emulate.sh .venv/bin/python bench/harness.py

# Compare candidate models present in model/
PYTHONPATH=src:. bash bench/emulate.sh .venv/bin/python bench/bakeoff.py

# Official ADTC profiler smoke test (needs llama-bench from llama.cpp on PATH)
.venv/bin/pip install "git+https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler.git"
bash download_model.sh
.venv/bin/adtc-profiler run --submission . --mode participant --output submission.json --skip-accuracy
```

## How it works

```
Farmer request
   → llama.cpp (Qwen2.5-1.5B Q4_K_M, CPU-only)
   → capped ReAct agent loop (hard step limit → bounded RAM & latency)
   → GBNF grammar guard (the model *cannot* emit a malformed tool call)
   → deterministic tools:
        intercrop_planner   · spacing, rows, plant counts, companion checks
        input_allocator     · urea split by remaining N need, legume N credit
        planting_scheduler  · 3 risk-staggered windows from offline rainfall data
   → localised answer (English / Fulfulde) → offline UI
```

| Path | What it is |
|---|---|
| `src/gesa/tools/` | The deterministic agronomy tools (the accuracy core) |
| `src/gesa/agronomy.py` | All agronomy constants in one auditable file |
| `src/gesa/grammar.py` | GBNF grammar that forces valid JSON tool calls |
| `src/gesa/orchestrator.py` | Capped ReAct loop with error containment |
| `src/gesa/locale/` | Pluggable localisation (en, ff) |
| `src/gesa/ui/` | FastAPI + self-contained offline HTML UI |
| `data/rainfall/onset.json` | Bundled historical rain-onset data (no weather API) |
| `bench/` | Benchmark harness, 7 GB emulation wrapper, model bake-off |
| `metadata.json`, `download_model.sh` | ADTC 2026 submission files |

## Challenge compliance

- **Offline:** zero network calls in the request path; rainfall data is bundled.
- **llama.cpp + GGUF only**, open base model (Qwen2.5), CPU-only (`n_gpu_layers=0`).
- **RAM:** 1.95 GB peak measured under a 7 GB `systemd-run` cap — see REPORT.md §6.
- **African language (+15%):** answers composed in Fulfulde via the locale layer *(strings pending native-speaker verification)*.
- **Budget profile (+10%):** planning around scarce, locally-available inputs is the core product.

## License

[MIT](LICENSE)
