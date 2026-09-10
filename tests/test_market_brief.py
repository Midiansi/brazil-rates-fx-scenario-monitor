from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

from src.brief import derive_trade_thresholds, generate_market_brief


SNAPSHOT_PATH = Path("research/data_snapshot.json")


def generate_to_tmp(tmp_path: Path) -> tuple[Path, Path, dict]:
    pdf_path = tmp_path / "Brazil_Rates_FX_Trade_Brief.pdf"
    markdown_path = tmp_path / "market_brief.md"
    context = generate_market_brief(SNAPSHOT_PATH, pdf_path, markdown_path)
    return pdf_path, markdown_path, context


def test_brief_is_generated_as_three_readable_searchable_pages(tmp_path: Path) -> None:
    pdf_path, markdown_path, _ = generate_to_tmp(tmp_path)

    assert pdf_path.is_file()
    assert pdf_path.stat().st_size > 0
    assert markdown_path.is_file()

    reader = PdfReader(pdf_path)
    assert len(reader.pages) == 3
    assert len(reader.pages[0].extract_text()) > 500


def test_brief_contains_required_sections_and_one_trade(tmp_path: Path) -> None:
    pdf_path, _, _ = generate_to_tmp(tmp_path)
    text = "\n".join(page.extract_text() for page in PdfReader(pdf_path).pages)

    required = ("Brazil macro: one conditional trade", "OBSERVED", "SCENARIOS", "PAPER TRADE", "COMMODITIES", "METHOD AND SOURCE LIMITS")
    assert all(section in text for section in required)
    assert "No position at the saved snapshot" in text


def test_brief_thresholds_match_saved_ptax_range(tmp_path: Path) -> None:
    payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    thresholds = derive_trade_thresholds(payload)
    pdf_path, _, context = generate_to_tmp(tmp_path)
    text = "\n".join(page.extract_text() for page in PdfReader(pdf_path).pages)

    saved_range = payload["series"]["ptax_usd_brl_midpoint"]["twenty_observation_range"]
    assert str(thresholds.entry) == "5.22"
    assert str(thresholds.invalidation) == "5.16"
    assert str(thresholds.measured_move) == "5.3561"
    assert str(thresholds.review_low) == "5.35"
    assert str(thresholds.review_high) == "5.36"
    assert float(thresholds.range_high) == saved_range["high"]
    assert f"{thresholds.entry:.2f}" in text
    assert f"{thresholds.invalidation:.2f}" in text
    assert f"{thresholds.range_high:.4f}" in text
    assert f"{thresholds.measured_move:.4f}" in text
    assert "5.1567" in text and "2026-09-01" in text


def test_brief_disclaimer_and_no_missing_placeholders(tmp_path: Path) -> None:
    pdf_path, markdown_path, _ = generate_to_tmp(tmp_path)
    combined = (
        "\n".join(page.extract_text() for page in PdfReader(pdf_path).pages)
        + "\n"
        + markdown_path.read_text(encoding="utf-8")
    )

    assert "not investment advice" in combined.lower()
    assert "not actual execution" in combined
    lowered = combined.lower()
    for placeholder in ("tbd", "n/a", "none", "nan", "{placeholder}", "lorem ipsum"):
        assert not re.search(r'\b'+re.escape(placeholder)+r'\b', lowered)
