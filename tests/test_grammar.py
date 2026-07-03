from gesa.grammar import build_tool_grammar

def test_grammar_lists_tool_names():
    g = build_tool_grammar()
    assert '"intercrop_planner"' in g
    assert '"planting_scheduler"' in g
    assert "root" in g  # GBNF requires a root rule

def test_grammar_has_json_object_rule():
    g = build_tool_grammar()
    assert "object" in g
