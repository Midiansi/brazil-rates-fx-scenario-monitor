"""Freshness rules shared by the page, the refresh job and the CI gate."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from datetime import date

import pytest

from scripts.check_freshness import evaluate
from src.freshness import status

from conftest import ROOT, THESIS_DATE


@pytest.mark.parametrize(
    ("observed", "frequency", "expected"),
    [
        ("2026-09-24", "daily", "fresh"),
        ("2026-09-19", "daily", "delayed"),   # a long weekend
        ("2026-09-10", "daily", "stale"),
        ("2026-09-18", "weekly", "fresh"),
        ("2026-09-10", "weekly", "delayed"),
        ("2026-07-01", "monthly", "fresh"),    # IMF prices lag by design
        ("2026-05-01", "monthly", "stale"),
        (None, "daily", "unknown"),
        ("not-a-date", "daily", "unknown"),
    ],
)
def test_status_depends_on_frequency(observed, frequency, expected) -> None:
    assert status(observed, frequency, THESIS_DATE) == expected


def test_gate_passes_on_the_thesis_snapshot(frozen) -> None:
    rows, problems = evaluate(frozen, THESIS_DATE)
    assert problems == []
    assert len(rows) >= 13


def test_gate_fails_when_critical_data_is_stale(frozen) -> None:
    stale = copy.deepcopy(frozen)
    stale["series"]["ptax_usd_brl_midpoint"]["latest_observation_date"] = "2026-09-01"
    _, problems = evaluate(stale, THESIS_DATE)
    assert any("ptax_usd_brl_midpoint is stale" in problem for problem in problems)


def test_gate_fails_when_the_job_stops_running(frozen) -> None:
    _, problems = evaluate(frozen, date(2026, 10, 2))
    assert any("refresh attempt" in problem for problem in problems)


def test_gate_fails_when_a_critical_series_is_missing(frozen) -> None:
    missing = copy.deepcopy(frozen)
    del missing["series"]["fed_target_range"]
    _, problems = evaluate(missing, THESIS_DATE)
    assert "fed_target_range is missing from the snapshot." in problems


def test_gate_script_exit_codes(tmp_path, frozen) -> None:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(frozen), encoding="utf-8")
    ok = subprocess.run([sys.executable, "scripts/check_freshness.py", "--snapshot", str(path), "--today", "2026-09-24"], cwd=ROOT, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    late = subprocess.run([sys.executable, "scripts/check_freshness.py", "--snapshot", str(path), "--today", "2026-10-15"], cwd=ROOT, capture_output=True, text=True)
    assert late.returncode == 1
    assert "::error" in late.stdout
