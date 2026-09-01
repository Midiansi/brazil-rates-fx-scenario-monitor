from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping


SCENARIO_NAMES = (
    "Hawkish relative to expectations",
    "Base case",
    "Dovish relative to expectations",
)

SCENARIO_REQUIRED_FIELDS = (
    "name",
    "copom_outcome_and_guidance",
    "fomc_outcome_and_guidance",
    "difference_from_current_expectations",
    "expected_initial_brl_usd_direction",
    "expected_initial_brazil_front_end_rates_direction",
    "expected_initial_us_2y_direction",
    "expected_brazil_us_differential_change",
    "confirmation_signals",
    "principal_risk",
    "brief_summary",
)

BRIEF_SCENARIO_FIELDS = (
    "copom",
    "fomc",
    "differential",
    "brl_usd_pressure",
    "confirmation",
)

TRADE_REQUIRED_FIELDS = (
    "direction",
    "thesis",
    "supporting_evidence",
    "catalyst",
    "entry_logic",
    "latest_ptax_reference",
    "invalidation_condition",
    "profit_taking_logic",
    "expected_holding_period",
    "principal_risks",
    "brief_principal_risks",
    "view_change_evidence",
    "supporting_scenario",
    "invalidating_scenario",
    "disclaimer",
)


class ResearchDataError(ValueError):
    """Raised when the saved, reviewable research package is unavailable or invalid."""


def _is_populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return True


def _parse_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str):
        raise ResearchDataError(f"{field} must be an ISO timestamp.")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResearchDataError(f"{field} is not a valid ISO timestamp.") from exc


def _parse_date(value: Any, field: str) -> None:
    if not isinstance(value, str):
        raise ResearchDataError(f"{field} must be an ISO date.")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ResearchDataError(f"{field} is not a valid ISO date.") from exc


