# Gesa Mo Volata — ADTC 2026 Report

**Track:** Agriculture · **Challenge:** Africa Deep Tech Challenge 2026 (The Laptop LLM Challenge)

An offline whole-plot planning agent for African smallholder farmers. A small quantized
language model interprets a farmer's request; deterministic Python tools compute all the
agronomy; the answer comes back in the farmer's language — entirely offline, CPU-only, on a
low-cost laptop.

---

## 1. The problem, and why offline is the point

Smallholder farming across Africa is structurally different from the monoculture, data-rich,
connected agriculture that generic AgTech assumes: fields are **intercropped** (maize + beans +
cassava together), there is **no soil test** and only whatever inputs the local market stocks,
planting is **rain-fed** around an uncertain onset, and the goal is household **food security and
cash flow**, not maximum yield. And rural farmers frequently have **no connectivity**.

So an on-device advisor is not a contest constraint we tolerate — it is the actual product need.
Every design decision follows from that.

## 2. Thesis: think in language, calculate in code

A 1–3B model on a CPU is unreliable at arithmetic. So the model is trusted only with what small
models are good at — understanding intent and phrasing answers — and **every number a farmer relies
on is produced by deterministic code**, not model guesswork. This is what protects the 50% accuracy
weight in the scoring formula.

```
S = 0.50·Accuracy + 0.30·Speed + 0.20·Efficiency − Thermal   (+15% local language, +10% budget)
```

| Rubric element | How the design earns it |
|---|---|
| Accuracy (50%) | Deterministic tools own all math → verifiable, can't be "wrong" |
| Speed (30%) | Small Q4 model, capped agent loop, short contexts |
| Efficiency (20%) | Fixed context window + hard step cap → bounded RAM, verified under 7 GB emulation |
| +15% local language | Pluggable locale layer; answers composed in the target language (Fulfulde) |
| +10% budget profile | Planning around scarce, affordable, locally-available inputs is the product |
| Best Integration | Multi-tool agent: intercrop + inputs + rainfall orchestrated in one loop |

## 3. Architecture

See `docs/superpowers/specs/architecture.html` for the diagram. Request flow, all inside the 7 GB
boundary, all offline:

```
Farmer request → llama.cpp (small GGUF) → capped ReAct loop
    → GBNF grammar forces valid JSON tool calls
    → deterministic tools: intercrop_planner · input_allocator · planting_scheduler
    → localised natural-language answer → offline UI
```

- **Inference core** (`gesa/model.py`): llama.cpp via `llama-cpp-python`, `n_gpu_layers=0` (CPU-only).
- **Grammar guard** (`gesa/grammar.py`): a GBNF grammar constrains the model to emit
  `{"tool": "<name>", "args": {...}}` with tool names as quoted JSON strings — a tiny model *cannot*
  emit malformed calls.
- **Agent orchestrator** (`gesa/orchestrator.py`): a ReAct loop hard-capped at `max_steps` (bounds
  RAM and inference time). Model errors (bad JSON, wrong args, unknown crop) are **contained** — the
  loop appends an error observation and lets the model self-correct rather than crashing.
- **Deterministic tools** (`gesa/tools/`): pure functions with agronomy ground truth; the accuracy core.
- **Localisation** (`gesa/locale/`): pluggable; the target answer language is threaded into the prompt.
- **UI** (`gesa/ui/`): FastAPI + a fully self-contained offline HTML form (no CDN, no external fonts).

## 4. The deterministic tools (the accuracy core)

- **`intercrop_planner`** — per-crop spacing, rows, and plant counts for a valid mixed planting;
  flags incompatible crop pairs; validates crops (rejects unknown/empty/duplicate).
- **`input_allocator`** — allocates the urea a farmer actually has across crops in proportion to
  remaining nitrogen need, crediting the nitrogen a legume gives an intercropped cereal (urea = 46% N).
- **`planting_scheduler`** — three risk-staggered planting windows (early/main/late, 30/50/20) around
  the historical rainfall onset, from **bundled offline data** (`data/rainfall/onset.json`) — no
  weather API, which would violate the no-network rule.

All agronomy constants live in one auditable file (`gesa/agronomy.py`) for review by a domain expert.

## 5. Model selection (bake-off)

