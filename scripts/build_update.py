"""Reproduce the 16 October publication from frozen official inputs (offline)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.update import build_update


def main():
    snapshot = json.loads((ROOT / 'research/thesis_snapshot_2026-10-16.json').read_text())
    baseline = json.loads((ROOT / 'research/thesis_2026-10-06.json').read_text())
    report = build_update(snapshot, baseline)
    path = ROOT / 'research/update_2026-10-16.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(path)


if __name__ == '__main__':
    main()
