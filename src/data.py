from __future__ import annotations

from datetime import date
from io import StringIO
from typing import Any, Mapping
from urllib.parse import quote, urlencode

import pandas as pd
import requests
import streamlit as st

BCB_EXPECTATIONS_URL = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
BCB_PTAX_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
BCB_SELIC_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json"
BCB_SGS_API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"
FRED_GRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES_URL = "https://fred.stlouisfed.org/series"
REQUEST_TIMEOUT = (3, 8)
HEADERS = {"User-Agent": "Brazil-Macro-Monitor/2.0"}

class DataSourceError(RuntimeError):
    pass

def _request_json(url: str, params: Mapping[str, str], source: str) -> Any:
    request_url = f"{url}?{urlencode(params, quote_via=quote)}"
    try:
        response = requests.get(request_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise DataSourceError(f"{source} request failed: {exc}") from exc

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
    if not rows: return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows); required = {"Indicador", "Data", "DataReferencia", "Mediana", "baseCalculo"}
    _require_columns(frame, required, "BCB Focus")
    frame = frame[list(required)].rename(columns={"Indicador":"Indicator","Data":"Date","DataReferencia":"Reference year","Mediana":"Median","baseCalculo":"Calculation base"})
    frame["Date"] = pd.to_datetime(frame["Date"], format="%Y-%m-%d", errors="coerce")
    for col in ("Reference year","Median","Calculation base"): frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.loc[(frame["Indicator"] == expected_indicator) & (frame["Calculation base"] == 0)].dropna(subset=["Date","Reference year","Median"])
    if frame.empty: raise DataSourceError("BCB Focus returned no usable observations.")
    frame["Reference year"] = frame["Reference year"].astype(int)
    return frame[columns].sort_values(["Reference year","Date"]).drop_duplicates(["Indicator","Date","Reference year"], keep="last").reset_index(drop=True)

def parse_ptax_response(payload: Any) -> pd.DataFrame:
    columns = ["Date","Timestamp","Buying rate","Selling rate","Midpoint"]
    rows = _odata_rows(payload, "BCB PTAX")
    if not rows: return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows); required = {"cotacaoCompra","cotacaoVenda","dataHoraCotacao"}; _require_columns(frame, required, "BCB PTAX")
    frame = frame[list(required)].rename(columns={"cotacaoCompra":"Buying rate","cotacaoVenda":"Selling rate","dataHoraCotacao":"Timestamp"})
    frame["Timestamp"] = pd.to_datetime(frame["Timestamp"], errors="coerce")
    frame["Buying rate"] = pd.to_numeric(frame["Buying rate"], errors="coerce"); frame["Selling rate"] = pd.to_numeric(frame["Selling rate"], errors="coerce")
    frame = frame.dropna(); frame["Date"] = frame["Timestamp"].dt.normalize(); frame["Midpoint"] = (frame["Buying rate"]+frame["Selling rate"])/2
    return frame[columns].sort_values(["Date","Timestamp"]).drop_duplicates("Date", keep="last").reset_index(drop=True)

def parse_sgs_response(payload: Any) -> pd.DataFrame:
    columns=["Date","Value"]
    if not isinstance(payload,list): raise DataSourceError("BCB SGS returned a malformed response.")
    if not payload: return pd.DataFrame(columns=columns)
    frame=pd.DataFrame(payload); _require_columns(frame,{"data","valor"},"BCB SGS")
    frame=frame[["data","valor"]].rename(columns={"data":"Date","valor":"Value"}); frame["Date"]=pd.to_datetime(frame["Date"],format="%d/%m/%Y",errors="coerce"); frame["Value"]=pd.to_numeric(frame["Value"].astype("string").str.replace(",",".",regex=False),errors="coerce")
    return frame.dropna().sort_values("Date").drop_duplicates("Date",keep="last").reset_index(drop=True)

def parse_fred_csv(text: str, series_id: str) -> pd.DataFrame:
    try: frame=pd.read_csv(StringIO(text))
    except Exception as exc: raise DataSourceError(f"FRED {series_id} returned malformed CSV.") from exc
    date_col = "observation_date" if "observation_date" in frame.columns else "DATE" if "DATE" in frame.columns else None
    if date_col is None: raise DataSourceError(f"FRED {series_id} response is missing a date field.")
    _require_columns(frame,{date_col,series_id},f"FRED {series_id}")
    frame=frame[[date_col,series_id]].rename(columns={date_col:"Date",series_id:"Value"}); frame["Date"]=pd.to_datetime(frame["Date"],errors="coerce"); frame["Value"]=pd.to_numeric(frame["Value"],errors="coerce")
    frame=frame.dropna();
    if frame.empty: raise DataSourceError(f"FRED {series_id} returned no usable observations.")
    return frame.sort_values("Date").drop_duplicates("Date",keep="last").reset_index(drop=True)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_focus_expectations(indicator: str, start_date: date) -> pd.DataFrame:
    if indicator not in {"Selic","IPCA"}: raise ValueError("Focus indicator must be 'Selic' or 'IPCA'.")
    url=f"{BCB_EXPECTATIONS_URL}ExpectativasMercadoAnuais"; params={"$format":"json","$select":"Indicador,Data,DataReferencia,Mediana,baseCalculo","$filter":f"Indicador eq '{indicator}' and Data ge '{start_date:%Y-%m-%d}' and baseCalculo eq 0","$orderby":"Data asc,DataReferencia asc","$top":"10000"}
    return parse_focus_response(_request_json(url,params,"BCB Focus"),indicator)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ptax(start_date: date, end_date: date) -> pd.DataFrame:
    url=f"{BCB_PTAX_URL}CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"; params={"@dataInicial":f"'{start_date:%m-%d-%Y}'","@dataFinalCotacao":f"'{end_date:%m-%d-%Y}'","$format":"json","$select":"cotacaoCompra,cotacaoVenda,dataHoraCotacao","$orderby":"dataHoraCotacao asc"}
    return parse_ptax_response(_request_json(url,params,"BCB PTAX"))

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_selic_target(start_date: date, end_date: date) -> pd.DataFrame:
    return parse_sgs_response(_request_json(BCB_SGS_API_URL,{"formato":"json","dataInicial":start_date.strftime("%d/%m/%Y"),"dataFinal":end_date.strftime("%d/%m/%Y")},"BCB SGS series 432"))

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred_series(series_id: str, start_date: date) -> pd.DataFrame:
    allowed={"DFEDTARL","DFEDTARU","DGS2","DGS10","DCOILBRENTEU","PIORECRUSDM","PSOYBUSDM","PSUGAISAUSDM"}
    if series_id not in allowed: raise ValueError(f"Unsupported FRED series: {series_id}.")
    try:
        response=requests.get(FRED_GRAPH_URL,params={"id":series_id,"cosd":start_date.strftime("%Y-%m-%d")},headers=HEADERS,timeout=REQUEST_TIMEOUT); response.raise_for_status()
    except requests.RequestException as exc: raise DataSourceError(f"FRED {series_id} request failed: {exc}") from exc
    return parse_fred_csv(response.text,series_id)
