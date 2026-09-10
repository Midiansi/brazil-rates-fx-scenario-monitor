from streamlit.testing.v1 import AppTest


def render_portuguese() -> AppTest:
    app = AppTest.from_file("app.py").run(timeout=10)
    app.button_group[0].set_value(["🇧🇷 PT"]).run(timeout=10)
    assert not app.exception
    return app


def render_french() -> AppTest:
    app = AppTest.from_file("app.py").run(timeout=10)
    app.button_group[0].set_value(["🇫🇷 FR"]).run(timeout=10)
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
        "Do movimento da commodity à tese de investimento",
        "Exposição da receita",
        "Margem e curva de custos",
        "Balanço patrimonial",
        "Avaliação e decisão",
        "margem de segurança",
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
        "From a commodity move to an investment case",
        "Revenue exposure",
        "Margin and cost curve",
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


def test_french_view_translates_primary_and_deep_content() -> None:
    text = visible_text(render_french())

    expected_french = (
        "Le Brésil, de la politique monétaire aux marchés",
        "En bref",
        "Pourquoi ces chiffres comptent",
        "Canal externe",
        "Pétrole",
        "Minerai de fer",
        "Du mouvement d'une matière première à une thèse d'investissement",
        "Exposition du chiffre",
        "Marges et courbe de coûts",
        "Plus restrictif que prévu",
        "Trajectoire des taux",
        "Thèse initiale",
        "Règle d'entrée",
        "Auteur du projet",
        "Voir le code",
        "Créé par Romeo Mugnier de Almeida",
    )
    assert all(fragment in text for fragment in expected_french)

    untranslated_fragments = (
        "The short version",
        "Why these numbers matter",
        "External channel",
        ">Oil<",
        ">Iron ore<",
        ">Soybeans<",
        ">Sugar<",
        "From a commodity move to an investment case",
        "Revenue exposure",
        "Margin and cost curve",
        "Hawkish relative to expectations",
        "Dovish relative to expectations",
        "**Policy path**",
        "**Original thesis**",
        "**Entry rule**",
        "Project author",
        "Inspect the code",
        "Built by Romeo Mugnier de Almeida",
    )
    assert all(fragment not in text for fragment in untranslated_fragments)


def test_french_snapshot_date_uses_french_month() -> None:
    text = visible_text(render_french())
    assert "1 sept. 2026" in text
    assert "1 Sep 2026" not in text
