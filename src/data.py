"""Official-source fetchers and parsers used only by the scheduled refresh job.

Nothing in this module is imported by the Streamlit page: visitors are served
from the saved snapshot in ``research/live_snapshot.json``.
"""
from __future__ import annotations

import time
from datetime import date
from io import StringIO
from typing import Any, Callable, Mapping
from urllib.parse import quote, urlencode

import pandas as pd
import requests

BCB_EXPECTATIONS_URL = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
BCB_PTAX_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
BCB_SELIC_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json"
BCB_SGS_API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"
FRED_GRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES_URL = "https://fred.stlouisfed.org/series"
TREASURY_CSV_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all"
)
TREASURY_PAGE_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "TextView?type=daily_treasury_yield_curve"
)
NYFED_EFFR_URL = "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/{count}.json"
NYFED_PAGE_URL = "https://www.newyorkfed.org/markets/reference-rates/effr"

# Connect / read timeouts. FRED is slow from some cloud networks, so the job
# retries instead of giving up on the first timeout.
REQUEST_TIMEOUT = (10, 30)
RETRIES = 3
HEADERS = {"User-Agent": "Brazil-Macro-Monitor/3.0 (+https://github.com/Midiansi/brazil-rates-fx-scenario-monitor)"}

FRED_SERIES = {
    "DFEDTARL", "DFEDTARU", "DGS2", "DGS10",
    "DCOILBRENTEU", "PIORECRUSDM", "PSOYBUSDM", "PSUGAISAUSDM",
}


class DataSourceError(RuntimeError):
    pass


def _get(url: str, source: str, **kwargs: Any) -> requests.Response:
    """GET with a small, bounded retry loop; raise a readable error at the end."""

    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last = exc
            if attempt + 1 < RETRIES:
                time.sleep(2 * (attempt + 1))
    raise DataSourceError(f"{source} request failed after {RETRIES} attempts: {last}")


def _request_json(url: str, params: Mapping[str, str], source: str) -> Any:
    request_url = f"{url}?{urlencode(params, quote_via=quote)}"
    try:
        return _get(request_url, source).json()
    except ValueError as exc:
        raise DataSourceError(f"{source} returned invalid JSON: {exc}") from exc


def _odata_rows(payload: Any, source: str) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping) or "value" not in payload or not isinstance(payload["value"], list):
        raise DataSourceError(f"{source} returned a malformed OData response.")
    return payload["value"]


def _require_columns(frame: pd.DataFrame, columns: set[str], source: str) -> None:
    missing = columns.difference(frame.columns)
    if missing:
        raise DataSourceError(f"{source} response is missing fields: {', '.join(sorted(missing))}.")


def parse_focus_response(payload: Any, expected_indicator: str) -> pd.DataFrame:
    columns = ["Indicator", "Date", "Reference year", "Median", "Calculation base"]
    rows = _odata_rows(payload, "BCB Focus")
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows)
    required = {"Indicador", "Data", "DataReferencia", "Mediana", "baseCalculo"}
    _require_columns(frame, required, "BCB Focus")
    frame = frame[list(required)].rename(columns={
        "Indicador": "Indicator", "Data": "Date", "DataReferencia": "Reference year",
        "Mediana": "Median", "baseCalculo": "Calculation base",
    })
    frame["Date"] = pd.to_datetime(frame["Date"], format="%Y-%m-%d", errors="coerce")
    for col in ("Reference year", "Median", "Calculation base"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.loc[(frame["Indicator"] == expected_indicator) & (frame["Calculation base"] == 0)]
    frame = frame.dropna(subset=["Date", "Reference year", "Median"])
    if frame.empty:
        raise DataSourceError("BCB Focus returned no usable observations.")
    frame["Reference year"] = frame["Reference year"].astype(int)
    return (
        frame[columns].sort_values(["Reference year", "Date"])
        .drop_duplicates(["Indicator", "Date", "Reference year"], keep="last").reset_index(drop=True)
    )


def parse_ptax_response(payload: Any) -> pd.DataFrame:
    columns = ["Date", "Timestamp", "Buying rate", "Selling rate", "Midpoint"]
    rows = _odata_rows(payload, "BCB PTAX")
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows)
    required = {"cotacaoCompra", "cotacaoVenda", "dataHoraCotacao"}
    _require_columns(frame, required, "BCB PTAX")
    frame = frame[list(required)].rename(columns={
        "cotacaoCompra": "Buying rate", "cotacaoVenda": "Selling rate", "dataHoraCotacao": "Timestamp",
    })
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame["Buying rate"] = pd.to_numeric(frame["Buying rate"], errors="coerce")
    frame["Selling rate"] = pd.to_numeric(frame["Selling rate"], errors="coerce")
    frame = frame.dropna()
    frame["Date"] = frame["Timestamp"].dt.normalize()
    frame["Midpoint"] = (frame["Buying rate"] + frame["Selling rate"]) / 2
    return frame[columns].sort_values(["Date", "Timestamp"]).drop_duplicates("Date", keep="last").reset_index(drop=True)


