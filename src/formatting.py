"""Locale-aware number, unit and date formatting for EN / PT / FR.

Portuguese and French use a decimal comma; French also puts a narrow
no-break space before % and uses "pts" for percentage points.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

LANGUAGES = ("en", "pt", "fr")
NNBSP = " "  # narrow no-break space (French typography)

MONTHS = {
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    "pt": ("jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."),
    "fr": ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."),
}


def num(value: float, digits: int = 2, lang: str = "en", signed: bool = False) -> str:
    text = f"{value:+,.{digits}f}" if signed else f"{value:,.{digits}f}"
    if lang == "en":
        return text.replace("-", "−")
    # 1,234.56 -> 1 234,56 (fr) / 1.234,56 (pt)
    thousands = NNBSP if lang == "fr" else "."
    text = text.replace(",", "\0").replace(".", ",").replace("\0", thousands)
    return text.replace("-", "−")


def pct(value: float, digits: int = 2, lang: str = "en", signed: bool = False) -> str:
    return num(value, digits, lang, signed) + (f"{NNBSP}%" if lang == "fr" else "%")


def pp(value: float, digits: int = 2, lang: str = "en", signed: bool = False) -> str:
    unit = {"en": " pp", "pt": " p.p.", "fr": f"{NNBSP}pt"}[lang]
    if lang == "fr" and abs(value) >= 2:
        unit = f"{NNBSP}pts"
    return num(value, digits, lang, signed) + unit


def usd(value: float, digits: int = 2, lang: str = "en") -> str:
    if lang == "en":
        return f"${num(value, digits, lang)}"
    if lang == "pt":
        return f"US$ {num(value, digits, lang)}"
    return f"{num(value, digits, lang)}{NNBSP}$"


def brl_bn(value: float, lang: str = "en") -> str:
    """Billions of reais; the sign is written by the sentence, not here."""

    amount = num(abs(value), 1, lang)
    return {"en": f"R${amount} bn", "pt": f"R$ {amount} bi", "fr": f"{amount}{NNBSP}Md R$"}[lang]


def rate_range(lower: float, upper: float, lang: str = "en") -> str:
    return f"{num(lower, 2, lang)}–{pct(upper, 2, lang)}"


MONTHS_LONG = {
    "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
    "pt": ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"),
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"),
}


def _parse(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def day(value: str | date, lang: str = "en", year: bool = True, long: bool = False) -> str:
    """'24 Sep 2026' in tables; long=True gives '24 September' / '24 de setembro' for prose."""

    parsed = _parse(value)
    if long:
        month = MONTHS_LONG[lang][parsed.month - 1]
        base = f"{parsed.day} de {month}" if lang == "pt" else f"{'1er' if lang == 'fr' and parsed.day == 1 else parsed.day} {month}"
        if year:
            return f"{base} de {parsed.year}" if lang == "pt" else f"{base} {parsed.year}"
        return base
    month = MONTHS[lang][parsed.month - 1]
    base = f"{parsed.day} {month}"
    return f"{base} {parsed.year}" if year else base


def period(value: str | date, frequency: str, lang: str = "en") -> str:
    parsed = _parse(value)
    if frequency.lower() == "monthly":
        names = {
            "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
            "pt": ("jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."),
            "fr": ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."),
        }[lang]
        return f"{names[parsed.month - 1]} {parsed.year}"
    if frequency.lower() == "quarterly":
        return f"{'Q' if lang == 'en' else 'T'}{(parsed.month - 1) // 3 + 1} {parsed.year}"
    return day(parsed, lang)


def timestamp(value: str, lang: str = "en") -> str:
    """ISO UTC timestamp -> '24 Sep 2026, 18:40 BRT'."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Sao_Paulo"))
    except (AttributeError, TypeError, ValueError):
        return "—"
    return f"{day(parsed.date(), lang)}, {parsed:%H:%M} BRT"
