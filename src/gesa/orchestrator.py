import json
from gesa.grammar import build_tool_grammar
from gesa.locale import t
from gesa.tools.registry import TOOLS, dispatch

def _system(lang: str) -> str:
    language = t("answer_language", lang=lang)
    signatures = ", ".join(f"{name}({', '.join(TOOLS[name]['args'])})" for name in TOOLS)
    return (
        "You are a farm planning assistant. Respond ONLY with one JSON tool call. "
        f"Tools: {signatures}. "
        'When done, use {"tool":"final","args":{"answer":"..."}}. '
        f"Write the final answer in {language}.\n"
    )

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
    return {"steps": steps, "answer": answer}
