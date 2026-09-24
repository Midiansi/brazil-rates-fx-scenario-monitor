"""The printable briefs: searchable, localized, complete and up to date."""
from __future__ import annotations

import re

import pytest
from pypdf import PdfReader

from src.content import TEXT
from src.pdf_brief import markdown_brief, render_pdf

from conftest import ROOT

FILES = {"en": "Brazil_Rates_FX_Trade_Brief.pdf", "pt": "Brazil_Rates_FX_Trade_Brief_PT.pdf", "fr": "Brazil_Rates_FX_Trade_Brief_FR.pdf"}


def text_of(path) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() for page in reader.pages)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(" ", " ").replace(" ", " ")).strip()


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    import json

    thesis = json.loads((ROOT / "research" / "thesis.json").read_text(encoding="utf-8"))
    frozen = json.loads((ROOT / thesis["inputs_file"]).read_text(encoding="utf-8"))
    folder = tmp_path_factory.mktemp("pdf")
    return {lang: render_pdf(thesis, frozen, folder / name, lang) for lang, name in FILES.items()}, thesis


@pytest.mark.parametrize("lang", ["en", "pt", "fr"])
def test_pdf_is_searchable_localized_and_short(generated, lang) -> None:
    paths, _ = generated
    reader = PdfReader(paths[lang])
    assert 2 <= len(reader.pages) <= 4
    text = normalize(text_of(paths[lang]))
    t = TEXT[lang]
    for key in ("pdf_title", "view_label", "act_label", "change_label", "trade_title", "review_title"):
        assert normalize(t[key]).split(":")[0][:30].lower() in text.lower(), key
    assert ("5,10" if lang != "en" else "5.10") in text
    assert ("5,1792" if lang != "en" else "5.1792") in text
    assert reader.metadata.author == "Romeo Mugnier de Almeida"
    annotations = sum(len(page.get("/Annots") or []) for page in reader.pages)
    assert annotations >= 20  # clickable sources


@pytest.mark.parametrize("lang", ["pt", "fr"])
def test_translated_pdf_has_no_english_headings(generated, lang) -> None:
    text = normalize(text_of(generated[0][lang]))
    for english in ("What would make me act", "The paper trade", "What happened to my", "Main risks", "Key figures"):
        assert english not in text
    if lang == "pt":
        assert "matérias-primas" not in text.lower()


def test_arrow_and_decimal_marks_survive_extraction(generated) -> None:
    assert "→" in text_of(generated[0]["en"])
    assert "13,75" in text_of(generated[0]["fr"])


@pytest.mark.parametrize("lang", ["en", "pt", "fr"])
def test_committed_pdfs_match_the_current_content(generated, lang) -> None:
    committed = ROOT / "outputs" / FILES[lang]
    assert committed.is_file(), "run: python scripts/generate_market_brief.py"
    assert normalize(text_of(committed)) == normalize(text_of(generated[0][lang])), (
        "outputs/ is out of date — run: python scripts/generate_market_brief.py"
    )


def test_markdown_companion_matches(generated) -> None:
    _, thesis = generated
    committed = (ROOT / "research" / "market_brief.md").read_text(encoding="utf-8")
    assert committed == markdown_brief(thesis)
    assert "not investment advice" in committed.lower()