def parse_sgs_response(payload: Any) -> pd.DataFrame:
    columns = ["Date", "Value"]
    if not isinstance(payload, list):
        raise DataSourceError("BCB SGS returned a malformed response.")
    if not payload:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(payload)
    _require_columns(frame, {"data", "valor"}, "BCB SGS")
    frame = frame[["data", "valor"]].rename(columns={"data": "Date", "valor": "Value"})
    frame["Date"] = pd.to_datetime(frame["Date"], format="%d/%m/%Y", errors="coerce")
    frame["Value"] = pd.to_numeric(frame["Value"].astype("string").str.replace(",", ".", regex=False), errors="coerce")
    return frame.dropna().sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)


def parse_fred_csv(text: str, series_id: str) -> pd.DataFrame:
    try:
        frame = pd.read_csv(StringIO(text))
    except Exception as exc:
        raise DataSourceError(f"FRED {series_id} returned malformed CSV.") from exc
    date_col = "observation_date" if "observation_date" in frame.columns else "DATE" if "DATE" in frame.columns else None
    if date_col is None:
        raise DataSourceError(f"FRED {series_id} response is missing a date field.")
    _require_columns(frame, {date_col, series_id}, f"FRED {series_id}")
    frame = frame[[date_col, series_id]].rename(columns={date_col: "Date", series_id: "Value"})
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["Value"] = pd.to_numeric(frame["Value"], errors="coerce")
    frame = frame.dropna()
    if frame.empty:
        raise DataSourceError(f"FRED {series_id} returned no usable observations.")
    return frame.sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)


def parse_treasury_csv(text: str) -> pd.DataFrame:
    """Parse the U.S. Treasury daily par yield curve CSV into Date / 2y / 10y columns."""

    try:
        frame = pd.read_csv(StringIO(text))
    except Exception as exc:
        raise DataSourceError("U.S. Treasury returned malformed CSV.") from exc
    _require_columns(frame, {"Date", "2 Yr", "10 Yr"}, "U.S. Treasury")
    frame = frame[["Date", "2 Yr", "10 Yr"]].rename(columns={"2 Yr": "2y", "10 Yr": "10y"})
    frame["Date"] = pd.to_datetime(frame["Date"], format="%m/%d/%Y", errors="coerce")
    for column in ("2y", "10y"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna()
    if frame.empty:
        raise DataSourceError("U.S. Treasury returned no usable observations.")
    return frame.sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)


def parse_nyfed_effr(payload: Any) -> pd.DataFrame:
    """Parse the New York Fed EFFR feed, which also reports the FOMC target range."""

    rows = payload.get("refRates") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list) or not rows:
        raise DataSourceError("New York Fed returned a malformed EFFR response.")
    frame = pd.DataFrame(rows)
    _require_columns(frame, {"effectiveDate", "targetRateFrom", "targetRateTo", "percentRate"}, "New York Fed")
    frame = frame.rename(columns={
        "effectiveDate": "Date", "targetRateFrom": "Lower", "targetRateTo": "Upper", "percentRate": "EFFR",
    })[["Date", "Lower", "Upper", "EFFR"]]
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    for column in ("Lower", "Upper", "EFFR"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna()
    frame = frame.loc[frame["Upper"] > frame["Lower"]]
    if frame.empty:
        raise DataSourceError("New York Fed returned no usable target-range observations.")
    return frame.sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)


