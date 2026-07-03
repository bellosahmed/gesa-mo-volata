# Gesa Mo Volata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline agriculture planning agent that runs on an 8 GB CPU-only laptop, where a small GGUF model interprets farmer requests and deterministic Python tools produce all agronomy numbers.

**Architecture:** A capped ReAct agent loop drives a small llama.cpp/GGUF model whose tool calls are forced to valid JSON by a GBNF grammar. Three deterministic tools (intercrop layout, input allocation, rainfall-staggered planting) own all correctness; the model only understands intent and phrases answers, routed through a pluggable localisation layer. A benchmark harness verifies everything under a 7 GB RAM-capped emulation of the target laptop.

**Tech Stack:** Python 3.10 (Ubuntu 22.04 default), `llama-cpp-python` (in-process llama.cpp bindings — no network), `pytest`, `fastapi` + `uvicorn` (local UI). GGUF model candidate: Qwen2.5-3B-Instruct Q4_K_M.

## Global Constraints

- Python 3.10; standard library + the pinned deps only. No package that requires network at runtime.
- Inference via `llama-cpp-python` (llama.cpp) with **GGUF** weights only. Open base model only (Qwen/Gemma/Llama/Mistral/Phi).
- **Zero network calls** anywhere in the request path. No CDN, no remote fonts, no API.
- Peak process RSS must stay **under 7 GB**; OOM = instant disqualification.
- **CPU-only** — no CUDA/GPU code paths.
- Keep per-request work bounded so cores stay **< 85 °C**.
- All development metrics measured under RAM-capped, CPU-only emulation (`systemd-run --property=MemoryMax=7G`).
- TDD throughout; commit after each passing task. Package name: `gesa`.

---

## File Structure

```
gesa_mo_volata/
  pyproject.toml                 # project + pytest config
  requirements.txt               # pinned runtime deps
  README.md
  REPORT.md                      # ADTC deliverable (Task 15)
  models/                        # .gguf weights (gitignored)
  data/rainfall/                 # bundled historical rainfall onset tables
  src/gesa/
    __init__.py
    units.py                     # local-unit -> m^2 normalization
    agronomy.py                  # spacing tables, companion & N-fixation constants
    tools/
      __init__.py
      intercrop.py               # intercrop_planner
      inputs.py                  # input_allocator
      scheduler.py               # planting_scheduler
      registry.py                # tool registry + JSON schemas
    grammar.py                   # GBNF grammar builder
    model.py                     # inference core wrapper + ModelClient protocol
    orchestrator.py              # capped ReAct loop
    locale/
      __init__.py                # localisation layer (get/translate)
      en.py                      # English strings
      ff.py                      # Fulfulde strings
    ui/
      app.py                     # FastAPI app
      static/index.html          # single-page form (no CDN)
  bench/
    emulate.sh                   # systemd-run RAM-capped wrapper
    scenarios.py                 # scenario suite + ground truth
    harness.py                   # runs scenarios, reports S estimate
  tests/
    test_units.py
    tools/test_intercrop.py
    tools/test_inputs.py
    tools/test_scheduler.py
    test_registry.py
    test_grammar.py
    test_orchestrator.py
    test_locale.py
```

---

### Task 1: Project scaffold & test harness

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `src/gesa/__init__.py`, `tests/__init__.py`, `README.md`

**Interfaces:**
- Produces: an importable `gesa` package and a working `pytest` command.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "gesa"
version = "0.1.0"
requires-python = ">=3.10"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `requirements.txt`**

```
llama-cpp-python==0.3.2
fastapi==0.115.0
uvicorn==0.30.6
pytest==8.3.3
```

- [ ] **Step 3: Create package markers**

`src/gesa/__init__.py` and `tests/__init__.py` as empty files. `README.md` with one-line project description.

- [ ] **Step 4: Verify pytest runs**

