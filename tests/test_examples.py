"""Regression checks for documentation examples."""

from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FASTAPI_EXAMPLE = ROOT / "examples" / "fastapi_integration.py"


def test_fastapi_example_compiles():
    py_compile.compile(str(FASTAPI_EXAMPLE), doraise=True)


def test_fastapi_example_is_production_oriented():
    source = FASTAPI_EXAMPLE.read_text(encoding="utf-8")
    required_markers = [
        "MAX_TEXT_CHARS",
        "MAX_BATCH_ITEMS",
        "TIMEOUT_SECONDS",
        "MAX_BODY_BYTES",
        "asyncio.wait_for",
        "ERROR_SCHEMA_VERSION",
        "request_id",
        '"/v1/humanize/batch"',
        "RequestValidationError",
        "HTTP_504_GATEWAY_TIMEOUT",
    ]
    for marker in required_markers:
        assert marker in source