def fetch_focus_expectations(indicator: str, start_date: date) -> pd.DataFrame:
    if indicator not in {"Selic", "IPCA", "Câmbio"}:
        raise ValueError("Focus indicator must be 'Selic', 'IPCA' or 'Câmbio'.")
    url = f"{BCB_EXPECTATIONS_URL}ExpectativasMercadoAnuais"
    params = {
        "$format": "json",
        "$select": "Indicador,Data,DataReferencia,Mediana,baseCalculo",
        "$filter": f"Indicador eq '{indicator}' and Data ge '{start_date:%Y-%m-%d}' and baseCalculo eq 0",
        "$orderby": "Data asc,DataReferencia asc",
        "$top": "10000",
    }
    return parse_focus_response(_request_json(url, params, "BCB Focus"), indicator)


def fetch_ptax(start_date: date, end_date: date) -> pd.DataFrame:
    url = f"{BCB_PTAX_URL}CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
    params = {
        "@dataInicial": f"'{start_date:%m-%d-%Y}'",
        "@dataFinalCotacao": f"'{end_date:%m-%d-%Y}'",
        "$format": "json",
        "$select": "cotacaoCompra,cotacaoVenda,dataHoraCotacao",
        "$orderby": "dataHoraCotacao asc",
    }
    return parse_ptax_response(_request_json(url, params, "BCB PTAX"))


def fetch_selic_target(start_date: date, end_date: date) -> pd.DataFrame:
    params = {"formato": "json", "dataInicial": start_date.strftime("%d/%m/%Y"), "dataFinal": end_date.strftime("%d/%m/%Y")}
    return parse_sgs_response(_request_json(BCB_SGS_API_URL, params, "BCB SGS series 432"))


def fetch_fred_series(series_id: str, start_date: date) -> pd.DataFrame:
    if series_id not in FRED_SERIES:
        raise ValueError(f"Unsupported FRED series: {series_id}.")
    response = _get(FRED_GRAPH_URL, f"FRED {series_id}", params={"id": series_id, "cosd": start_date.strftime("%Y-%m-%d")})
    return parse_fred_csv(response.text, series_id)


def fetch_treasury_yields(start_date: date, end_date: date) -> pd.DataFrame:
    frames = []
    for year in range(start_date.year, end_date.year + 1):
        url = TREASURY_CSV_URL.format(year=year)
        params = {"type": "daily_treasury_yield_curve", "field_tdr_date_value": str(year), "_format": "csv"}
        frames.append(parse_treasury_csv(_get(url, "U.S. Treasury", params=params).text))
    frame = pd.concat(frames, ignore_index=True)
    frame = frame.loc[frame["Date"] >= pd.Timestamp(start_date)]
    return frame.sort_values("Date").drop_duplicates("Date", keep="last").reset_index(drop=True)


def fetch_nyfed_target_range(count: int = 60) -> pd.DataFrame:
    return parse_nyfed_effr(_get(NYFED_EFFR_URL.format(count=count), "New York Fed").json())


def first_success(loaders: list[tuple[str, Callable[[], pd.DataFrame]]]) -> tuple[str, pd.DataFrame, list[str]]:
    """Try alternative official sources in order; return the first usable frame."""

    errors: list[str] = []
    for name, loader in loaders:
        try:
            frame = loader()
            if frame is None or frame.empty:
                raise DataSourceError(f"{name} returned no usable observations")
            return name, frame, errors
        except Exception as exc:  # external-service boundary in a scheduled job
            errors.append(f"{name}: {exc}")
    raise DataSourceError("; ".join(errors) or "no source configured")
