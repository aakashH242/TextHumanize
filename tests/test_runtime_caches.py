from __future__ import annotations

from texthumanize.decancel import (
    Debureaucratizer,
    _get_compiled_phrase_patterns,
    _get_compiled_word_patterns,
)
from texthumanize.lang import get_lang_pack


def test_unknown_language_pack_is_cached() -> None:
    first = get_lang_pack("xx-cache-test")
    second = get_lang_pack("xx-cache-test")

    assert first is second
    assert first["code"] == "xx-cache-test"
    assert first["bureaucratic"] == {}


def test_debureaucratizer_reuses_compiled_standard_patterns() -> None:
    _get_compiled_phrase_patterns.cache_clear()
    _get_compiled_word_patterns.cache_clear()

    first_phrases = _get_compiled_phrase_patterns("en")
    second_phrases = _get_compiled_phrase_patterns("en")
    first_words = _get_compiled_word_patterns("en")
    second_words = _get_compiled_word_patterns("en")

    assert first_phrases is second_phrases
    assert first_words is second_words
    assert first_words


def test_debureaucratizer_custom_lang_pack_still_uses_custom_patterns() -> None:
    db = Debureaucratizer(lang="en", intensity=100, seed=1)
    db.lang_pack = {
        "bureaucratic_phrases": {"very important": ["key"]},
        "bureaucratic": {},
    }
    db._max_changes = 5
    db._changes_made = 0

    result = db._replace_phrases("This is very important for quality.", prob=1.0)

    assert "key" in result
    assert db.changes[0]["type"] == "decancel_phrase"
