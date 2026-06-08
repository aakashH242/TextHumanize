"""Tests for the unified TextHumanize Quality Score.

Covers ``texthumanize.quality_score_report`` and its CLI surface
(``texthumanize quality`` subcommand and the ``--quality-score`` flag).
"""

from __future__ import annotations

import json
import subprocess
import sys

import texthumanize as th
from texthumanize.core import (
    _change_balance_quality,
    _quality_grade,
    _quality_verdict,
    _readability_quality,
    _text_similarity,
    quality_score_report,
)


class TestQualityScoreReport:
    """Public ``quality_score_report`` contract."""

    SAMPLE = (
        "This guide walks you through the setup in a few short steps. "
        "You install the package, point it at your text, and read the score. "
        "Most people get a useful result on the first try."
    )

    def test_public_export(self) -> None:
        assert th.quality_score_report is quality_score_report
        assert "quality_score_report" in th.__all__

    def test_schema_and_bounds(self) -> None:
        report = quality_score_report(self.SAMPLE, lang="en")
        assert report["schema_version"] == "text-humanize.quality_score.v1"
        assert 0.0 <= report["score"] <= 1.0
        assert report["score_100"] == round(report["score"] * 100.0, 1)
        assert report["grade"] in {"A+", "A", "B", "C", "D", "F"}
        assert report["verdict"] in {"excellent", "good", "fair", "poor"}
        assert report["has_reference"] is False
        assert isinstance(report["recommendations"], list)
        assert report["recommendations"]

    def test_no_reference_drops_dimensions(self) -> None:
        report = quality_score_report(self.SAMPLE, lang="en")
        dims = report["dimensions"]
        assert "semantic_similarity" not in dims
        assert "change_ratio" not in dims
        for key in ("naturalness", "readability", "ai_pattern_risk",
                    "watermark_risk", "speed"):
            assert key in dims

    def test_reference_adds_dimensions(self) -> None:
        original = (
            "Moreover, it is important to note that the utilization of this "
            "methodology facilitates optimal outcomes across all domains."
        )
        revised = (
            "This method simply works better, and you can see the results "
            "in most situations without the jargon."
        )
        report = quality_score_report(revised, original=original, lang="en")
        assert report["has_reference"] is True
        dims = report["dimensions"]
        assert "semantic_similarity" in dims
        assert "change_ratio" in dims
        assert 0.0 <= dims["change_ratio"]["raw_change_ratio"] <= 1.0

    def test_weights_normalised_to_one(self) -> None:
        for kwargs in ({}, {"original": SAMPLE_REF}):
            report = quality_score_report(self.SAMPLE, lang="en", **kwargs)
            total = sum(d["weight"] for d in report["dimensions"].values())
            assert abs(total - 1.0) < 1e-6

    def test_custom_weights_override(self) -> None:
        # Zero out every dimension except naturalness so it is the only
        # active contributor; the composite then equals its value.
        only_nat = {
            "semantic_similarity": 0.0,
            "readability": 0.0,
            "ai_pattern_risk": 0.0,
            "watermark_risk": 0.0,
            "change_ratio": 0.0,
            "speed": 0.0,
            "naturalness": 1.0,
        }
        report = quality_score_report(self.SAMPLE, lang="en", weights=only_nat)
        assert report["dimensions"]["naturalness"]["weight"] == 1.0
        assert abs(
            report["score"] - report["dimensions"]["naturalness"]["value"]
        ) < 1e-6

    def test_fast_mode_uses_fast_detector(self) -> None:
        report = quality_score_report(self.SAMPLE, lang="en", fast=True)
        assert report["dimensions"]["ai_pattern_risk"]["source"] == "detect_ai_fast"

    def test_empty_text(self) -> None:
        report = quality_score_report("")
        assert report["score"] == 0.0
        assert report["grade"] == "F"
        assert report["dimensions"] == {}

    def test_non_str_raises(self) -> None:
        from texthumanize.exceptions import ConfigError
        try:
            quality_score_report(123)  # type: ignore[arg-type]
        except ConfigError:
            pass
        else:  # pragma: no cover
            raise AssertionError("expected ConfigError")

    def test_timing_present(self) -> None:
        report = quality_score_report(self.SAMPLE, lang="en")
        assert report["timing"]["latency_ms"] >= 0.0
        assert report["timing"]["chars_per_sec"] >= 0.0


SAMPLE_REF = "The original reference text used for similarity comparisons here."


class TestQualityHelpers:
    """Internal scoring helpers behave monotonically and within bounds."""

    def test_grade_bands(self) -> None:
        assert _quality_grade(0.95) == "A+"
        assert _quality_grade(0.83) == "A"
        assert _quality_grade(0.0) == "F"

    def test_verdict_bands(self) -> None:
        assert _quality_verdict(0.9) == "excellent"
        assert _quality_verdict(0.7) == "good"
        assert _quality_verdict(0.55) == "fair"
        assert _quality_verdict(0.1) == "poor"

    def test_text_similarity_identical_and_disjoint(self) -> None:
        assert _text_similarity("hello world", "hello world") == 1.0
        assert _text_similarity("hello world", "") == 0.0
        assert _text_similarity("alpha beta", "gamma delta") < 0.3

    def test_readability_quality_band(self) -> None:
        assert _readability_quality(9.0) == 1.0
        assert _readability_quality(0.0) == 0.6
        assert _readability_quality(40.0) < 0.1

    def test_change_balance_sweet_spot(self) -> None:
        assert _change_balance_quality(0.2) == 1.0
        assert _change_balance_quality(0.0) == 0.55
        assert _change_balance_quality(0.9) < 0.3


class TestQualityCLI:
    """CLI: ``texthumanize quality`` and ``--quality-score``."""

    def _run(self, *args: str, stdin: str | None = None) -> dict:
        proc = subprocess.run(
            [sys.executable, "-m", "texthumanize", *args],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout)

    def test_quality_subcommand_stdin(self) -> None:
        report = self._run("quality", "-", "--json", stdin=TestQualityScoreReport.SAMPLE)
        assert report["schema_version"] == "text-humanize.quality_score.v1"
        assert report["has_reference"] is False

    def test_quality_flag(self, tmp_path) -> None:
        path = tmp_path / "input.txt"
        path.write_text(TestQualityScoreReport.SAMPLE, encoding="utf-8")
        report = self._run(str(path), "--quality-score")
        assert report["schema_version"] == "text-humanize.quality_score.v1"

    def test_quality_with_reference(self, tmp_path) -> None:
        ref = tmp_path / "ref.txt"
        out = tmp_path / "out.txt"
        ref.write_text("Original reference text for comparison.", encoding="utf-8")
        out.write_text(TestQualityScoreReport.SAMPLE, encoding="utf-8")
        report = self._run(
            "quality", str(out), "--reference", str(ref), "--json"
        )
        assert report["has_reference"] is True
        assert "semantic_similarity" in report["dimensions"]
        # The reference and input are distinct files: the --reference value
        # must not be misread as the positional input (which would make them
        # identical and force similarity to 1.0).
        assert report["dimensions"]["semantic_similarity"]["value"] < 1.0
