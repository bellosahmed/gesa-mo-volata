from gesa.locale import en, ff

_LANGS = {"en": en.STRINGS, "ff": ff.STRINGS}

def t(key: str, lang: str = "en", **kw) -> str:
    table = _LANGS.get(lang, en.STRINGS)
    template = table.get(key) or en.STRINGS.get(key) or key
    return template.format(**kw) if kw else template
