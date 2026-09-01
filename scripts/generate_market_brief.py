from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.brief import generate_market_brief


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the saved one-page Brazil Rates & FX Trade Brief."
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=PROJECT_ROOT / "research" / "data_snapshot.json",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "Brazil_Rates_FX_Trade_Brief.pdf",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=PROJECT_ROOT / "research" / "market_brief.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_market_brief(args.snapshot, args.pdf, args.markdown)
    print(f"Generated {args.pdf}")
    print(f"Generated {args.markdown}")


if __name__ == "__main__":
    main()
