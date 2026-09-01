import requests
import pytest
from streamlit.testing.v1 import AppTest


def test_all_three_views_render_when_every_source_is_unavailable(monkeypatch) -> None:
    def fail_request(*args, **kwargs):
        raise requests.ConnectionError("simulated source outage")

    monkeypatch.setattr(requests, "get", fail_request)
    app = AppTest.from_file("app.py").run(timeout=20)

    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Brazil expectations",
        "BRL/USD",
        "Brazil–US rates",
    ]


@pytest.mark.parametrize("file_contents", [None, "{not valid json"])
def test_app_loads_when_research_file_is_missing_or_malformed(
    monkeypatch, tmp_path, file_contents
) -> None:
    def fail_request(*args, **kwargs):
        raise requests.ConnectionError("simulated source outage")

    research_path = tmp_path / "data_snapshot.json"
    if file_contents is not None:
        research_path.write_text(file_contents, encoding="utf-8")

    monkeypatch.setattr(requests, "get", fail_request)
    monkeypatch.setenv("SCENARIO_RESEARCH_PATH", str(research_path))
    app = AppTest.from_file("app.py").run(timeout=20)

    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Brazil expectations",
        "BRL/USD",
        "Brazil–US rates",
    ]
    assert any("Scenario Lab research is unavailable" in warning.value for warning in app.warning)


def test_app_loads_when_downloadable_brief_is_missing(monkeypatch, tmp_path) -> None:
    def fail_request(*args, **kwargs):
        raise requests.ConnectionError("simulated source outage")

    monkeypatch.setattr(requests, "get", fail_request)
    monkeypatch.setenv("MARKET_BRIEF_PDF_PATH", str(tmp_path / "missing-brief.pdf"))
    app = AppTest.from_file("app.py").run(timeout=20)

    assert not app.exception
    assert any(
        "downloadable PDF is not available" in caption.value for caption in app.caption
    )
