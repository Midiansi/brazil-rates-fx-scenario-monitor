"""Brazil Macro — production entrypoint.

Every visit reads two small local JSON files and pre-generated PDFs; nothing
here touches the network, generates a PDF or runs pandas.  The page is a few
large HTML blocks, cached per language and per data-file version, so the first
render and language switches stay fast.
"""
from __future__ import annotations

import importlib
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import streamlit as st

from src import chart, content, formatting, freshness, page, thesis

ROOT = Path(__file__).resolve().parent
THESIS_PATH = ROOT / "research" / "thesis.json"
SNAPSHOT_PATH = ROOT / "research" / "live_snapshot.json"
CSS_PATH = ROOT / "src" / "style.css"
LANGUAGES = {"EN": "en", "PT": "pt", "FR": "fr"}
PDF_NAMES = {"en": "Brazil_Rates_FX_Trade_Brief.pdf", "pt": "Brazil_Rates_FX_Trade_Brief_PT.pdf", "fr": "Brazil_Rates_FX_Trade_Brief_FR.pdf"}
MODULES = (formatting, content, freshness, chart, thesis, page)  # dependency order


def _mtime(path: Path | str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _refresh_modules() -> float:
    """Reload local modules after a redeploy.

    Streamlit reruns this file in a long-lived process; without this, a deploy
    that changes ``src/`` can leave stale modules in memory until a reboot.
    """

    stamps = [_mtime(module.__file__) for module in MODULES]
    if any(getattr(module, "_loaded_mtime", stamp) != stamp for module, stamp in zip(MODULES, stamps)):
        for module in MODULES:
            importlib.reload(module)
    for module, stamp in zip(MODULES, stamps):
        module._loaded_mtime = stamp
    return max(stamps + [_mtime(CSS_PATH)])


@lru_cache(maxsize=4)
def _css(version: float) -> str:
    """Stylesheet with comments and indentation stripped (sent on every rerun)."""

    try:
        raw = CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
    raw = re.sub(r"\s*\n\s*", "", raw)
    raw = re.sub(r"\s*([{};,>])\s*", r"\1", raw)
    return "<style>" + raw + "</style>"


@lru_cache(maxsize=16)
def _blocks(lang: str, today: str, versions: tuple[float, float, float]) -> dict[str, str]:
    saved_thesis = thesis.load_thesis(THESIS_PATH)
    snapshot = thesis.read_json(SNAPSHOT_PATH)
    return page.render(lang, saved_thesis, snapshot, datetime.fromisoformat(today).date())


@lru_cache(maxsize=8)
def _pdf(path: str, version: float) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError:
        return b""


def _language() -> str:
    requested = str(st.query_params.get("lang", "en")).lower()
    if "language" not in st.session_state:
        st.session_state["language"] = next((label for label, code in LANGUAGES.items() if code == requested), "EN")
    return st.session_state["language"]


st.set_page_config(page_title="Brazil Macro · Romeo Mugnier de Almeida", page_icon="🇧🇷", layout="wide")
code_version = _refresh_modules()
st.html(_css(code_version))

_language()
top_left, top_right = st.columns([5, 1.4], vertical_alignment="center")
with top_right:
    choice = st.segmented_control(
        "Language / Idioma / Langue", options=list(LANGUAGES), key="language",
        label_visibility="collapsed", width="content",
    )
if choice is None:  # clicking the active option deselects it; keep the last language
    choice = st.session_state.get("_last_language", "EN")
st.session_state["_last_language"] = choice
lang = LANGUAGES[choice]
if st.query_params.get("lang", "en") != lang:
    st.query_params["lang"] = lang

today = datetime.now(timezone.utc).date().isoformat()
blocks = _blocks(lang, today, (code_version, _mtime(THESIS_PATH), _mtime(SNAPSHOT_PATH)))
with top_left:
    st.html(blocks["top"])
st.html(blocks["hero"])

pdf_path = ROOT / "outputs" / PDF_NAMES[lang]
pdf_bytes = _pdf(str(pdf_path), _mtime(pdf_path))
if pdf_bytes:
    st.download_button(
        content.TEXT[lang]["download"], data=pdf_bytes, file_name=pdf_path.name, mime="application/pdf",
        help=content.TEXT[lang]["download_help"], on_click="ignore", icon=":material/download:",
    )

if "toc" in blocks:  # its own element so CSS can pin it while the sections scroll
    st.html(blocks["toc"])
if "body_1" in blocks:
    st.html(blocks["body_1"])
    if blocks.get("chart"):
        st.markdown(blocks["chart"], unsafe_allow_html=True)
    st.html(blocks["body_2"])