def _require_https_url(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.startswith("https://"):
        raise ResearchDataError(f"{field} must contain a direct HTTPS source URL.")


def validate_research_snapshot(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ResearchDataError("Research snapshot must be a JSON object.")

    snapshot = dict(payload)
    _parse_timestamp(snapshot.get("retrieved_at"), "retrieved_at")

    audit = snapshot.get("scenario_label_audit")
    if not isinstance(audit, Mapping):
        raise ResearchDataError("Research snapshot must contain a scenario-label audit.")
    _parse_timestamp(audit.get("audited_at"), "scenario_label_audit.audited_at")
    if not isinstance(audit.get("current_meeting_specific_pricing_obtained"), bool):
        raise ResearchDataError("Scenario-label audit must state whether current pricing was obtained.")
    for authority in ("fomc", "copom"):
        pricing = audit.get(authority)
        if not isinstance(pricing, Mapping):
            raise ResearchDataError(f"Scenario-label audit is missing '{authority}' pricing.")
        _require_https_url(pricing.get("source_url"), f"scenario_label_audit.{authority}.source_url")
        _require_https_url(
            pricing.get("methodology_url"),
            f"scenario_label_audit.{authority}.methodology_url",
        )
        if not _is_populated(pricing.get("methodology")) or not _is_populated(
            pricing.get("staleness_note")
        ):
            raise ResearchDataError(
                f"Scenario-label audit '{authority}' pricing needs methodology and staleness notes."
            )
    _parse_timestamp(audit["fomc"].get("pricing_timestamp"), "scenario_label_audit.fomc.pricing_timestamp")
    _parse_date(audit["copom"].get("pricing_date"), "scenario_label_audit.copom.pricing_date")

    scenarios = snapshot.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 3:
        raise ResearchDataError("Research snapshot must contain exactly three scenarios.")
    names = []
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, Mapping):
            raise ResearchDataError(f"Scenario {index + 1} must be an object.")
        for field in SCENARIO_REQUIRED_FIELDS:
            if field not in scenario or not _is_populated(scenario[field]):
                raise ResearchDataError(f"Scenario {index + 1} is missing populated field '{field}'.")
        signals = scenario["confirmation_signals"]
        if not isinstance(signals, list) or len(signals) != 2 or not all(
            isinstance(signal, str) and signal.strip() for signal in signals
        ):
            raise ResearchDataError(f"Scenario {index + 1} must have exactly two confirmation signals.")
        brief_summary = scenario["brief_summary"]
        if not isinstance(brief_summary, Mapping) or any(
            not _is_populated(brief_summary.get(field)) for field in BRIEF_SCENARIO_FIELDS
        ):
            raise ResearchDataError(
                f"Scenario {index + 1} must contain a populated compact brief summary."
            )
        names.append(scenario["name"])
    if tuple(names) != SCENARIO_NAMES:
        raise ResearchDataError("Scenario names or ordering do not match the required framework.")

    trades = snapshot.get("paper_trades")
    if not isinstance(trades, list) or len(trades) != 1:
        raise ResearchDataError("Research snapshot must contain exactly one paper trade.")
    trade = trades[0]
    if not isinstance(trade, Mapping):
        raise ResearchDataError("Paper trade must be an object.")
    for field in TRADE_REQUIRED_FIELDS:
        if field not in trade or not _is_populated(trade[field]):
            raise ResearchDataError(f"Paper trade is missing populated field '{field}'.")
    for field in ("supporting_scenario", "invalidating_scenario"):
        if trade[field] not in names:
            raise ResearchDataError(f"Paper trade field '{field}' must name a valid scenario.")
    if trade["entry_logic"].strip() == trade["invalidation_condition"].strip():
        raise ResearchDataError("Paper-trade entry and invalidation conditions must differ.")
    if not isinstance(trade["supporting_evidence"], list) or len(trade["supporting_evidence"]) < 3:
        raise ResearchDataError("Paper trade must cite at least three supporting dashboard indicators.")
    if not isinstance(trade["principal_risks"], list) or len(trade["principal_risks"]) != 3:
        raise ResearchDataError("Paper trade must contain exactly three principal risks.")
    if not isinstance(trade["brief_principal_risks"], list) or len(
        trade["brief_principal_risks"]
    ) != 3:
        raise ResearchDataError("Paper trade must contain exactly three compact brief risks.")

    ptax_reference = trade["latest_ptax_reference"]
    if not isinstance(ptax_reference, Mapping):
        raise ResearchDataError("Paper trade PTAX reference must be an object.")
    _parse_date(ptax_reference.get("observation_date"), "latest_ptax_reference.observation_date")
    _parse_timestamp(
        ptax_reference.get("observation_timestamp"),
        "latest_ptax_reference.observation_timestamp",
    )

    series = snapshot.get("series")
    if not isinstance(series, Mapping) or not series:
        raise ResearchDataError("Research snapshot must contain timestamped source series.")
    for key, item in series.items():
        if not isinstance(item, Mapping):
            raise ResearchDataError(f"Series '{key}' must be an object.")
        _parse_date(item.get("latest_observation_date"), f"series.{key}.latest_observation_date")
        source_urls = [value for field, value in item.items() if field.endswith("source_url")]
        if not source_urls:
            raise ResearchDataError(f"Series '{key}' must contain at least one source URL.")
        for source_index, url in enumerate(source_urls):
            _require_https_url(url, f"series.{key}.source_url[{source_index}]")
        if "is_stale_at_retrieval" not in item or not isinstance(
            item["is_stale_at_retrieval"], bool
        ):
            raise ResearchDataError(f"Series '{key}' must state whether it was stale at retrieval.")

    sources = snapshot.get("source_registry")
    if not isinstance(sources, list) or not sources:
        raise ResearchDataError("Research snapshot must contain direct official sources.")
    for index, source in enumerate(sources):
        if not isinstance(source, Mapping) or not _is_populated(source.get("label")):
            raise ResearchDataError(f"Source {index + 1} is malformed.")
        _require_https_url(source.get("url"), f"source_registry[{index}].url")

    return snapshot


def load_research_snapshot(path: str | Path) -> dict[str, Any]:
    research_path = Path(path)
    try:
        with research_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise ResearchDataError(f"Research file not found: {research_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ResearchDataError(f"Research file could not be read: {research_path}") from exc
    return validate_research_snapshot(payload)
