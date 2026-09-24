from __future__ import annotations

import copy
import json
import socket
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THESIS_DATE = date(2026, 9, 24)


def load(name: str) -> dict:
    return json.loads((ROOT / "research" / name).read_text(encoding="utf-8"))


@pytest.fixture
def thesis() -> dict:
    return load("thesis.json")


@pytest.fixture
def frozen(thesis) -> dict:
    """The data saved with the thesis; stable even after the daily refresh."""

    return json.loads((ROOT / thesis["inputs_file"]).read_text(encoding="utf-8"))


@pytest.fixture
def snapshot(frozen) -> dict:
    return copy.deepcopy(frozen)


@pytest.fixture
def no_network(monkeypatch):
    """Fail loudly if anything opens a socket or calls requests."""

    calls: list = []

    def refuse(*args, **kwargs):
        calls.append(args)
        raise AssertionError("network access attempted during a page render")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    try:
        import requests

        monkeypatch.setattr(requests, "get", refuse)
        monkeypatch.setattr(requests.Session, "request", refuse)
    except ImportError:  # pragma: no cover - requests is a refresh-job dependency
        pass
    return calls
