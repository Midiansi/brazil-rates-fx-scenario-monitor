#!/usr/bin/env python3
"""Regenerate the three printable briefs and the English Markdown companion.

Offline and deliberate: the PDFs describe the dated thesis in
research/thesis.json and are committed, never generated during a page visit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.pdf_brief import markdown_brief, render_pdf  # noqa: E402
from src.thesis import load_thesis, read_json  # noqa: E402

NAMES = {"en": "Brazil_Rates_FX_Trade_Brief.pdf", "pt": "Brazil_Rates_FX_Trade_Brief_PT.pdf", "fr": "Brazil_Rates_FX_Trade_Brief_FR.pdf"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", type=Path, default=PROJECT_ROOT / "outputs")
    parser.add_argument("--markdown", type=Path, default=PROJECT_ROOT / "research" / "market_brief.md")
    args = parser.parse_args()
    thesis = load_thesis(PROJECT_ROOT / "research" / "thesis.json")
    # The brief describes the dated thesis, so it reads the data frozen with it,
    # not the daily-refreshed snapshot.
    snapshot = read_json(PROJECT_ROOT / thesis.get("inputs_file", "research/live_snapshot.json")) if thesis else {}
    if not thesis:
        print("research/thesis.json is missing or invalid.", file=sys.stderr)
        return 1
    for lang, name in NAMES.items():
        print(f"Generated {render_pdf(thesis, snapshot, args.outputs / name, lang)}")
    args.markdown.write_text(markdown_brief(thesis), encoding="utf-8")
    print(f"Generated {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
