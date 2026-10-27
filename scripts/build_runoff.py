"""Reproduce the 27 October (post-runoff) publication from frozen inputs (offline)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.runoff import build_runoff


def main():
    read = lambda name: json.loads((ROOT / 'research' / name).read_text())
    report = build_runoff(read('thesis_snapshot_2026-10-27.json'), read('study_inputs_2026-10-06.json'),
                          read('thesis_2026-10-06.json'), read('update_2026-10-16.json'))
    path = ROOT / 'research/runoff_2026-10-27.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(path)


if __name__ == '__main__':
    main()
