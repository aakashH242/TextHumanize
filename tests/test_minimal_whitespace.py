"""Regression tests for inter-sentence whitespace in minimal / only_flagged mode.

Bug: humanize(..., minimal=True) and humanize(..., only_flagged=True) dropped
every space after a sentence-ending period, turning
"Sample size looked right. Geographic spread looked right." into
"Sample size looked right.Geographic spread looked right.".

Root cause: detect_ai_sentences() trims trailing whitespace from sent["text"]
but keeps it inside [start:end], so end == next start and the gap-recovery
branch never fired. The fix reattaches the trailing whitespace explicitly.
"""

from __future__ import annotations

import re

from hypothesis import given, settings
from hypothesis import strategies as st

import texthumanize as th


class TestMinimalWhitespace:
    REPRO = "Sample size looked right. Geographic spread looked right."

    def test_clean_input_unchanged(self) -> None:
        # No characters dropped on clean, already-natural input.
        assert th.humanize("A. B. C.", lang="en", minimal=True).text == "A. B. C."

    def test_repro_space_preserved(self) -> None:
        out = th.humanize(self.REPRO, lang="en", minimal=True).text
        assert "right.Geographic" not in out
        assert ". " in out

    def test_only_flagged_alias_preserves_space(self) -> None:
        out = th.humanize(self.REPRO, lang="en", only_flagged=True).text
        assert "right.Geographic" not in out
        assert ". " in out

    def test_newline_between_sentences_preserved(self) -> None:
        src = "First sentence here.\nSecond sentence here."
        out = th.humanize(src, lang="en", minimal=True).text
        assert "\n" in out
        assert "here.Second" not in out

    def test_ai_input_still_rewrites_and_keeps_spaces(self) -> None:
        ai = (
            "Furthermore, it is important to note that the utilization of this "
            "methodology facilitates optimal outcomes. Moreover, the "
            "implementation of robust frameworks ensures that stakeholders can "
            "effectively achieve their objectives. The team met on Friday."
        )
        result = th.humanize(ai, lang="en", minimal=True, seed=7)
        # The rewrite must still happen AND spaces after periods must survive.
        assert result.change_ratio > 0
        assert ". " in result.text
        # No glued sentence boundaries.
        assert ".Moreover" not in result.text and ".The" not in result.text

    def test_clean_input_is_byte_exact(self) -> None:
        # Already-natural inputs must pass through minimal mode unchanged,
        # including leading, trailing and repeated whitespace.
        for src in (
            "  leading ws. trailing ws.  ",
            "Leading space test.  Double space after.  Triple.",
            "Tab\tseparated. Next sentence.",
        ):
            assert th.humanize(src, lang="en", minimal=True).text == src

    def test_multiple_spaces_and_punctuation(self) -> None:
        # Sentence boundaries with question/exclamation marks also keep spacing.
        src = "Is this right? Yes it is! Absolutely correct."
        out = th.humanize(src, lang="en", minimal=True).text
        assert "right?Yes" not in out
        assert "is!Absolutely" not in out


# ── Property-based invariant ─────────────────────────────────────────────────

_SENTENCES = [
    "the cat sat on the warm mat",
    "we shipped the update on friday",
    "coffee tasted good this morning",
    "the report covered three regions",
    "she fixed the bug before lunch",
    "rain is expected later today",
]
_SEPARATORS = [". ", ".  ", ".\n", ".\n\n", "! ", "? "]


def _glued_boundaries(text: str) -> int:
    """Count sentence-ending punctuation immediately followed by non-space."""
    return len(re.findall(r"[.!?](?=\S)", text))


@given(
    parts=st.lists(st.sampled_from(_SENTENCES), min_size=1, max_size=4),
    sep=st.sampled_from(_SEPARATORS),
)
@settings(max_examples=30, deadline=None)
def test_minimal_never_introduces_glued_boundaries(parts: list[str], sep: str) -> None:
    """Invariant: minimal mode must never delete whitespace after a sentence
    boundary, i.e. it can only keep or reduce the number of glued boundaries
    present in the input — never add new ones."""
    text = sep.join(parts)
    out = th.humanize(text, lang="en", minimal=True).text
    assert _glued_boundaries(out) <= _glued_boundaries(text)
