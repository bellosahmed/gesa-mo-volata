# Gesa Mo Volata — Design Spec

**Project:** Gesa Mo Volata — an offline whole-plot planning agent for African smallholder farmers
**Competition:** Africa Deep Tech Challenge 2026 — *The Laptop LLM Challenge*, Agriculture track
**Date:** 2026-07-03
**Status:** Draft for review
**Submission deadline (Gate 1):** 2026-08-25

---

## 1. Summary

Gesa Mo Volata is an on-device agricultural planning assistant that runs entirely offline on a
low-cost laptop (the "ADTC Standard Laptop": ~$150–500, 8 GB RAM with a **7 GB usable ceiling**,
integrated graphics, CPU-only, Ubuntu 22.04). A small quantized language model interprets a
farmer's request in natural language and their own language; a set of **deterministic Python tools**
does all the actual agronomy math (intercrop layout, input allocation, planting dates); the model
then composes a plain-language, localised answer.

The guiding principle is **"think in language, calculate in code."** The model is only trusted to do
what small models are good at — understanding intent and phrasing answers. Every number a farmer
relies on is produced by verifiable code, not model guesswork.

## 2. Why this design (mapping to the judging rubric)

Scoring: `S = 0.50·Accuracy + 0.30·Speed + 0.20·Efficiency − ThermalPenalty`,
plus **+15%** local-language support, **+10%** budget-profile optimization, and a required
cross-disciplinary integration (Best Integration award). Hard constraints: ≤7 GB RAM (OOM =
instant disqualification), CPU-only, cores <85 °C, **zero network during judging**, must use
**llama.cpp + GGUF** with open base models only.

| Rubric element | How this design wins it |
|---|---|
| Accuracy (50%) | Correctness offloaded to deterministic tools → near-guaranteed, verifiable. Removes the failure mode (a tiny model getting numbers wrong) that sinks Math/Healthcare/Creative entries. |
| Speed (30%) | ~2 GB Q4 model on CPU + a **capped** agent loop (few passes, short contexts). |
| Efficiency (20%) | Fixed context window + loop-depth cap keep peak RAM and heat predictable; benchmark harness proves it under emulation. |
| Thermal penalty | Bounded work per request keeps cores below 85 °C. |
| +15% local language | Pluggable localisation layer; primary target **Fulfulde** (see §7), confirmed in the model bake-off. |
| +10% budget profile | Planning around scarce, locally-available, affordable inputs *is* the product. |
| Best Integration | Four orchestrated tools (intercrop + inputs + rainfall + pest) driven by an agent loop. |

**The unique angle:** competitors will ship a farming *chatbot* (RAG Q&A) built on Western
monoculture assumptions. Gesa Mo Volata models the realities generic tools ignore — intercropping,
no soil tests, only-what's-at-market inputs, rain-fed risk-staggering, and household food-security
optimization — which are exactly the multi-step planning problems an agent-plus-tools system is
uniquely suited to. For a rural farmer with no signal, offline is not a contest rule to tolerate;
it is the entire point of the product.

## 3. Scope

**v1 (this submission):** intercrop layout + input allocation + rainfall-staggered planting dates,
in a local language, via a capped agent loop with a local UI and a benchmark harness.

**Stretch (only if RAM/time allow):** `pest_advisor` push-pull pest-management tool.

**Explicitly out of scope for v1:** image/photo diagnosis, live weather, multi-plot farm management,
market-price data, account/sync features.

## 4. Architecture

Six layers, top-to-bottom data flow, all inside the 7 GB boundary:

1. **Farmer request** — natural language, local language.
2. **Inference core** — llama.cpp serving a small GGUF model (candidate: Qwen2.5-3B-Instruct
   Q4_K_M, ~2 GB; fallbacks Qwen2.5-1.5B, Gemma-2-2B). The only "AI"; never trusted with arithmetic.
3. **Agent orchestrator** — a capped ReAct loop (hard limit 3–4 steps, fixed context window) that
   plans, calls tools, observes results, and decides the next step. Guarded by a **GBNF grammar**
   that forces every tool call to valid JSON so the small model cannot emit malformed calls.
4. **Tool layer (deterministic Python)** — `intercrop_planner`, `input_allocator`,
   `planting_scheduler` (+ stretch `pest_advisor`), plus bundled offline data (historical rainfall
   tables, agronomic constants).
5. **Answer composer + localisation layer** — model turns exact tool numbers into a friendly answer,
   routed through a swappable locale module.
6. **Local UI** — minimal FastAPI + static HTML (or TUI); nothing loads from a CDN or the network.

Cross-cutting: a **profiler/benchmark harness** measures accuracy, tokens/sec, peak RAM and
temperature under a RAM-capped emulation of the target laptop.

Reference architecture diagram: `docs/superpowers/specs/architecture.html` (published artifact).

## 5. Components (units, each independently testable)

### 5.1 Deterministic tools (pure functions — the accuracy core)
- **`intercrop_planner(plot, crops)` → layout**
  Input: plot size (in local units + normalized area), chosen crop set. Output: per-crop spacing,
  row arrangement, plant counts for a valid mixed planting. Encodes spacing tables + companion rules.
