#!/usr/bin/env python3
"""Fast offline pre-release sanity checks.

Local PHP/JS/mypy/full-pytest runners can hang in some sandboxes, so this
script runs a quick, dependency-free set of invariants that catch the most
common release breakages (version drift, hardcoded version asserts, quality
rounding, broken data fixtures) in a couple of seconds.

Usage:
    python scripts/dev_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _check_version_sync() -> list[str]:
    from scripts.check_version_sync import main as version_main
    return [] if version_main() == 0 else ["check_version_sync failed"]


def _check_import_smoke() -> list[str]:
    import texthumanize as th
    problems = []
    for name in ("humanize", "quality_score_report", "audit_widget_html",
                 "benchmark_leaderboard", "watermark_eval", "load_bad_output_bank"):
        if not hasattr(th, name):
            problems.append(f"missing public export: {name}")
    return problems


def _check_quality_rounding() -> list[str]:
    from texthumanize import quality_score_report
    problems = []
    for n in range(1, 40):
        text = f"word{n} " * n + "This is a natural sentence here."
        report = quality_score_report(text, lang="en")
        if report["score_100"] != round(report["score"] * 100.0, 1):
            problems.append(f"score_100 mismatch at n={n}")
            break
    return problems


def _check_watermark_fixtures() -> list[str]:
    from texthumanize.quality_metrics import watermark_eval
    result = watermark_eval()
    problems = []
    if result["false_negative_rate"] > 0.0:
        problems.append(f"watermark FN rate {result['false_negative_rate']} > 0")
    if result["false_positive_rate"] > 0.0:
        problems.append(f"watermark FP rate {result['false_positive_rate']} > 0")
    return problems


def _check_bad_output_bank() -> list[str]:
    from texthumanize.bad_output_bank import validate_bad_output_bank
    try:
        validate_bad_output_bank()
    except Exception as exc:
        return [f"bad_output_bank invalid: {exc}"]
    return []


def _check_readme_counters() -> list[str]:
    """Catch drift between README's advertised counts and reality.

    Modules are counted exactly (cheap). Test count is collected via pytest;
    if collection is unavailable the test-count comparison is skipped rather
    than failing the whole guard.
    """
    import re
    import subprocess

    problems: list[str] = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    # Modules: cheap and exact. The authoritative count must appear verbatim.
    actual_modules = len(list((ROOT / "texthumanize").rglob("*.py")))
    if re.search(r"\d{2,4}\s+Python modules", readme) and \
            f"{actual_modules} Python modules" not in readme:
        problems.append(
            f"README Python-module count is stale; should be {actual_modules}"
        )

    # Tests: collect via pytest; skip if collection is unavailable.
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=180,
        ).stdout
        match = re.search(r"(\d+)\s+tests collected", out)
        if match and re.search(r"[\d,]{3,}\s+tests\b|tests-\d+", readme):
            actual_tests = int(match.group(1))
            if f"{actual_tests:,} tests" not in readme and f"tests-{actual_tests}" not in readme:
                problems.append(
                    f"README test count is stale or malformed; should be {actual_tests:,}"
                )
            # The shields Tests badge must be intact on one line (a stray
            # newline once split it as `tests-2269\n0\n41%20passed`).
            if "img.shields.io/badge/tests-" in readme and \
                    f"tests-{actual_tests}%20passed" not in readme:
                problems.append(
                    f"README Tests badge is malformed; expected tests-{actual_tests}%20passed"
                )
    except Exception:
        pass  # collection unavailable — skip the test-count comparison

    return problems


def main() -> int:
    checks = [
        ("version sync", _check_version_sync),
        ("import smoke", _check_import_smoke),
        ("quality rounding", _check_quality_rounding),
        ("watermark fixtures", _check_watermark_fixtures),
        ("bad output bank", _check_bad_output_bank),
        ("readme counters", _check_readme_counters),
    ]
    failed = False
    for name, fn in checks:
        problems = fn()
        if problems:
            failed = True
            print(f"✗ {name}")
            for problem in problems:
                print(f"   - {problem}")
        else:
            print(f"✓ {name}")
    if failed:
        print("\ndev_check FAILED")
        return 1
    print("\ndev_check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
