"""The printable briefs: searchable, localized, complete and up to date."""
from __future__ import annotations

import re

import pytest
from pypdf import PdfReader

from src.content import TEXT
from src.copom_content import TEXT as NOTE_TEXT
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

    from src.thesis import load_thesis

    thesis = load_thesis(ROOT / "research" / "thesis.json")
    frozen = json.loads((ROOT / thesis["inputs_file"]).read_text(encoding="utf-8"))
    folder = tmp_path_factory.mktemp("pdf")
    return {lang: render_pdf(thesis, frozen, folder / name, lang) for lang, name in FILES.items()}, thesis


@pytest.mark.parametrize("lang", ["en", "pt", "fr"])
def test_pdf_is_searchable_localized_and_short(generated, lang) -> None:
    paths, _ = generated
    reader = PdfReader(paths[lang])
    assert len(reader.pages) == 2
    text = normalize(text_of(paths[lang]))
    for key in ("title", "ticket_label", "q1_title", "q2_title", "q3_title", "q4_title", "q5_title", "q6_title", "q8_title"):
        assert normalize(NOTE_TEXT[lang][key]).lower() in text.lower(), key
    assert ("5,4775" if lang != "en" else "5.4775") in text
    assert ("14,39" if lang != "en" else "14.39") in text
    assert ("14,00" if lang != "en" else "14.00") in text
    assert reader.metadata.author == "Romeo Mugnier de Almeida"
    annotations = sum(len(page.get("/Annots") or []) for page in reader.pages)
    assert annotations >= 9  # clickable sources for this publication


@pytest.mark.parametrize("lang", ["pt", "fr"])
def test_translated_pdf_has_no_english_headings(generated, lang) -> None:
    text = normalize(text_of(generated[0][lang]))
    for english in ("What I would do", "The paper trade", "Track record", "Main risks", "Key figures", "What would change my mind"):
        assert english not in text
    if lang == "pt":
        assert "matérias-primas" not in text.lower()


def test_signs_and_decimal_marks_survive_extraction(generated) -> None:
    assert "−R$82,000" in normalize(text_of(generated[0]["en"]))
    assert "205.083" in text_of(generated[0]["pt"])
    assert "5,4775" in text_of(generated[0]["fr"])


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
