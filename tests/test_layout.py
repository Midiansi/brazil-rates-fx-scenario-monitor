"""Static checks of the responsive layout (browser checks are in the README)."""
from __future__ import annotations

import re

from conftest import ROOT

CSS = (ROOT / "src" / "style.css").read_text(encoding="utf-8")


def block(query: str) -> str:
    start = CSS.index(query)
    depth, index = 0, CSS.index("{", start)
    for position in range(index, len(CSS)):
        depth += {"{": 1, "}": -1}.get(CSS[position], 0)
        if depth == 0:
            return CSS[index:position]
    raise AssertionError(query)


def test_breakpoints_exist() -> None:
    for query in ("@media (max-width: 1080px)", "@media (max-width: 820px)", "@media (max-width: 560px)", "@media (prefers-reduced-motion: reduce)"):
        assert query in CSS


def test_multi_column_grids_collapse_on_phones() -> None:
    phone = block("@media (max-width: 820px)")
    for selector in (".why", ".decide", ".kinds", ".paths", ".about"):
        assert selector in phone
    assert "grid-template-columns: minmax(0, 1fr)" in phone
    assert ".chart-wide { display: none; }" in phone and ".chart-compact { display: block; }" in phone
    assert ".legend { display: flex; }" in phone


def test_tables_scroll_instead_of_overflowing() -> None:
    assert re.search(r"\.table-wrap \{[^}]*overflow-x: auto", CSS)
    page = (ROOT / "src" / "page.py").read_text(encoding="utf-8")
    assert page.count('class="table-wrap') == page.count('tabindex="0" role="region"')


def test_no_fixed_widths_wider_than_a_phone_outside_media_queries() -> None:
    flat = re.sub(r"@media[^{]+\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", CSS)
    for value in re.findall(r"(?<!max-)width:\s*(\d+)px", flat):
        assert int(value) <= 360, value


def test_focus_styles_and_colour_tokens() -> None:
    assert ":focus-visible" in CSS
    assert CSS.count("#") < 40  # colours come from a handful of tokens
