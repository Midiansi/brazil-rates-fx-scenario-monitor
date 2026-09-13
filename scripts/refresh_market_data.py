#!/usr/bin/env python3
"""Refresh the checked-in production snapshot from official data sources."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.live_refresh import refresh_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "research" / "live_snapshot.json")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    try:
        existing = json.loads(args.output.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        # Bootstrap from the reviewed case so a first-run outage can never
        # replace the dashboard with a partial or empty file.
        try:
            research = json.loads((PROJECT_ROOT / "research" / "data_snapshot.json").read_text(encoding="utf-8"))
            commodities = json.loads((PROJECT_ROOT / "research" / "commodity_snapshot.json").read_text(encoding="utf-8"))
            existing = {
                "updated_at": research.get("retrieved_at"),
                "series": research.get("series", {}),
                "commodities": commodities.get("commodities", {}),
            }
        except (OSError, json.JSONDecodeError):
            existing = {}
    payload = refresh_payload(existing, args.as_of)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output.exists() and args.output.read_text(encoding="utf-8") == rendered:
        print("No newer official observations; snapshot unchanged.")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(args.output)
    print(f"Updated {args.output}")
    if payload.get("source_failures"):
        print("Retained last-good values for: " + ", ".join(payload["source_failures"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
