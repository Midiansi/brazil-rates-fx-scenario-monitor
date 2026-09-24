#!/usr/bin/env python3
"""Fail loudly when the production snapshot is too old.

Run after the refresh job.  Exits 1 if a critical series (PTAX, Selic target,
Fed target range, U.S. two-year yield) is stale or if the last refresh attempt
is more than four days old, so GitHub marks the scheduled run as failed and
notifies the repository owner instead of reporting a green run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.freshness import CRITICAL, age_days, run_age_days, status  # noqa: E402

MAX_RUN_AGE_DAYS = 4


def evaluate(payload: dict, today: date) -> tuple[list[str], list[str]]:
    rows: list[str] = []
    problems: list[str] = []
    series = payload.get("series") or {}
    for key, item in sorted(series.items()):
        observed = item.get("latest_observation_date")
        state = status(observed, item.get("frequency", "daily"), today)
        rows.append(f"| {key} | {observed} | {age_days(observed, today)} | {state} |")
        if key in CRITICAL and state == "stale":
            problems.append(f"{key} is stale (last observation {observed}).")
    for key in CRITICAL:
        if key not in series:
            problems.append(f"{key} is missing from the snapshot.")
    for key, item in sorted((payload.get("commodities") or {}).items()):
        observed = item.get("latest_date")
        rows.append(f"| {key} | {observed} | {age_days(observed, today)} | {status(observed, item.get('frequency', 'daily'), today)} |")
    run_age = run_age_days((payload.get("refresh") or {}).get("attempted_at"), today)
    if run_age is None or run_age > MAX_RUN_AGE_DAYS:
        problems.append(f"Last refresh attempt is {run_age} days old.")
    return rows, problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, default=PROJECT_ROOT / "research" / "live_snapshot.json")
    parser.add_argument("--today", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    args = parser.parse_args()
    try:
        payload = json.loads(args.snapshot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"::error title=Snapshot unreadable::{exc}")
        return 1
    rows, problems = evaluate(payload, args.today)
    lines = ["### Freshness check", "", "| Series | Observation | Age (days) | Status |", "|---|---|---|---|", *rows, ""]
    lines += [f"- {problem}" for problem in problems] or ["All critical series are fresh."]
    print("\n".join(lines))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    for problem in problems:
        print(f"::error title=Stale market data::{problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
