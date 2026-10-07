"""Build the 7 October risk diagnostic and per-day CSV from frozen data, offline.

Run from the repository root: python scripts/build_risk.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import risk  # noqa: E402


def main() -> None:
    input_path = ROOT / "research" / "study_inputs_2026-10-06.json"
    raw = input_path.read_bytes()
    report = risk.build(json.loads(raw))
    report["input_sha256"] = hashlib.sha256(raw).hexdigest()
    output = ROOT / "research" / "risk_2026-10-07.json"
    summary = {key: value for key, value in report.items() if key != "timeline"}
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "research" / "risk_forecasts.csv").write_text(risk.forecast_csv(report), encoding="utf-8")
    print(f"Saved {report['evaluation']['n']} trailing forecasts per model through {report['data_as_of']}.")
    for model in report["models"]:
        print(f"{model['label']}: {model['breaches']} breaches ({model['breach_rate_pct']:.2f}%), Kupiec p={model['kupiec_p']:.4f}")


if __name__ == "__main__":
    main()