Run: `pip install pytest && pytest -q`
Expected: `no tests ran` (exit 0), package discoverable.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml requirements.txt src/gesa/__init__.py tests/__init__.py README.md
git commit -m "chore: scaffold gesa package and pytest"
```

---

### Task 2: Local-unit normalization (`units.py`)

Farmers use local area units, not hectares. This module normalizes them to m².

**Files:**
- Create: `src/gesa/units.py`
- Test: `tests/test_units.py`

**Interfaces:**
- Produces: `normalize_area(value: float, unit: str) -> float` (returns m²); raises `ValueError` on unknown unit. Supported units: `"m2"`, `"acre"` (4046.86 m²), `"hectare"` (10000 m²), `"plot"` (a local 15m×15m=225 m² unit).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_units.py
import pytest
from gesa.units import normalize_area

def test_acre_to_m2():
    assert normalize_area(1, "acre") == pytest.approx(4046.86, rel=1e-4)

def test_half_acre():
    assert normalize_area(0.5, "acre") == pytest.approx(2023.43, rel=1e-4)

def test_local_plot_unit():
    assert normalize_area(2, "plot") == 450.0

def test_unknown_unit_raises():
    with pytest.raises(ValueError):
        normalize_area(1, "furlong")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_units.py -v`
Expected: FAIL (`ModuleNotFoundError: gesa.units`).

- [ ] **Step 3: Write minimal implementation**

```python
# src/gesa/units.py
_TO_M2 = {"m2": 1.0, "acre": 4046.86, "hectare": 10000.0, "plot": 225.0}

def normalize_area(value: float, unit: str) -> float:
    key = unit.strip().lower()
    if key not in _TO_M2:
        raise ValueError(f"unknown area unit: {unit!r}")
    return value * _TO_M2[key]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_units.py -v` → Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/gesa/units.py tests/test_units.py
git commit -m "feat: local-unit area normalization"
```

---

### Task 3: Agronomy constants (`agronomy.py`)

Shared, citable constants used by the tools. Isolated so values are reviewable in one place.

**Files:**
- Create: `src/gesa/agronomy.py`

**Interfaces:**
- Produces:
  - `SPACING` — `dict[str, dict]`: per-crop `{"row_cm": int, "plant_cm": int, "legume": bool, "n_need_kg_ha": float}`.
  - `COMPANION` — `set[frozenset[str]]`: crop pairs that intercrop well.
  - `LEGUME_N_CREDIT_KG_HA` — nitrogen (kg/ha) a legume contributes to a paired cereal.

- [ ] **Step 1: Create the module**

```python
# src/gesa/agronomy.py
# Sources: national extension spacing guides (maize/beans/cowpea/cassava).
SPACING = {
    "maize":   {"row_cm": 75, "plant_cm": 25, "legume": False, "n_need_kg_ha": 60.0},
    "beans":   {"row_cm": 45, "plant_cm": 10, "legume": True,  "n_need_kg_ha": 20.0},
    "cowpea":  {"row_cm": 60, "plant_cm": 20, "legume": True,  "n_need_kg_ha": 15.0},
    "cassava": {"row_cm": 100, "plant_cm": 100, "legume": False, "n_need_kg_ha": 40.0},
}
COMPANION = {
    frozenset({"maize", "beans"}),
    frozenset({"maize", "cowpea"}),
    frozenset({"cassava", "cowpea"}),
}
LEGUME_N_CREDIT_KG_HA = 30.0
```

- [ ] **Step 2: Sanity import**

Run: `python -c "from gesa.agronomy import SPACING; print(len(SPACING))"` → Expected: `4`.

- [ ] **Step 3: Commit**

```bash
git add src/gesa/agronomy.py
git commit -m "feat: agronomy spacing and companion constants"
```

---

### Task 4: `intercrop_planner` tool

**Files:**
- Create: `src/gesa/tools/__init__.py`, `src/gesa/tools/intercrop.py`
- Test: `tests/tools/test_intercrop.py`

**Interfaces:**
- Consumes: `gesa.units.normalize_area`, `gesa.agronomy.SPACING`, `gesa.agronomy.COMPANION`.
- Produces: `intercrop_planner(area_m2: float, crops: list[str]) -> dict` returning
  `{"area_m2": float, "compatible": bool, "layout": {crop: {"rows": int, "plants": int, "row_cm": int, "plant_cm": int}}}`.
  Plants per crop = `floor(area_share_m2 / (row_cm/100 * plant_cm/100))`, where each crop gets an equal share of area. Raises `ValueError` for unknown crop.

- [ ] **Step 1: Write the failing test**

```python
# tests/tools/test_intercrop.py
import pytest
from gesa.tools.intercrop import intercrop_planner

