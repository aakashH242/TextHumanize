#!/usr/bin/env python3
"""Calibrate the built-in AI detector against the labelled eval corpus.

Sweeps decision thresholds and reports precision/recall/F1 at each, the best-F1
threshold (overall and per language), and metrics at the current default. Fully
offline. Optionally compare against external scores supplied as JSON ``{id: score}``.

Usage:
    python scripts/calibrate_detector.py
    python scripts/calibrate_detector.py --langs en,ru,uk
    python scripts/calibrate_detector.py --external external_scores.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Detector calibration")
    parser.add_argument("--langs", help="Comma-separated languages")
    parser.add_argument("--default-threshold", type=float, default=0.50)
    parser.add_argument("--external", help="JSON file mapping sample id -> external score")
    args = parser.parse_args()

    from texthumanize.quality_metrics import detector_calibration

    languages = args.langs.split(",") if args.langs else None
    external = None
    if args.external:
        external = {
            str(k): float(v)
            for k, v in json.loads(Path(args.external).read_text(encoding="utf-8")).items()
        }

    report = detector_calibration(
        languages=languages,
        default_threshold=args.default_threshold,
        external_scores=external,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
