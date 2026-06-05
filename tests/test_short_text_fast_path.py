from __future__ import annotations

from texthumanize import humanize
from texthumanize.core import _short_text_fast_path_risk, _try_short_text_fast_path
from texthumanize.utils import HumanizeOptions


def test_short_low_risk_text_uses_fast_path() -> None:
    result = humanize(
        "I checked the draft and fixed two awkward lines.",
        lang="en",
        seed=42,
    )

    assert result.text
    assert any(change["type"] == "fast_path" for change in result.changes)
    assert result.metrics_after["fast_path"]["enabled"] is True
    assert result.metrics_after["humanize_explain"]["schema_version"] == (
        "text-humanize.humanize_explain.v1"
    )


def test_short_ai_like_marker_disables_fast_path() -> None:
    text = (
        "Furthermore, it is important to note that this comprehensive "
        "implementation facilitates optimization."
    )

    assert _short_text_fast_path_risk(text).startswith("ai_marker:")
    assert _try_short_text_fast_path(
        text,
        "en",
        HumanizeOptions(lang="en"),
        has_custom_controls=False,
    ) is None


def test_short_unicode_marker_disables_fast_path() -> None:
    text = "This\u200b text has hidden markers."

    assert _short_text_fast_path_risk(text) == "unicode_marker"
    assert _try_short_text_fast_path(
        text,
        "en",
        HumanizeOptions(lang="en"),
        has_custom_controls=False,
    ) is None


def test_short_fast_path_respects_custom_controls() -> None:
    text = "I checked the draft and fixed two awkward lines."

    assert _try_short_text_fast_path(
        text,
        "en",
        HumanizeOptions(lang="en"),
        has_custom_controls=True,
    ) is None
    assert _try_short_text_fast_path(
        text,
        "en",
        HumanizeOptions(lang="en", custom_dict={"draft": "copy"}),
        has_custom_controls=False,
    ) is None
