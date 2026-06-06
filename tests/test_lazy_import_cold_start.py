"""Cold-start lazy import regression tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _run_cold_import(code: str) -> dict[str, Any]:
    env = os.environ.copy()
    pythonpath = str(ROOT)
    if env.get("PYTHONPATH"):
        pythonpath = pythonpath + os.pathsep + env["PYTHONPATH"]
    env["PYTHONPATH"] = pythonpath
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_package_import_skips_distribution_metadata_and_heavy_modules() -> None:
    data = _run_cold_import(
        """
import json
import sys
import texthumanize

blocked = [
    "importlib.metadata",
    "texthumanize.lang",
    "texthumanize.lang_detect",
    "texthumanize.analyzer",
    "texthumanize.pipeline",
    "texthumanize.detectors",
    "texthumanize.neural_detector",
]
print(json.dumps({
    "version": texthumanize.__version__,
    "loaded": [name for name in blocked if name in sys.modules],
}, sort_keys=True))
"""
    )
    assert data["version"]
    assert data["loaded"] == []


def test_public_core_function_access_does_not_load_pipeline_or_language_packs() -> None:
    data = _run_cold_import(
        """
import json
import sys
from texthumanize import detect_ai_fast, humanize

blocked = [
    "importlib.metadata",
    "texthumanize.lang",
    "texthumanize.lang_detect",
    "texthumanize.analyzer",
    "texthumanize.pipeline",
    "texthumanize.detectors",
    "texthumanize.neural_detector",
]
print(json.dumps({
    "core_loaded": "texthumanize.core" in sys.modules,
    "humanize_module": humanize.__module__,
    "detect_fast_module": detect_ai_fast.__module__,
    "loaded": [name for name in blocked if name in sys.modules],
}, sort_keys=True))
"""
    )
    assert data["core_loaded"] is True
    assert data["humanize_module"] == "texthumanize.core"
    assert data["detect_fast_module"] == "texthumanize.core"
    assert data["loaded"] == []


def test_empty_humanize_keeps_heavy_modules_lazy() -> None:
    data = _run_cold_import(
        """
import json
import sys
from texthumanize import humanize

result = humanize("")
blocked = [
    "texthumanize.lang",
    "texthumanize.lang_detect",
    "texthumanize.analyzer",
    "texthumanize.pipeline",
]
print(json.dumps({
    "text": result.text,
    "loaded": [name for name in blocked if name in sys.modules],
}, sort_keys=True))
"""
    )
    assert data == {"loaded": [], "text": ""}
