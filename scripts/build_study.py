"""Compute the 6 October 2026 study from its frozen inputs and save the results.

    python scripts/build_study.py

Offline: reads ``research/study_inputs_2026-10-06.json`` (written by
``scripts/collect_study_inputs.py``) and ``research/thesis.json``, and writes
``research/study_2026-10-06.json``, which the page and the PDFs read.
``tests/test_study.py`` fails when the saved results no longer match the inputs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import study  # noqa: E402


def main() -> None:
    thesis = json.loads((ROOT / "research" / "thesis.json").read_text(encoding="utf-8"))
    inputs = json.loads((ROOT / thesis["study_inputs_file"]).read_text(encoding="utf-8"))
    results = study.build(inputs, thesis)
    target = ROOT / thesis["study_file"]
    target.write_text(json.dumps(results, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)} ({target.stat().st_size / 1024:.0f} kB)")


if __name__ == "__main__":
    main()
