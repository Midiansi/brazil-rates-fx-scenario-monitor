"""Collect the raw inputs of the 6 October 2026 study and freeze them in one file.

Network access is needed here and only here: ``src/study.py`` and the tests read
the saved file, so every figure on the page can be recomputed offline.

    python scripts/collect_study_inputs.py            # writes research/study_inputs_2026-10-06.json

Sources (all public): BCB PTAX (OData), ANBIMA ETTJ (CSV download; ANBIMA keeps
only the most recent weeks), IMF monthly commodity prices via FRED, UN Comtrade
(Brazil's exports as reported by Brazil, HS 4-digit) and the BCB Focus survey.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "research" / "study_inputs_2026-10-06.json"
HEADERS = {"User-Agent": "Brazil-Macro-Monitor/3.0 (+https://github.com/Midiansi/brazil-rates-fx-scenario-monitor)"}
PTAX_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
ANBIMA_URL = "https://www.anbima.com.br/informacoes/est-termo/CZ-down.asp"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
COMTRADE_URL = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
FOCUS_URL = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"

FIRST_DAY, LAST_DAY = date(2002, 1, 2), date(2026, 10, 5)
FRED_MONTHLY = {
    "brent": "POILBREUSDM", "soybeans": "PSOYBUSDM", "sugar": "PSUGAISAUSDM",
    "iron_ore": "PIORECRUSDM", "coffee": "PCOFFOTMUSDM", "maize": "PMAIZMTUSDM",
}
# HS 4-digit codes of the six commodities that have a clean monthly benchmark.
HS_CODES = {"brent": "2709", "soybeans": "1201", "iron_ore": "2601", "coffee": "0901", "sugar": "1701", "maize": "1005"}
ANBIMA_DATES = ("2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18", "2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24",
                "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02", "2026-10-05")


def get(url: str, **kwargs):
    last = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=(10, 60), **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise SystemExit(f"{url} failed: {last}")


def collect_ptax() -> list[list]:
    """Daily PTAX midpoint (average of the buying and selling rates), 2002 to 5 Oct 2026."""

    rows: dict[str, float] = {}
    start = FIRST_DAY
    while start <= LAST_DAY:
        end = min(date(start.year + 3, 12, 31), LAST_DAY)
        params = {"@dataInicial": f"'{start:%m-%d-%Y}'", "@dataFinalCotacao": f"'{end:%m-%d-%Y}'", "$format": "json", "$top": "5000"}
        for item in get(PTAX_URL, params=params).json()["value"]:
            rows[item["dataHoraCotacao"][:10]] = round((item["cotacaoCompra"] + item["cotacaoVenda"]) / 2, 5)
        start = end + timedelta(days=1)
    return [[d, rows[d]] for d in sorted(rows)]


def collect_fred_monthly() -> dict[str, list]:
    out = {}
    for key, series in FRED_MONTHLY.items():
        text = get(FRED_URL, params={"id": series}).text.strip().splitlines()[1:]
        out[key] = [[line.split(",")[0], round(float(line.split(",")[1]), 4)] for line in text
                    if line.split(",")[1] not in ("", ".") and line.split(",")[0] >= "2002-01-01"]
    return out


def parse_ettj(text: str) -> dict:
    """Pre-fixed zero curve (vertices in business days) and implied inflation from an ANBIMA CSV."""

    text = text.replace("\r", "")
    curve = re.search(r"PREFIXADOS \(CIRCULAR 3\.361\)\nVertices;Taxa \(%a\.a\.\)\n(.*?)\n\n", text, re.S)
    implied = re.search(r"Vertices;ETTJ IPCA;ETTJ PREF;Infla.*?\n(.*?)\n\n", text, re.S)
    if not curve:
        return {}

    def number(value: str) -> float:
        return float(value.replace(".", "").replace(",", "."))

    out = {"fixed_rate": {line.split(";")[0].replace(".", ""): number(line.split(";")[1]) for line in curve.group(1).split("\n")}}
    if implied:
        breakeven, real = {}, {}
        for line in implied.group(1).split("\n"):
            parts = line.split(";")
            if len(parts) >= 4 and parts[3]:
                vertex = parts[0].replace(".", "")
                breakeven[vertex], real[vertex] = number(parts[3]), number(parts[1])
        out["implied_inflation"], out["real_rate"] = breakeven, real
    return out


def collect_anbima() -> dict[str, dict]:
    out = {}
    for iso in ANBIMA_DATES:
        day = date.fromisoformat(iso)
        response = requests.post(ANBIMA_URL, data={"Idioma": "PT", "Dt_Ref": f"{day:%d/%m/%Y}", "saida": "csv"}, headers=HEADERS, timeout=40)
        parsed = parse_ettj(response.content.decode("latin-1")) if response.content else {}
        if parsed:
            out[iso] = parsed
        time.sleep(0.5)
    return out


def collect_exports(year: str = "2025") -> dict:
    values = {}
    codes = ["TOTAL"] + list(HS_CODES.values())
    response = get(COMTRADE_URL, params={
        "reporterCode": "76", "period": year, "partnerCode": "0", "cmdCode": ",".join(codes), "flowCode": "X",
        "partner2Code": "0", "customsCode": "C00", "motCode": "0"})
    for row in response.json()["data"]:
        values[row["cmdCode"]] = row["primaryValue"]
    total = values.pop("TOTAL")
    return {"year": int(year), "total_usd": total, "usd": {key: values[code] for key, code in HS_CODES.items()},
            "hs": HS_CODES, "source": "UN Comtrade, Brazil as reporter, goods exports to the world, FOB value"}


def main() -> None:
    inputs = {
        "schema_version": 1,
        "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Raw inputs of the 6 October 2026 study, frozen so every figure can be recomputed offline (src/study.py, tests/test_study.py).",
        "ptax": collect_ptax(),
        "commodities_monthly": collect_fred_monthly(),
        "anbima_ettj": collect_anbima(),
        "exports": collect_exports(),
    }
    OUTPUT.write_text(json.dumps(inputs, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    ptax = inputs["ptax"]
    print(f"PTAX {len(ptax)} closes {ptax[0][0]} -> {ptax[-1][0]}; ANBIMA dates {sorted(inputs['anbima_ettj'])[:1]}..{sorted(inputs['anbima_ettj'])[-1:]} "
          f"({len(inputs['anbima_ettj'])}); monthly series {[(k, len(v)) for k, v in inputs['commodities_monthly'].items()]}")
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size / 1024:.0f} kB)")


if __name__ == "__main__":
    sys.exit(main())