def test_maize_beans_layout_on_half_acre():
    r = intercrop_planner(2023.43, ["maize", "beans"])
    assert r["compatible"] is True
    # maize share 1011.7 m2 / (0.75*0.25=0.1875) -> 5395 plants
    assert r["layout"]["maize"]["plants"] == 5395
    assert r["layout"]["beans"]["plants"] == 22482  # /(0.45*0.10=0.045)

def test_incompatible_pair_flagged():
    r = intercrop_planner(1000, ["maize", "cassava"])
    assert r["compatible"] is False

def test_unknown_crop_raises():
    with pytest.raises(ValueError):
        intercrop_planner(1000, ["maize", "quinoa"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_intercrop.py -v` → Expected: FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# src/gesa/tools/intercrop.py
import math
from itertools import combinations
from gesa.agronomy import SPACING, COMPANION

def intercrop_planner(area_m2: float, crops: list[str]) -> dict:
    for c in crops:
        if c not in SPACING:
            raise ValueError(f"unknown crop: {c!r}")
    compatible = all(frozenset(p) in COMPANION for p in combinations(crops, 2)) if len(crops) > 1 else True
    share = area_m2 / len(crops)
    layout = {}
    for c in crops:
        s = SPACING[c]
        cell_m2 = (s["row_cm"] / 100) * (s["plant_cm"] / 100)
        plants = math.floor(share / cell_m2)
        rows = math.floor((share ** 0.5) / (s["row_cm"] / 100))
        layout[c] = {"rows": rows, "plants": plants,
                     "row_cm": s["row_cm"], "plant_cm": s["plant_cm"]}
    return {"area_m2": area_m2, "compatible": compatible, "layout": layout}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/tools/test_intercrop.py -v` → Expected: 3 passed. (Create `src/gesa/tools/__init__.py` and `tests/tools/__init__.py` if missing.)

- [ ] **Step 5: Commit**

```bash
git add src/gesa/tools/ tests/tools/test_intercrop.py
git commit -m "feat: intercrop_planner tool"
```

---

### Task 5: `input_allocator` tool

**Files:**
- Create: `src/gesa/tools/inputs.py`
- Test: `tests/tools/test_inputs.py`

**Interfaces:**
- Consumes: `gesa.agronomy.SPACING`, `gesa.agronomy.LEGUME_N_CREDIT_KG_HA`.
- Produces: `input_allocator(area_m2: float, crops: list[str], urea_kg: float) -> dict` returning
  `{"required_n_kg": float, "urea_available_n_kg": float, "sufficient": bool, "allocation": {crop: kg_urea}}`.
  Urea is 46% N. Legume N-credit reduces the cereal's need when a legume is intercropped. Allocation is proportional to each crop's remaining N need.

- [ ] **Step 1: Write the failing test**

```python
# tests/tools/test_inputs.py
import pytest
from gesa.tools.inputs import input_allocator

def test_sufficient_allocation_maize_beans():
    # 0.2 ha maize+beans. maize need 60*0.2=12kg N minus 30*0.2=6 credit =6kg; beans 20*0.2=4kg
    r = input_allocator(2000, ["maize", "beans"], urea_kg=25)
    assert r["required_n_kg"] == pytest.approx(10.0, rel=1e-3)
    assert r["urea_available_n_kg"] == pytest.approx(11.5, rel=1e-3)  # 25*0.46
    assert r["sufficient"] is True

def test_insufficient_flagged():
    r = input_allocator(4046.86, ["maize"], urea_kg=1)
    assert r["sufficient"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_inputs.py -v` → Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# src/gesa/tools/inputs.py
from gesa.agronomy import SPACING, LEGUME_N_CREDIT_KG_HA

UREA_N_FRACTION = 0.46

def input_allocator(area_m2: float, crops: list[str], urea_kg: float) -> dict:
    ha = area_m2 / 10000.0
    has_legume = any(SPACING[c]["legume"] for c in crops)
    needs = {}
    for c in crops:
        need = SPACING[c]["n_need_kg_ha"] * ha
        if not SPACING[c]["legume"] and has_legume:
            need = max(0.0, need - LEGUME_N_CREDIT_KG_HA * ha)
        needs[c] = need
    required = sum(needs.values())
    available_n = urea_kg * UREA_N_FRACTION
    total_need = required or 1.0
    allocation = {c: round((needs[c] / total_need) * urea_kg, 2) for c in crops}
    return {"required_n_kg": required, "urea_available_n_kg": available_n,
            "sufficient": available_n >= required, "allocation": allocation}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/tools/test_inputs.py -v` → Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/gesa/tools/inputs.py tests/tools/test_inputs.py
git commit -m "feat: input_allocator tool with legume N-credit"
```

---

### Task 6: `planting_scheduler` tool + bundled rainfall data

**Files:**
- Create: `data/rainfall/onset.json`, `src/gesa/tools/scheduler.py`
- Test: `tests/tools/test_scheduler.py`

**Interfaces:**
- Produces: `planting_scheduler(region: str, season: str, data_path: str = DEFAULT) -> dict` returning
  `{"region": str, "season": str, "onset_week": str, "windows": [{"label": str, "start": str, "share_pct": int}]}`.
  Reads bundled onset data (median onset + a staggering rule: split planting into 3 windows around onset to spread rainfall risk). Raises `KeyError` for unknown region/season.

- [ ] **Step 1: Create bundled data**

```json
// data/rainfall/onset.json
{
  "sahel": {
    "long_rains": {"onset_week": "2026-06-15", "std_days": 10}
  },
  "east_africa": {
    "long_rains": {"onset_week": "2026-03-10", "std_days": 12},
    "short_rains": {"onset_week": "2026-10-15", "std_days": 9}
  }
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/tools/test_scheduler.py
import pytest
from gesa.tools.scheduler import planting_scheduler

def test_three_staggered_windows():
    r = planting_scheduler("east_africa", "long_rains")
    assert r["onset_week"] == "2026-03-10"
    assert len(r["windows"]) == 3
    assert sum(w["share_pct"] for w in r["windows"]) == 100

def test_unknown_region_raises():
    with pytest.raises(KeyError):
        planting_scheduler("atlantis", "long_rains")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/tools/test_scheduler.py -v` → Expected: FAIL.

- [ ] **Step 4: Write minimal implementation**

```python
# src/gesa/tools/scheduler.py
import json, os
from datetime import date, timedelta

DEFAULT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "rainfall", "onset.json")

def planting_scheduler(region: str, season: str, data_path: str = DEFAULT) -> dict:
    with open(os.path.abspath(data_path)) as fh:
        data = json.load(fh)
    entry = data[region][season]  # KeyError if unknown
    onset = date.fromisoformat(entry["onset_week"])
    std = entry["std_days"]
    offsets = [(-std, "early (risk hedge)", 30), (0, "main planting", 50), (std, "late (safety)", 20)]
    windows = [{"label": lbl, "start": (onset + timedelta(days=d)).isoformat(), "share_pct": pct}
               for d, lbl, pct in offsets]
    return {"region": region, "season": season, "onset_week": entry["onset_week"], "windows": windows}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/tools/test_scheduler.py -v` → Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add data/rainfall/onset.json src/gesa/tools/scheduler.py tests/tools/test_scheduler.py
git commit -m "feat: planting_scheduler with bundled rainfall onset data"
```

---

### Task 7: Tool registry & JSON schemas

**Files:**
- Create: `src/gesa/tools/registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: the three tool functions.
- Produces: `TOOLS: dict[str, dict]` mapping tool name → `{"fn": callable, "args": list[str]}`, and
  `dispatch(name: str, args: dict) -> dict` that validates arg names and calls the tool.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_registry.py
import pytest
from gesa.tools.registry import TOOLS, dispatch

def test_registry_lists_three_tools():
    assert set(TOOLS) == {"intercrop_planner", "input_allocator", "planting_scheduler"}

def test_dispatch_calls_tool():
    r = dispatch("planting_scheduler", {"region": "east_africa", "season": "long_rains"})
    assert r["region"] == "east_africa"

def test_dispatch_rejects_unknown_arg():
    with pytest.raises(ValueError):
        dispatch("planting_scheduler", {"region": "x", "season": "y", "bogus": 1})
```

- [ ] **Step 2: Run test to verify it fails** → `pytest tests/test_registry.py -v`

- [ ] **Step 3: Write minimal implementation**

```python
# src/gesa/tools/registry.py
from gesa.tools.intercrop import intercrop_planner
from gesa.tools.inputs import input_allocator
from gesa.tools.scheduler import planting_scheduler

TOOLS = {
    "intercrop_planner": {"fn": intercrop_planner, "args": ["area_m2", "crops"]},
    "input_allocator":   {"fn": input_allocator, "args": ["area_m2", "crops", "urea_kg"]},
    "planting_scheduler":{"fn": planting_scheduler, "args": ["region", "season"]},
}

def dispatch(name: str, args: dict) -> dict:
    if name not in TOOLS:
        raise ValueError(f"unknown tool: {name!r}")
    allowed = set(TOOLS[name]["args"])
    extra = set(args) - allowed
    if extra:
        raise ValueError(f"unexpected args for {name}: {extra}")
    return TOOLS[name]["fn"](**args)
```

- [ ] **Step 4: Run test to verify it passes** → Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/gesa/tools/registry.py tests/test_registry.py
git commit -m "feat: tool registry and dispatch"
```

---

### Task 8: GBNF grammar guard

**Files:**
- Create: `src/gesa/grammar.py`
- Test: `tests/test_grammar.py`

**Interfaces:**
- Consumes: `gesa.tools.registry.TOOLS`.
- Produces: `build_tool_grammar() -> str` returning a GBNF grammar string that constrains output to
  `{"tool": <one of the tool names>, "args": <json object>}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_grammar.py
from gesa.grammar import build_tool_grammar

def test_grammar_lists_tool_names():
    g = build_tool_grammar()
    assert '"intercrop_planner"' in g
    assert '"planting_scheduler"' in g
    assert "root" in g  # GBNF requires a root rule

def test_grammar_has_json_object_rule():
    g = build_tool_grammar()
    assert "object" in g
```

- [ ] **Step 2: Run test to verify it fails** → `pytest tests/test_grammar.py -v`

- [ ] **Step 3: Write minimal implementation**

```python
# src/gesa/grammar.py
from gesa.tools.registry import TOOLS

def build_tool_grammar() -> str:
    names = " | ".join(f'"\\"{n}\\""' for n in TOOLS)
    return f'''
root   ::= "{{" ws "\\"tool\\"" ws ":" ws toolname ws "," ws "\\"args\\"" ws ":" ws object ws "}}"
toolname ::= {names}
object ::= "{{" ws ( pair (ws "," ws pair)* )? ws "}}"
pair   ::= string ws ":" ws value
value  ::= string | number | object | array | "true" | "false" | "null"
array  ::= "[" ws ( value (ws "," ws value)* )? ws "]"
string ::= "\\"" ([^"\\\\] | "\\\\" .)* "\\""
number ::= "-"? [0-9]+ ("." [0-9]+)?
ws     ::= [ \\t\\n]*
'''.strip()
```

- [ ] **Step 4: Run test to verify it passes** → Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/gesa/grammar.py tests/test_grammar.py
git commit -m "feat: GBNF grammar guard for tool calls"
```

---

### Task 9: Inference core wrapper + ModelClient protocol

The real model is heavy and non-deterministic, so define a `ModelClient` protocol and a llama.cpp-backed implementation; tests use a fake.

**Files:**
- Create: `src/gesa/model.py`

**Interfaces:**
- Produces:
  - `class ModelClient(Protocol): def complete(self, prompt: str, grammar: str | None = None, max_tokens: int = 256) -> str: ...`
  - `class LlamaModel(ModelClient)` — loads a GGUF via `llama_cpp.Llama(model_path, n_ctx=2048, n_threads=os.cpu_count())`, applies `LlamaGrammar.from_string(grammar)` when given, returns text.

- [ ] **Step 1: Create the module**

```python
# src/gesa/model.py
import os
from typing import Protocol

class ModelClient(Protocol):
    def complete(self, prompt: str, grammar: str | None = None, max_tokens: int = 256) -> str: ...

class LlamaModel:
    def __init__(self, model_path: str, n_ctx: int = 2048):
        from llama_cpp import Llama
        self._llm = Llama(model_path=model_path, n_ctx=n_ctx,
                          n_threads=os.cpu_count(), n_gpu_layers=0, verbose=False)

    def complete(self, prompt: str, grammar: str | None = None, max_tokens: int = 256) -> str:
        from llama_cpp import LlamaGrammar
        g = LlamaGrammar.from_string(grammar) if grammar else None
        out = self._llm(prompt, grammar=g, max_tokens=max_tokens, temperature=0.2)
        return out["choices"][0]["text"]
```

- [ ] **Step 2: Import sanity (no model load)**

Run: `python -c "from gesa.model import ModelClient, LlamaModel; print('ok')"` → Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add src/gesa/model.py
git commit -m "feat: ModelClient protocol and llama.cpp-backed LlamaModel"
```

---

### Task 10: Capped ReAct orchestrator

**Files:**
- Create: `src/gesa/orchestrator.py`
- Test: `tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `gesa.model.ModelClient`, `gesa.grammar.build_tool_grammar`, `gesa.tools.registry.dispatch`.
- Produces: `run(request: str, model: ModelClient, max_steps: int = 4) -> dict` returning
  `{"steps": [{"tool": str, "args": dict, "result": dict}], "answer": str}`. Each step: prompt the
  model with the grammar for one tool call, dispatch it, append the observation; stop when the model
  emits `{"tool": "final", "args": {"answer": "..."}}` or `max_steps` is hit.

- [ ] **Step 1: Write the failing test (with a fake model)**

```python
# tests/test_orchestrator.py
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
```

- [ ] **Step 2: Run test to verify it fails** → `pytest tests/test_orchestrator.py -v`

- [ ] **Step 3: Write minimal implementation**

```python
# src/gesa/orchestrator.py
import json
from gesa.grammar import build_tool_grammar
from gesa.tools.registry import dispatch

SYSTEM = ("You are a farm planning assistant. Respond ONLY with one JSON tool call. "
          "Tools: intercrop_planner, input_allocator, planting_scheduler. "
          "When done, use {\"tool\":\"final\",\"args\":{\"answer\":\"...\"}}.\n")

def run(request: str, model, max_steps: int = 4) -> dict:
    grammar = build_tool_grammar()
    steps, transcript = [], f"{SYSTEM}Request: {request}\n"
    answer = ""
    for _ in range(max_steps):
        raw = model.complete(transcript, grammar=grammar)
        call = json.loads(raw)
        if call["tool"] == "final":
            answer = call["args"].get("answer", "")
            break
        result = dispatch(call["tool"], call["args"])
        steps.append({"tool": call["tool"], "args": call["args"], "result": result})
        transcript += f"Observation: {json.dumps(result)}\n"
    return {"steps": steps, "answer": answer}
```

Note: the `final` tool is control-only, so `build_tool_grammar` must also permit `"final"`. Update Task 8's grammar to append `| "\"final\""` to `toolname` (add a test asserting `'"final"' in g`).

- [ ] **Step 4: Run test to verify it passes** → Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/gesa/orchestrator.py tests/test_orchestrator.py src/gesa/grammar.py tests/test_grammar.py
git commit -m "feat: capped ReAct orchestrator with final-tool termination"
```

---

### Task 11: Localisation layer

**Files:**
- Create: `src/gesa/locale/__init__.py`, `src/gesa/locale/en.py`, `src/gesa/locale/ff.py`
- Test: `tests/test_locale.py`

**Interfaces:**
- Produces: `t(key: str, lang: str = "en", **kw) -> str` — looks up a template by key for the language,
  falls back to English if missing, formats with `kw`. Locales are plain dicts.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_locale.py
from gesa.locale import t

def test_english_lookup():
    assert t("plant_windows", lang="en", n=3) == "Plant in 3 staggered windows."

def test_fulfulde_lookup():
    assert t("plant_windows", lang="ff", n=3) != t("plant_windows", lang="en", n=3)

def test_missing_key_falls_back_to_key():
    assert t("nonexistent", lang="en") == "nonexistent"
```

- [ ] **Step 2: Run test to verify it fails** → `pytest tests/test_locale.py -v`

- [ ] **Step 3: Write minimal implementation**

```python
# src/gesa/locale/en.py
STRINGS = {"plant_windows": "Plant in {n} staggered windows.",
           "insufficient_urea": "You need more urea for this plan."}
# src/gesa/locale/ff.py
STRINGS = {"plant_windows": "Aawu e nder {n} sahaaji senaaɗi.",
           "insufficient_urea": "A ɗaɓɓi urea buri ngam eɓɓaango ngoo."}
# src/gesa/locale/__init__.py
from gesa.locale import en, ff
_LANGS = {"en": en.STRINGS, "ff": ff.STRINGS}
def t(key: str, lang: str = "en", **kw) -> str:
    table = _LANGS.get(lang, en.STRINGS)
    template = table.get(key) or en.STRINGS.get(key) or key
    return template.format(**kw) if kw else template
```

Note: Fulfulde strings are placeholders to be verified by a native speaker before submission (tracked in REPORT.md open items).

- [ ] **Step 4: Run test to verify it passes** → Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/gesa/locale/ tests/test_locale.py
git commit -m "feat: pluggable localisation layer with en + ff"
```

---

### Task 12: Local UI (FastAPI + static, no network)

**Files:**
- Create: `src/gesa/ui/app.py`, `src/gesa/ui/static/index.html`

**Interfaces:**
- Consumes: `gesa.orchestrator.run`, `gesa.model.LlamaModel`.
- Produces: FastAPI app with `GET /` (serves the form) and `POST /plan` (accepts request text + lang,
  returns the orchestrator result as JSON). Model path from `GESA_MODEL` env var.

- [ ] **Step 1: Write the app**

```python
# src/gesa/ui/app.py
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from gesa.orchestrator import run
from gesa.model import LlamaModel

app = FastAPI()
_STATIC = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC), name="static")
_model = None

class PlanReq(BaseModel):
    request: str
    lang: str = "en"

def _get_model():
    global _model
    if _model is None:
        _model = LlamaModel(os.environ["GESA_MODEL"])
    return _model

@app.get("/")
def index():
    return FileResponse(os.path.join(_STATIC, "index.html"))

@app.post("/plan")
def plan(req: PlanReq):
    return run(req.request, _get_model())
```

- [ ] **Step 2: Write `static/index.html`** — a single self-contained form (inline CSS/JS, **no CDN**) that POSTs to `/plan` and renders the returned steps + answer.

- [ ] **Step 3: Manual smoke test**

Run: `GESA_MODEL=models/model.gguf uvicorn gesa.ui.app:app` and load `http://127.0.0.1:8000/`.
Expected: form renders; submitting returns a plan JSON. Confirm no outbound network in devtools.

- [ ] **Step 4: Commit**

```bash
git add src/gesa/ui/
git commit -m "feat: local FastAPI UI with offline static form"
```

---

### Task 13: Model bake-off & selection

**Files:**
- Create: `bench/bakeoff.py`

**Interfaces:**
- Produces: a script that, given a list of local GGUF paths, runs a fixed set of tool-calling +
  multilingual prompts against each and prints tokens/sec, peak RSS, and tool-call validity rate.

- [ ] **Step 1: Write `bench/bakeoff.py`** iterating candidate models (Qwen2.5-3B Q4_K_M, Qwen2.5-1.5B, Gemma-2-2B), timing `LlamaModel.complete` on grammar-guarded prompts, measuring `resource.getrusage` peak RSS, and counting valid JSON tool calls.

- [ ] **Step 2: Download candidate GGUFs** into `models/` (documented in README; gitignored).

- [ ] **Step 3: Run under emulation** (see Task 14) and record results in `REPORT.md`. Select the model; set it as default `GESA_MODEL`.

- [ ] **Step 4: Commit**

```bash
git add bench/bakeoff.py
git commit -m "feat: model bake-off harness"
```

---

### Task 14: Benchmark harness under 7 GB emulation

**Files:**
- Create: `bench/emulate.sh`, `bench/scenarios.py`, `bench/harness.py`

**Interfaces:**
- Produces:
  - `emulate.sh` — wraps any command in `systemd-run --user --scope -p MemoryMax=7G -p MemorySwapMax=0`.
  - `scenarios.py` — `SCENARIOS: list[dict]` of `{request, expected_tools, ground_truth}`.
  - `harness.py` — runs each scenario end-to-end, checks tool results against ground truth (accuracy),
    measures tokens/sec (speed) and peak RSS + temperature (efficiency/thermal), prints an `S` estimate.

- [ ] **Step 1: Write `emulate.sh`**

```bash
#!/usr/bin/env bash
exec systemd-run --user --scope -p MemoryMax=7G -p MemorySwapMax=0 "$@"
```

- [ ] **Step 2: Write `scenarios.py`** with ~10 realistic farmer requests and their deterministic ground-truth tool outputs (reuse the tool functions to generate expected values).

- [ ] **Step 3: Write `harness.py`** computing accuracy (fraction of scenarios whose tool results match ground truth), mean tokens/sec, peak RSS (assert < 7 GB), and max core temp (`sensors` parse; assert < 85 °C).

- [ ] **Step 4: Run** `chmod +x bench/emulate.sh && ./bench/emulate.sh python bench/harness.py`
Expected: report printed; peak RSS < 7 GB; no OOM kill.

- [ ] **Step 5: Commit**

```bash
git add bench/emulate.sh bench/scenarios.py bench/harness.py
git commit -m "feat: benchmark harness under 7GB RAM emulation"
```

---

### Task 15: Deliverables (REPORT.md, demo, video)

**Files:**
- Create: `REPORT.md`; capture screenshots + 2-minute video (external).

- [ ] **Step 1: Write `REPORT.md`** — problem, architecture (link the diagram), the think-in-language/calculate-in-code thesis, model bake-off results, benchmark numbers (accuracy/speed/efficiency/thermal, `S` estimate), localisation notes (Fulfulde verification status), and the compliance checklist from the spec §10.
- [ ] **Step 2: Capture screenshots** of the running UI producing a plan.
- [ ] **Step 3: Record the 2-minute video** walkthrough (offline demo on the constrained profile).
- [ ] **Step 4: Final compliance pass** against spec §10 checklist; confirm repo is public and clean.
- [ ] **Step 5: Commit**

```bash
git add REPORT.md
git commit -m "docs: ADTC REPORT.md and deliverables"
```

---

## Self-Review

**Spec coverage:** every spec §5 component maps to a task — units (2), agronomy (3), tools (4–6),
registry (7), grammar (8), model (9), orchestrator (10), localisation (11), UI (12), benchmark
(13–14), deliverables (15). Spec §7 localisation → Task 11 + bake-off Task 13. Spec §10 compliance →
verified in Tasks 14–15.

**Placeholder scan:** the only intentional placeholders are the Fulfulde strings (flagged for
native-speaker verification) and model weights (downloaded in Task 13, gitignored) — both tracked,
neither a code gap.

**Type consistency:** `dispatch(name, args)`, `ModelClient.complete(prompt, grammar, max_tokens)`,
`run(request, model, max_steps)`, and `build_tool_grammar()` are used with identical signatures across
Tasks 7–12. Tool return-dict keys referenced in tests match the producing tasks.

**Known follow-up:** Task 10 requires the `"final"` control tool in the grammar; Task 8's grammar is
updated in Task 10's commit and covered by an added grammar test.
