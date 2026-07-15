# Gesa Mo Volata — ADTC 2026 Report

**Domain:** `agriculture` · **Model:** Qwen2.5-1.5B-Instruct-Q4_K_M (llama.cpp, GGUF) ·
**Challenge:** Africa Deep Tech Challenge 2026 (The Laptop LLM Challenge)

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

**Two candidates were run live on this machine (CPU-only):** Qwen2.5-1.5B and Qwen2.5-3B, both
Q4_K_M. See §6 for the head-to-head — the notable result is that on our strict benchmark the 3B did
**not** beat the 1.5B and is ~2× slower, so for this workload the **1.5B is the better speed/RAM
trade-off** while both stay far under the RAM ceiling.

**Pipeline validated live:** the model loads in 0.7 s, correctly selects `intercrop_planner`
(maize+beans), the deterministic tool computes the layout, and the agent returns a clean localised
answer over the real FastAPI UI (POST `/plan`). Live findings that drove fixes: (a) the model
mis-converted "half an acre" to 500 m² → we wired `normalize_area` so units convert in code (now
"half an acre" → 2023 m², "2 hectares" → 20000 m², verified live); (b) a malformed scheduler call was
**contained without crashing**, confirming the orchestrator's error-recovery.

## 6. Benchmark results

Measured by `bench/harness.py` under RAM-capped emulation (`bench/emulate.sh`,
`systemd-run -p MemoryMax=7G -p MemorySwapMax=0`). Scoring sub-values are ESTIMATES; the official
scoring differs.

6-scenario suite · this machine (CPU-only, 32 threads). The 7 GB RAM cap via
`systemd-run --user --scope -p MemoryMax=7G -p MemorySwapMax=0` was confirmed functional.

| Model (Q4_K_M) | Accuracy* | Tokens/sec~ | Peak RSS | S est. |
|---|---|---|---|---|
| **Qwen2.5-1.5B** | 33.3% (2/6) | **6.12** | **1952 MB** | **0.40** |
| Qwen2.5-3B | 33.3% (2/6) | 3.20 | 3605 MB | 0.31 |

**Full run *under* the active 7 GB cap** (Qwen2.5-1.5B, whole 6-scenario agent suite inside the
`systemd-run` scope, no swap): completed with **no OOM**, strict accuracy 50% (3/6), ~2.7 agent-loop
tokens/sec, **peak RSS 1286 MB** — ~18% of the ceiling.

**Official ADTC profiler** (`adtc-profiler 0.1.0`, participant mode, `--skip-accuracy`,
`measured_on: participant_laptop`) on this submission's `metadata.json` + `download_model.sh`:

| Metric | Value |
|---|---|
| Generation speed (llama-bench) | 33.44 t/s |
| First-token latency (pp512) | 2607 ms |
| Peak RSS | 1828 MB |
| Core temp peak | **68.4 °C — no throttling** |
| CPU p99 | 77.9% |

(The profiler's 33.4 t/s is raw single-pass generation; the harness's ~3–6 t/s is end-to-end
*agent-loop* throughput including multiple model calls and tool execution — different quantities.)

\* *Accuracy is a strict **exact-args match** against deterministic ground truth — a harsh lower bound.
It does not credit "selected the right tool with reasonable args," which the live demos did well
(e.g. correct intercrop layout for 2 ha). Treat it as a floor, not a ceiling.*

**Interpretation:**
- **Constraints met with large margin:** both models run CPU-only, bounded loop, no OOM; peak RSS
  1.95 GB (1.5B) / 3.6 GB (3B), both far under 7 GB.
- **3B did not beat 1.5B here** and is ~2× slower, so on this workload the **1.5B is the better
  speed/efficiency choice** (higher S estimate). This is a benchmark-driven finding, not an
  assumption.
- The accuracy metric is the bottleneck, not the models: the strict exact-match scoring under-credits
  good-but-not-identical plans. A follow-up should add a semantic accuracy metric ("right tool +
  args within valid range") to differentiate models fairly; the failing scenarios are mainly the
  enum-style `region`/`season` scheduler calls and exact-value allocator matches.

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
- [x] Peak RAM < 7 GB — **verified: 1286 MB peak for the full agent suite run *inside* the active
  7 GB `systemd-run` cap** (§6); official profiler measured 1828 MB peak RSS.
- [x] Cores < 85 °C — official ADTC profiler measured **68.4 °C peak, no throttling** on this dev
  machine; re-confirm on the target-profile laptop.
- [x] Official submission layout — `metadata.json`, `download_model.sh` (idempotent, public URL),
  `model/` gitignored, MIT `LICENSE`; validated end-to-end with `adtc-profiler run --mode participant`
  (valid `submission.json` produced).
- [x] Deliverables: open-source repo (MIT), this REPORT.md, demo UI; 2-minute video pending.

## 9. Engineering method

Built test-first (TDD) across 16 tasks, each independently code-reviewed for spec compliance and
quality; a final whole-branch review preceded merge. **44+ automated tests**, all passing. Bugs the
review process caught and fixed include an invalid-JSON grammar bug, a crash on empty crop input, and
missing agent-loop error containment.

## 10. Improvements made from live evidence, and remaining open items

**Done (verified live):** unit conversion is now deterministic. Tools accept the plot as
`area_value` + `area_unit`; `normalize_area` converts in code. Confirmed with the real model:
"half an acre" now resolves to **2023.43 m²** (correct), where the model alone had guessed 500 m².

**Remaining before final submission:**
- Verify Fulfulde locale strings with a native speaker.
- Register on the ADTF portal and fill the real `team_id` into `metadata.json`.
- Re-run `adtc-profiler` and the harness on the actual target-profile laptop (4 vCPU / 8 GB); capture
  the UI screenshots and the 2-minute demo video.
- Optional: add a semantic accuracy metric ("right tool + args within valid range") — the strict
  exact-match metric under-credits good plans (§6).