- **`input_allocator(available_inputs, crops, layout)` → allocation**
  Input: quantities of fertilizer/manure actually available. Output: per-crop allocation, legume
  nitrogen-credit aware, flagged if insufficient. Optimizes for the budget-profile bonus.
- **`planting_scheduler(region, season, rainfall_data)` → windows**
  Input: region/season. Output: risk-staggered planting date windows derived from bundled historical
  rainfall onset distributions.
- **(stretch) `pest_advisor(crops, region)` → plan** — push-pull (desmodium + napier) recommendation.

Each tool: documented I/O contract, input validation, no hidden dependencies, unit-tested against
agronomic ground-truth cases.

### 5.2 Inference core
Thin wrapper over the llama.cpp server (local HTTP or in-process bindings). Loads the selected GGUF,
exposes a `complete(prompt, grammar=None)` interface. Config: context size, thread count, temperature.

### 5.3 Agent orchestrator
Capped ReAct loop. Responsibilities: build the system/tool prompt, call the model with the GBNF
grammar, parse the tool call, dispatch to the tool, feed the observation back, enforce the step and
context caps, and terminate with a composed answer. Repairs or rejects invalid tool args rather than
crashing.

### 5.4 Grammar guard
GBNF grammar defining the exact JSON shape of a tool call (`{"tool": "...", "args": {...}}`),
enumerating valid tool names. Passed to llama.cpp so generation is constrained.

### 5.5 Localisation layer
Pluggable locale module: all user-facing strings and advisory phrasing routed through it. A locale is
a data file + phrasing rules. Language-agnostic core; localised skin.

### 5.6 Local UI
Minimal FastAPI + static HTML page (fallback: TUI). No external fonts/CDN/network. A single form:
plot size, crops, available inputs, region/season → rendered plan.

### 5.7 Benchmark harness
Runs a scenario suite under a RAM-capped emulation (`systemd-run --property=MemoryMax=7G` /
cgroups, CPU-only build). Reports accuracy vs ground truth, tokens/sec, peak RSS, and core
temperature; computes an estimate of `S`. This is how we keep dev numbers honest on powerful hardware.

## 6. Data flow

Farmer request → orchestrator plans → grammar-guarded tool call(s) → deterministic tool(s) compute
exact numbers → orchestrator composes a localised natural-language answer → UI renders it. Fully
offline; all data bundled in the repo.

## 7. Localisation target

Primary candidate: **Fulfulde** (the Fulɓe are agro-pastoralists across the Sahel — a large,
underserved farming audience; consistent with the project name). Final choice confirmed in the
Phase 1 model bake-off based on which language the selected model actually handles reliably; the
pluggable layer means the choice is reversible without touching the core.

## 8. Error handling

- Loop depth + context hard caps → protect against OOM (instant DQ) and thermal penalty.
- Tool input validation → repair or refuse bad model-supplied args, never crash the loop.
- Missing-information prompts → when a request lacks plot size / inputs / region, ask for it rather
  than guessing.
- Insufficient-inputs case → tools return an explicit "not enough fertilizer for X" result, surfaced
  honestly to the farmer.

## 9. Testing strategy

- **TDD for tools:** ground-truth agronomic test cases written *before* implementation; tools are
  pure functions and fully testable without the model.
- **Grammar tests:** assert the model can only emit valid tool-call JSON.
- **Orchestrator integration tests:** end-to-end farmer scenarios → expected tool sequence + answer.
- **Benchmark/acceptance:** the harness runs the scenario suite under the 7 GB emulation and asserts
  no OOM, cores <85 °C, and target thresholds for accuracy/speed.

## 10. Constraints & compliance checklist

- [ ] Runs entirely offline (no network calls anywhere in the request path).
- [ ] Peak RAM stays under 7 GB (verified under emulation).
- [ ] CPU-only; no GPU/discrete-graphics dependency.
- [ ] Cores stay below 85 °C under sustained use.
- [ ] Inference via llama.cpp + GGUF only; open base model (Qwen/Gemma/Llama/Mistral/Phi).
- [ ] Deliverables: open-source GitHub repo, `REPORT.md`, screenshots/demo, 2-minute video.

## 11. Deliverables (Gate 1 — 2026-08-25)

- Open-source GitHub repository (this repo).
- `REPORT.md` — design, benchmarks, rubric mapping, localisation notes.
- Screenshots / demo clips of the running app.
- 2-minute video walkthrough.

## 12. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Small model unreliable at tool calls | GBNF grammar guard forces valid JSON; capped, single-tool-per-step loop. |
| Agent loop blows RAM / slows down (30% speed) | Hard depth + context caps; benchmark under emulation from Phase 0. |
| Model weak in Fulfulde | Pluggable locale layer; bake-off picks the best-supported language; bilingual fallback. |
| Scope creep vs Aug 25 deadline | `pest_advisor` and extras are explicitly stretch; v1 is three tools. |
| Dev machine flatters results | All measurement done under RAM-capped, CPU-only emulation. |

## 13. Open questions

- Confirm the literal meaning of "Gesa Mo Volata" for `REPORT.md`.
- Lock the localisation language after Phase 1 (Fulfulde vs Swahili vs bilingual).
- UI form vs TUI for the demo video — decide in Phase 5 based on which shows better.
