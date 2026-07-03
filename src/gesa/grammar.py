from gesa.tools.registry import TOOLS

def build_tool_grammar() -> str:
    names = " | ".join(f'"\\"{n}\\""' for n in list(TOOLS) + ["final"])
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
