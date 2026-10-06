"""The production entrypoint: network-free, light, and complete in three languages."""
from __future__ import annotations

import re
import sys
from html import unescape

import pytest
from streamlit.testing.v1 import AppTest

EXPECTED = {
    "EN": ("Brazil macro, from policy to price.", "What I would do", "Track record: a one-day-old call, checked"),
    "PT": ("Brasil macro: da política monetária aos preços.", "O que eu faria", "Histórico: uma visão de um dia atrás, conferida"),
    "FR": ("Le Brésil, de la politique monétaire aux marchés.", "Ce que je ferais", "une vue vieille d’un jour, vérifiée"),
}


def page_text(app: AppTest) -> str:
    chunks = [element.proto.body for element in app.get("html")]
    chunks += [element.value for element in app.markdown]
    return unescape("\n".join(chunks))


def download_label(app: AppTest) -> str:
    buttons = app.get("download_button")
    assert buttons, "download button missing"
    return buttons[0].proto.label


def run(**query) -> AppTest:
    app = AppTest.from_file("app.py", default_timeout=30)
    for key, value in query.items():
        app.query_params[key] = value
    return app.run()


def test_first_render_makes_no_network_call(no_network) -> None:
    app = run()
    assert not app.exception
    assert no_network == []


def test_render_imports_no_heavy_or_network_modules(monkeypatch) -> None:
    for name in ("reportlab", "src.data", "src.live_refresh", "src.pdf_brief"):
        monkeypatch.delitem(sys.modules, name, raising=False)  # restored after the test
    app = run()
    assert not app.exception
    # Streamlit itself may import pandas; the app's own modules must not need
    # the refresh or PDF stacks.
    assert "src.live_refresh" not in sys.modules
    assert "src.data" not in sys.modules
    assert "src.pdf_brief" not in sys.modules
    assert "reportlab" not in sys.modules


def test_page_is_a_handful_of_elements() -> None:
    app = run()
    assert len(app.get("html")) <= 12  # large blocks, not hundreds of widgets
    assert len(app.markdown) <= 6  # the five inline-SVG figures
    assert len(app.button_group) == 1


@pytest.mark.parametrize("label", ["EN", "PT", "FR"])
def test_every_language_renders_completely(label, no_network) -> None:
    app = run()
    if label != "EN":
        app.button_group[0].set_value([label]).run()
    assert not app.exception
    text = page_text(app)
    for fragment in EXPECTED[label]:
        assert fragment in text
    assert app.query_params.get("lang", ["en"]) == [label.lower()]
    assert not re.search(r"\{[a-z_0-9]+\}", text), "unfilled placeholder"
    assert no_network == []


def test_lens_can_be_shared_by_url() -> None:
    quant = page_text(run())
    commodities = page_text(run(lens="commodities"))
    assert quant.index("Rates, FX and quant: what the first day tells us") < quant.index("Commodities: Brazil sells in dollars")
    assert commodities.index("Commodities: Brazil sells in dollars") < commodities.index("Rates, FX and quant: what the first day tells us")


def test_language_can_be_shared_by_url() -> None:
    app = run(lang="pt")
    assert not app.exception
    assert EXPECTED["PT"][0] in page_text(app)
    assert download_label(app).startswith("Baixar o relatório")


def test_clicking_the_active_language_keeps_the_page() -> None:
    app = run()
    app.button_group[0].set_value([]).run()
    assert not app.exception
    assert EXPECTED["EN"][0] in page_text(app)


def test_download_button_serves_the_localized_pdf() -> None:
    app = run(lang="fr")
    assert "PDF, français" in download_label(app)
