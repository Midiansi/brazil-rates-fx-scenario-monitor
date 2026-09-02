import requests
from streamlit.testing.v1 import AppTest


def test_app_renders_without_any_network(monkeypatch) -> None:
    def fail_request(*args, **kwargs):
        raise requests.ConnectionError("simulated source outage")

    monkeypatch.setattr(requests, "get", fail_request)
    app = AppTest.from_file("app.py").run(timeout=10)

    assert not app.exception
    assert any("Brazil in brief" in header.value for header in app.header)
    assert any("Brazil commodities" in header.value for header in app.header)
    assert any("live refresh is optional" in caption.value for caption in app.caption)
    assert not app.warning


def test_network_is_not_called_on_first_render(monkeypatch) -> None:
    calls = []
    def record_request(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("network must not be on the first-render path")

    monkeypatch.setattr(requests, "get", record_request)
    app = AppTest.from_file("app.py").run(timeout=10)
    assert not app.exception
    assert calls == []
