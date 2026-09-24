#!/usr/bin/env python3
"""Refresh the checked-in production snapshot from official data sources.

Each source is validated on its own; failures keep the last good value and are
listed in the output and in the GitHub Actions step summary.  The script exits
0 even when a feed fails so that valid updates are still committed; the
separate ``scripts/check_freshness.py`` step turns the workflow red when data
becomes too old.
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

from src.live_refresh import refresh_payload  # noqa: E402


def load_existing(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def summary_lines(payload: dict) -> list[str]:
    refresh = payload.get("refresh", {})
    lines = [
        f"### Market-data refresh · {refresh.get('attempted_at', 'unknown')}",
        "",
        f"{refresh.get('sources_ok', 0)} of {refresh.get('sources_total', 0)} sources refreshed.",
        "",
        "| Source key | Status | Source used | Last success | Error |",
        "|---|---|---|---|---|",
    ]
    for key, item in sorted(refresh.get("sources", {}).items()):
        error = (item.get("error") or item.get("note") or "").replace("|", "/")
        lines.append(f"| {key} | {item.get('status')} | {item.get('source', '')} | {item.get('last_success') or 'never'} | {error[:160]} |")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "research" / "live_snapshot.json")
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    args = parser.parse_args()

    existing = load_existing(args.output)
    payload = refresh_payload(existing, args.as_of)
    rendered = json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(args.output)

    lines = summary_lines(payload)
    print("\n".join(lines))
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    for key, item in payload["refresh"]["sources"].items():
        if item["status"] != "ok":
            # GitHub annotation: visible on the run page without opening logs.
            print(f"::warning title=Source failed: {key}::{item.get('error', '')[:200]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