Intended candidates (`bench/bakeoff.py`): Qwen2.5-3B-Instruct Q4_K_M, Qwen2.5-1.5B-Instruct Q4_K_M,
Gemma-2-2B-it Q4_K_M — compared on tool-call validity, tokens/sec, and peak RSS under the 7 GB cap.

**Live run in this report:** `qwen2.5-1.5b-instruct-q4_k_m.gguf` (1.1 GB) — a *fallback* candidate,
run here to validate the pipeline. The live results (§6) show 1.5B is too weak at tool-following
(33% accuracy); the ample RAM headroom (peak 1.95 GB of 7 GB) confirms the intended
**Qwen2.5-3B-Instruct Q4_K_M** fits comfortably and should be the primary model.

**Pipeline validated live:** the model loads in 0.7 s, correctly selects `intercrop_planner`
(maize+beans), the deterministic tool computes the layout, and the agent returns a clean localised
answer. Two live findings drove improvements: (a) the model mis-converted "half an acre" to 500 m²
(→ motivates wiring `normalize_area`, see §10); (b) on a malformed scheduler call the loop **contained
the error without crashing**, confirming the orchestrator's error-recovery.

## 6. Benchmark results

Measured by `bench/harness.py` under RAM-capped emulation (`bench/emulate.sh`,
`systemd-run -p MemoryMax=7G -p MemorySwapMax=0`). Scoring sub-values are ESTIMATES; the official
scoring differs.

Model: `qwen2.5-1.5b-instruct-q4_k_m.gguf` · 6-scenario suite · this machine (CPU-only). The 7 GB
RAM cap via `systemd-run --user --scope -p MemoryMax=7G -p MemorySwapMax=0` was confirmed functional.

| Metric | Value | Notes |
|---|---|---|
| Accuracy | **33.3%** (2/6) | 1.5B is weak at tool-following; intercrop tasks pass, scheduler/allocator often fail |
| Tokens/sec (~) | 6.12 | rough char-based proxy |
| **Peak RSS** | **1952 MB** | **well under the 7 GB ceiling** — no OOM risk; room for the 3B model |
| Max core temp | n/a | `sensors` not installed on this machine |
| S estimate | 0.40 | proxy sub-scores; official scoring differs |

**Interpretation:** the constraints are met with large margin (1.95 GB peak, no OOM, bounded loop).
The limiter is *model quality*, not the system — a 3B model (which still fits) should lift accuracy
substantially, and wiring `normalize_area` (§10) removes a known accuracy leak.

## 7. Localisation

The localisation layer is pluggable (English + Fulfulde), and the requested language is threaded into
the model's system prompt so the answer is composed in that language. **Open item:** the Fulfulde
strings are placeholders and must be verified by a native Fulfulde speaker before final submission.

## 8. Compliance checklist

- [x] Runs entirely offline — no network in the request path (in-process llama.cpp; UI form fully
  inline, no CDN/fonts/external fetch).
- [x] CPU-only — `n_gpu_layers=0`; no GPU/discrete-graphics path.
- [x] Inference via llama.cpp + GGUF only; open base model (Qwen2.5).
- [x] Bounded work per request — hard step cap + fixed context window.
- [x] Peak RAM < 7 GB — **verified: 1952 MB peak** (§6); 7 GB `systemd-run` cap confirmed functional.
- [ ] Cores < 85 °C under sustained use — `sensors` unavailable on this machine; measure on target laptop.
- [x] Deliverables: open-source repo, this REPORT.md, demo, 2-minute video.

## 9. Engineering method

Built test-first (TDD) across 16 tasks, each independently code-reviewed for spec compliance and
quality; a final whole-branch review preceded merge. **44+ automated tests**, all passing. Bugs the
review process caught and fixed include an invalid-JSON grammar bug, a crash on empty crop input, and
missing agent-loop error containment.

## 10. Open items before final submission

- Verify Fulfulde locale strings with a native speaker.
- Wire `normalize_area` into the request path so unit conversion (acre/hectare/plot → m²) is
  deterministic rather than model-performed.
- Emit key advisory lines (e.g. insufficient-urea, planting-window count) via the locale layer
  deterministically, rather than relying on model phrasing.
- Run the full 3-model bake-off and the benchmark on the actual target-profile laptop.
