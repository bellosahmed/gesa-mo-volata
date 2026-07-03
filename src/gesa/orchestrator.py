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
