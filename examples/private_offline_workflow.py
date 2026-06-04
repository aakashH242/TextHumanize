"""Private offline TextHumanize workflow.

This example shows an audit -> safe cleanup -> strict/minimal humanize -> audit
pipeline that is suitable for local CI, on-prem systems, and privacy-sensitive
content workflows.

Run:
    python examples/private_offline_workflow.py
"""

from __future__ import annotations

import json
import socket
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from texthumanize import audit_report, clean_safe, humanize


SAMPLE_TEXT = (
    "Furthermore, it is important to note that Acme Analytics provides a "
    "comprehensive implementation for support teams.\u200b The Order ID A-1024 "
    "must remain unchanged, and https://example.com/docs should stay intact."
)


@contextmanager
def blocked_network() -> Any:
    """Raise immediately if code tries to open a network socket."""
    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def _blocked(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network access is disabled for this workflow")

    socket.socket = _blocked  # type: ignore[assignment]
    socket.create_connection = _blocked  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]
        socket.create_connection = original_create_connection  # type: ignore[assignment]


def run_private_offline_workflow(
    text: str,
    *,
    lang: str = "en",
    seed: int = 20260604,
) -> dict[str, Any]:
    """Run TextHumanize without external network calls or cloud backends."""
    preserve = {
        "urls": True,
        "emails": True,
        "numbers": True,
        "dates": True,
        "prices": True,
        "identifiers": True,
        "quoted_text": True,
        "named_entities": True,
        "brand_terms": ["Acme Analytics"],
    }
    constraints = {
        "max_change_ratio": 0.35,
        "keep_keywords": ["Acme Analytics", "Order ID A-1024"],
    }

    with blocked_network():
        audit_before = audit_report(text, lang=lang, aggressive_watermark=False)
        safe_text = clean_safe(text, lang=lang)
        result = humanize(
            safe_text,
            lang=lang,
            profile="web",
            intensity=60,
            preserve=preserve,
            constraints=constraints,
            quality_gate="strict",
            minimal=True,
            backend="local",
            seed=seed,
        )
        audit_after = audit_report(
            result.text,
            lang=result.lang,
            aggressive_watermark=False,
        )

    return {
        "schema_version": "text-humanize.private_offline_workflow.v1",
        "network": "blocked",
        "backend": "local",
        "lang": result.lang,
        "input": {
            "chars": len(text),
            "had_watermark": audit_before["watermark"]["has_watermarks"],
            "ai_score": audit_before["ai"]["score"],
            "watermark_risk": audit_before["watermark"]["risk_score"],
        },
        "output": {
            "text": result.text,
            "change_ratio": result.change_ratio,
            "quality_score": result.quality_score,
            "ai_score": audit_after["ai"]["score"],
            "watermark_risk": audit_after["watermark"]["risk_score"],
            "safe_cleanup_changed": safe_text != text,
        },
        "preserved_terms": {
            "brand": "Acme Analytics" in result.text,
            "order_id": "Order ID A-1024" in result.text,
            "url": "https://example.com/docs" in result.text,
        },
        "suggested_actions": audit_after["suggested_actions"],
    }


def main() -> None:
    report = run_private_offline_workflow(SAMPLE_TEXT)
    output_path = Path("private_offline_report.json")
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {output_path}")


if __name__ == "__main__":
    main()
