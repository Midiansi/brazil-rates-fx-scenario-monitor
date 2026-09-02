import json
from pathlib import Path

from src.portfolio import commodity_rows, commodity_synthesis, load_json, local_market_frames, market_brief
from src.research import load_research_snapshot


def test_local_first_snapshot_builds_without_network():
    research = load_research_snapshot(Path("research/data_snapshot.json"))
    frames = local_market_frames(research)
    assert set(frames) == {"focus_selic", "focus_ipca", "ptax", "selic_target", "fed_lower", "fed_upper", "us_2y", "us_10y"}
    assert all(not frames[key].empty for key in frames)
    assert frames["ptax"].iloc[-1]["Midpoint"] > 0


def test_market_brief_is_concise_and_plain_language():
    research = load_research_snapshot(Path("research/data_snapshot.json"))
    commodities = load_json(Path("research/commodity_snapshot.json"))
    brief = market_brief(research, commodities)
    assert [label for label, _ in brief] == ["Rates", "Currency", "Inflation", "Commodities"]
    assert all(len(copy) < 260 for _, copy in brief)
    assert not any("2s10s" in copy for _, copy in brief)


def test_commodity_snapshot_has_dates_frequency_and_sources():
    snapshot = load_json(Path("research/commodity_snapshot.json"))
    rows = commodity_rows(snapshot)
    assert len(rows) == 4
    assert all(row["latest_date"] and row["frequency"] and row["source_url"] for row in rows)
    assert len(commodity_synthesis(snapshot)) == 4


def test_commodity_snapshot_is_valid_json():
    with Path("research/commodity_snapshot.json").open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert "commodities" in payload
