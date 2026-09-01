from datetime import date, datetime
from pathlib import Path

from src.research import (
    SCENARIO_NAMES,
    SCENARIO_REQUIRED_FIELDS,
    TRADE_REQUIRED_FIELDS,
    load_research_snapshot,
)


RESEARCH_PATH = Path("research/data_snapshot.json")


def test_all_three_scenarios_are_present_in_required_order() -> None:
    snapshot = load_research_snapshot(RESEARCH_PATH)
    scenarios = snapshot["scenarios"]

    assert len(scenarios) == 3
    assert tuple(scenario["name"] for scenario in scenarios) == SCENARIO_NAMES


def test_every_required_scenario_field_is_populated() -> None:
    snapshot = load_research_snapshot(RESEARCH_PATH)

    for scenario in snapshot["scenarios"]:
        for field in SCENARIO_REQUIRED_FIELDS:
            assert field in scenario
            assert scenario[field]
        assert len(scenario["confirmation_signals"]) == 2


def test_exactly_one_trade_references_valid_scenarios() -> None:
    snapshot = load_research_snapshot(RESEARCH_PATH)
    trades = snapshot["paper_trades"]
    scenario_names = {scenario["name"] for scenario in snapshot["scenarios"]}

    assert len(trades) == 1
    trade = trades[0]
    for field in TRADE_REQUIRED_FIELDS:
        assert field in trade
        assert trade[field]
    assert trade["supporting_scenario"] in scenario_names
    assert trade["invalidating_scenario"] in scenario_names
    assert trade["entry_logic"] != trade["invalidation_condition"]


def test_data_snapshot_contains_timestamps_and_direct_source_urls() -> None:
    snapshot = load_research_snapshot(RESEARCH_PATH)
    datetime.fromisoformat(snapshot["retrieved_at"].replace("Z", "+00:00"))
    datetime.fromisoformat(
        snapshot["refresh_status"]["completed_at"].replace("Z", "+00:00")
    )
    assert isinstance(snapshot["refresh_status"]["source_failures"], list)
    assert isinstance(snapshot["refresh_status"]["stale_series"], list)

    for series in snapshot["series"].values():
        date.fromisoformat(series["latest_observation_date"])
        urls = [value for key, value in series.items() if key.endswith("source_url")]
        assert urls
        assert all(url.startswith("https://") for url in urls)
        assert isinstance(series["is_stale_at_retrieval"], bool)

    assert snapshot["source_registry"]
    assert all(source["url"].startswith("https://") for source in snapshot["source_registry"])
