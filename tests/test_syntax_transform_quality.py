"""Regression tests for syntax transformation quality improvements."""

from __future__ import annotations

import random

from texthumanize.sentence_restructurer import (
    SentenceRestructurer,
    merge_short_sentences,
)


def test_merge_short_sentences_reduces_choppy_rhythm() -> None:
    text = (
        "The setup is simple. The result is stable. "
        "Users get answers. Support stays calm."
    )

    result = merge_short_sentences(
        text,
        lang="en",
        rng=random.Random(1),
        intensity=1.0,
    )

    assert result != text
    assert ", " in result
    assert result.count(".") < text.count(".")


def test_merge_short_sentences_preserves_numbers_and_questions() -> None:
    text = (
        "Version 2 ships today. The result is stable. "
        "Is it ready? The team agrees."
    )

    result = merge_short_sentences(
        text,
        lang="en",
        rng=random.Random(1),
        intensity=1.0,
    )

    assert result == text


def test_sentence_restructurer_records_sentence_merge() -> None:
    text = (
        "The setup is simple. The result is stable. "
        "Users get answers. Support stays calm."
    )
    restructurer = SentenceRestructurer(lang="en", intensity=100, seed=1)

    result = restructurer.process(text)

    assert result != text
    assert any(change["type"] == "sentence_merge" for change in restructurer.changes)
