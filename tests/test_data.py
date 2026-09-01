import pandas as pd
import pytest

from src.data import (
    DataSourceError,
    parse_focus_response,
    parse_fred_csv,
    parse_ptax_response,
    parse_sgs_response,
)
from src import data as data_module


@pytest.mark.parametrize(
    ("parser", "payload"),
    [
        (lambda payload: parse_focus_response(payload, "Selic"), {"value": []}),
        (parse_ptax_response, {"value": []}),
        (parse_sgs_response, []),
    ],
)
def test_empty_api_responses_return_empty_frames(parser, payload) -> None:
    assert parser(payload).empty


@pytest.mark.parametrize(
    ("parser", "payload"),
    [
        (lambda payload: parse_focus_response(payload, "Selic"), {}),
        (parse_ptax_response, {"value": "not-a-list"}),
        (parse_sgs_response, {"data": "not-a-list"}),
    ],
)
def test_malformed_api_responses_raise_readable_error(parser, payload) -> None:
    with pytest.raises(DataSourceError):
        parser(payload)


def test_focus_parser_converts_fields_and_filters_calculation_base() -> None:
    payload = {
        "value": [
            {
                "Indicador": "Selic",
                "Data": "2026-08-28",
                "DataReferencia": "2027",
                "Mediana": "12.00",
                "baseCalculo": 0,
            },
            {
                "Indicador": "Selic",
                "Data": "2026-08-28",
                "DataReferencia": "2027",
                "Mediana": "99.00",
                "baseCalculo": 1,
            },
        ]
    }
    frame = parse_focus_response(payload, "Selic")
    assert len(frame) == 1
    assert frame.iloc[0]["Median"] == 12.0
    assert pd.api.types.is_datetime64_any_dtype(frame["Date"])


def test_ptax_parser_calculates_midpoint_and_uses_latest_daily_quote() -> None:
    payload = {
        "value": [
            {
                "cotacaoCompra": "5.0000",
                "cotacaoVenda": "5.0200",
                "dataHoraCotacao": "2026-08-28 12:00:00",
            },
            {
                "cotacaoCompra": "5.0100",
                "cotacaoVenda": "5.0300",
                "dataHoraCotacao": "2026-08-28 13:00:00",
            },
        ]
    }
    frame = parse_ptax_response(payload)
    assert len(frame) == 1
    assert frame.iloc[0]["Midpoint"] == pytest.approx(5.02)


def test_fred_parser_handles_missing_values() -> None:
    text = "observation_date,DGS2\n2026-08-27,.\n2026-08-28,4.34\n"
    frame = parse_fred_csv(text, "DGS2")
    assert len(frame) == 1
    assert frame.iloc[0]["Value"] == 4.34


def test_bcb_request_uses_percent_encoded_spaces(monkeypatch) -> None:
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"value": []}

    def fake_get(url, **kwargs):
        captured["url"] = url
        return Response()

    monkeypatch.setattr(data_module.requests, "get", fake_get)
    result = data_module._request_json(
        "https://example.test/odata", {"$filter": "Indicador eq 'Selic'"}, "test"
    )

    assert result == {"value": []}
    assert "%20" in captured["url"]
    assert "+" not in captured["url"]
