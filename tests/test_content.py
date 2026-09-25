"""English, Portuguese and French must say the same thing, with the same numbers."""
from __future__ import annotations

import re
import string

import pytest

from src.content import TEXT
from src.thesis import placeholders

RUNTIME = {"latest", "latest_date", "date", "value", "n", "start", "end", "year", "attempted", "ok", "total", "names"}


def shape(value):
    if isinstance(value, dict):
        return {key: shape(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [shape(item) for item in value]
    return "str"


def strings(value, path=""):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from strings(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from strings(item, f"{path}[{index}]")


def fields(text):
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_languages_have_identical_structure() -> None:
    assert shape(TEXT["en"]) == shape(TEXT["pt"]) == shape(TEXT["fr"])


def test_same_placeholders_in_every_language() -> None:
    english = dict(strings(TEXT["en"]))
    for lang in ("pt", "fr"):
        for path, text in strings(TEXT[lang]):
            assert fields(text) == fields(english[path]), f"{lang}{path}"


@pytest.mark.parametrize("lang", ["en", "pt", "fr"])
def test_every_placeholder_resolves(thesis, lang) -> None:
    available = set(placeholders(thesis, lang)) | RUNTIME
    for path, text in strings(TEXT[lang]):
        assert fields(text) <= available, f"{lang}{path}: {fields(text) - available}"


def test_portuguese_says_commodities() -> None:
    joined = " ".join(text for _, text in strings(TEXT["pt"])).lower()
    assert "matérias-primas" not in joined and "matérias primas" not in joined
    assert "commodities" in joined


def test_french_punctuation_never_wraps() -> None:
    for path, text in strings(TEXT["fr"]):
        assert not re.search(r" [:;?!%»]", text), path
        assert "« " not in text, path


def test_no_untranslated_english_in_translations() -> None:
    english = {text for _, text in strings(TEXT["en"]) if len(text) > 25}
    for lang in ("pt", "fr"):
        for path, text in strings(TEXT[lang]):
            if len(text) > 25 and not path.endswith(("source_labels.anbima_ettj", "source_labels.eia_steo")):
                assert text not in english, f"{lang}{path} is still English"


def test_no_inflated_or_forbidden_wording() -> None:
    joined = " ".join(text for lang in TEXT for _, text in strings(TEXT[lang])).lower()
    for phrase in (" owned", "guarantee", "passionate", "expert", "world-class", "probability of", "will definitely"):
        assert phrase not in joined, phrase


def test_ai_assistance_is_disclosed_in_every_language() -> None:
    markers = {"en": "AI tools", "pt": "Ferramentas de IA", "fr": "Des outils d’IA"}
    for lang, marker in markers.items():
        assert any(marker in text for text in TEXT[lang]["limits"])
