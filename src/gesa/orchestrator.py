import json
from gesa.grammar import build_tool_grammar
from gesa.locale import t
from gesa.tools.registry import TOOLS, dispatch
from gesa.tools.scheduler import available_regions_seasons

def _system(lang: str) -> str:
    language = t("answer_language", lang=lang)
    signatures = ", ".join(f"{name}({', '.join(TOOLS[name]['args'])})" for name in TOOLS)
    regions_seasons = "; ".join(
        f"{r}: {', '.join(s)}" for r, s in available_regions_seasons().items()
    )
    return (
        "You are a farm planning assistant. Respond ONLY with one JSON tool call. "
        f"Tools: {signatures}. "
        "For plot size, provide area_value and area_unit (e.g. 0.5 and \"acre\") exactly as stated in the request; "
        "do NOT convert to square metres yourself. "
        f"For planting_scheduler, valid region/season values are: {regions_seasons}. "
        'Example: {"tool":"planting_scheduler","args":{"region":"east_africa","season":"long_rains"}}. '
        'When done, use {"tool":"final","args":{"answer":"..."}}. '
        f"Write the final answer in {language}.\n"
    )

def compose_advisories(steps, lang):
    """Deterministic, localised advisory lines derived from executed tool results."""
    lines = []
    for s in steps:
        if s["tool"] == "input_allocator" and s["result"].get("sufficient") is False:
            lines.append(t("insufficient_urea", lang=lang))
        if s["tool"] == "planting_scheduler":
            lines.append(t("plant_windows", lang=lang, n=len(s["result"]["windows"])))
    return lines

def run(request: str, model, max_steps: int = 4, lang: str = "en") -> dict:
    grammar = build_tool_grammar()
    steps, transcript = [], f"{_system(lang)}Request: {request}\n"
    answer = ""
    for _ in range(max_steps):
        raw = model.complete(transcript, grammar=grammar)
        try:
            call = json.loads(raw)
            if call["tool"] == "final":
                answer = call["args"].get("answer", "")
                break
            result = dispatch(call["tool"], call["args"])
            steps.append({"tool": call["tool"], "args": call["args"], "result": result})
            transcript += f"Observation: {json.dumps(result)}\n"
        except Exception as e:
            transcript += f"Observation: error: {e}\n"
    advisories = compose_advisories(steps, lang)
    answer = (answer + "\n" + "\n".join(advisories)).strip() if advisories else answer
    return {"steps": steps, "answer": answer}
