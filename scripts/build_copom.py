"""Reproduce the 5 November (post-Copom) publication from frozen inputs (offline)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.copom import build_copom


def main():
    read = lambda name: json.loads((ROOT / 'research' / name).read_text())
    report = build_copom(read('thesis_snapshot_2026-11-05.json'), read('study_2026-10-06.json'), read('runoff_2026-10-27.json'))
    path = ROOT / 'research/copom_2026-11-05.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(path)


if __name__ == '__main__':
    main()
