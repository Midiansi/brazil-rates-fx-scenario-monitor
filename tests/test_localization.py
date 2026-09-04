from streamlit.testing.v1 import AppTest


def render_portuguese() -> AppTest:
    app = AppTest.from_file("app.py").run(timeout=10)
    app.toggle[0].set_value(True).run(timeout=10)
    assert not app.exception
    return app


def visible_text(app: AppTest) -> str:
    chunks: list[str] = []
    for element_type in (
        "title",
        "header",
        "subheader",
        "markdown",
        "caption",
        "info",
        "expander",
    ):
        for element in getattr(app, element_type):
            value = getattr(element, "value", None)
            if isinstance(value, str):
                chunks.append(value)
            label = getattr(element, "label", None)
            if isinstance(label, str):
                chunks.append(label)
    return "\n".join(chunks)


def test_portuguese_view_translates_deep_content() -> None:
    text = visible_text(render_portuguese())

    expected_portuguese = (
        "Canal externo",
        "Juros / câmbio / commodities",
        "Petróleo",
        "Minério de ferro",
        "Mais restritivo que o esperado",
        "Caminho dos juros",
        "Tese original",
        "Regra de entrada",
        "Autor do projeto",
        "Ver o código",
        "Para quem quiser conferir o trabalho",
        "Criado por Romeo Mugnier de Almeida",
    )
    assert all(fragment in text for fragment in expected_portuguese)

    untranslated_fragments = (
        "External channel",
        ">Oil<",
        ">Iron ore<",
        ">Soybeans<",
        ">Sugar<",
        "Hawkish relative to expectations",
        "Dovish relative to expectations",
        "**Policy path**",
        "**Original thesis**",
        "**Entry rule**",
        "Project author",
        "Inspect the code",
        "For readers who want to check the work",
        "Built by Romeo Mugnier de Almeida",
    )
    assert all(fragment not in text for fragment in untranslated_fragments)
    assert "matérias-primas" not in text.lower()
    assert "matérias primas" not in text.lower()


def test_portuguese_snapshot_date_uses_portuguese_month() -> None:
    text = visible_text(render_portuguese())
    assert "1 set 2026" in text
    assert "1 Sep 2026" not in text
