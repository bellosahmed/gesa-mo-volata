from gesa.grammar import build_tool_grammar

def test_grammar_matches_quoted_tool_names():
    g = build_tool_grammar()
    for name in ("intercrop_planner", "input_allocator", "planting_scheduler"):
        assert name in g
        # tool names must be matched as QUOTED JSON strings in GBNF (escaped quotes)
        assert f'\\"{name}\\"' in g

def test_grammar_has_root_and_object_rules():
    g = build_tool_grammar()
    assert "root" in g
    assert "object" in g
