"""Тесты параллельной обработки (P3.3)."""

from __future__ import annotations

import pytest

from texthumanize import humanize_batch, humanize_batch_stream, humanize_chunked, humanize_stream
from texthumanize.exceptions import ConfigError

_SAMPLE = (
    "Artificial intelligence is rapidly evolving. Neural networks process "
    "vast amounts of data efficiently. Machine learning enables automated "
    "problem-solving capabilities that were previously impossible."
)

_BATCH = [
    "The weather is nice today. Birds are singing outside.",
    "Technology advances rapidly. New tools emerge constantly.",
    "Education is important. Knowledge builds societies.",
    "Health matters greatly. Exercise improves wellbeing.",
]


class TestParallelBatch:
    """Tests for humanize_batch with max_workers."""

    def test_batch_sequential(self):
        results = humanize_batch(
            _BATCH, lang="en", intensity=30, max_workers=None
        )
        assert len(results) == 4
        for r in results:
            assert r.text

    def test_batch_parallel(self):
        results = humanize_batch(
            _BATCH, lang="en", intensity=30, max_workers=2
        )
        assert len(results) == 4
        for r in results:
            assert r.text

    def test_batch_parallel_preserves_order(self):
        results = humanize_batch(
            _BATCH, lang="en", intensity=30, max_workers=4, seed=42
        )
        assert len(results) == 4
        # Order must be preserved (result[i] corresponds to _BATCH[i])
        for i, r in enumerate(results):
            # Original must match input
            assert r.original == _BATCH[i]

    def test_batch_progress_callback(self):
        progress = []

        def on_progress(idx, total, result):
            progress.append((idx, total))

        results = humanize_batch(
            _BATCH, lang="en", intensity=30,
            max_workers=2, on_progress=on_progress,
        )
        assert len(results) == 4
        assert len(progress) == 4

    def test_batch_single_item_no_thread(self):
        results = humanize_batch(
            ["Hello world."], lang="en", intensity=30, max_workers=4
        )
        assert len(results) == 1

    def test_batch_deterministic_with_seed(self):
        r1 = humanize_batch(
            _BATCH[:2], lang="en", intensity=40, seed=100
        )
        r2 = humanize_batch(
            _BATCH[:2], lang="en", intensity=40, seed=100
        )
        for a, b in zip(r1, r2):
            assert a.text == b.text

    def test_batch_stream_yields_ordered_results(self):
        items = list(
            humanize_batch_stream(
                _BATCH[:2],
                lang="en",
                intensity=30,
                seed=42,
                memory_limit_mb=1,
            )
        )
        assert [item["index"] for item in items] == [0, 1]
        assert all(item["result"].text for item in items)
        assert items[0]["result"].metrics_after["memory_bounded"]["enabled"] is True

    def test_batch_memory_limit_rejects_oversized_item(self):
        with pytest.raises(ConfigError, match="memory_limit_mb"):
            list(
                humanize_batch_stream(
                    ["x" * 2000],
                    lang="en",
                    memory_limit_mb=0.001,
                )
            )


class TestParallelChunked:
    """Tests for humanize_chunked with max_workers."""

    @pytest.mark.timeout(300)
    def test_chunked_sequential(self):
        long_text = "\n\n".join([_SAMPLE] * 10)
        result = humanize_chunked(
            long_text, chunk_size=200, lang="en", intensity=30,
        )
        assert result.text
        assert len(result.text) > 100

    @pytest.mark.timeout(300)
    def test_chunked_parallel(self):
        long_text = "\n\n".join([_SAMPLE] * 10)
        result = humanize_chunked(
            long_text, chunk_size=200, lang="en", intensity=30,
            max_workers=2,
        )
        assert result.text
        assert len(result.text) > 100

    def test_chunked_small_text_no_split(self):
        result = humanize_chunked(
            _SAMPLE, chunk_size=5000, lang="en", intensity=30,
            max_workers=4,
        )
        assert result.text

    def test_chunked_empty_text(self):
        result = humanize_chunked("", chunk_size=100, lang="en")
        assert result.text == ""

    @pytest.mark.timeout(300)
    def test_chunked_parallel_changes_collected(self):
        long_text = "\n\n".join([_SAMPLE] * 5)
        result = humanize_chunked(
            long_text, chunk_size=200, lang="en", intensity=50,
            max_workers=2,
        )
        # Changes from all chunks should be collected
        assert isinstance(result.changes, list)

    def test_chunked_memory_limit_metadata(self):
        long_text = "\n\n".join([_SAMPLE] * 3)
        result = humanize_chunked(
            long_text,
            chunk_size=200,
            lang="en",
            intensity=30,
            memory_limit_mb=1,
        )
        assert result.metrics_after["memory_bounded"]["enabled"] is True
        assert result.metrics_after["memory_bounded"]["chunks"] >= 1

    def test_chunked_memory_limit_rejects_large_chunk(self):
        with pytest.raises(ConfigError, match="memory_limit_mb"):
            humanize_chunked(
                "x" * 2000,
                chunk_size=100,
                lang="en",
                memory_limit_mb=0.001,
            )


class TestParallelPerformance:
    """Verify parallel processing doesn't break anything."""

    def test_parallel_vs_sequential_same_result(self):
        """Parallel and sequential should produce same results with same seed."""
        texts = _BATCH[:2]
        seq = humanize_batch(
            texts, lang="en", intensity=40, seed=77, max_workers=1
        )
        par = humanize_batch(
            texts, lang="en", intensity=40, seed=77, max_workers=2
        )
        for s, p in zip(seq, par):
            assert s.text == p.text

    def test_parallel_thread_safety(self):
        """Multiple parallel calls should not interfere."""
        results = humanize_batch(
            _BATCH * 2, lang="en", intensity=30, max_workers=4
        )
        assert len(results) == 8
        for r in results:
            assert r.text
            assert r.lang == "en"


class TestStreamingMemory:
    """Tests for memory-bounded humanize_stream."""

    def test_stream_memory_metadata(self):
        chunks = list(
            humanize_stream(
                "\n\n".join(_BATCH[:2]),
                lang="en",
                intensity=30,
                chunk_size=80,
                memory_limit_mb=1,
            )
        )
        assert chunks
        assert chunks[-1]["is_last"] is True
        assert chunks[0]["memory_bounded"]["enabled"] is True

    def test_stream_memory_limit_rejects_large_chunk(self):
        with pytest.raises(ConfigError, match="memory_limit_mb"):
            list(
                humanize_stream(
                    "x" * 2000,
                    lang="en",
                    chunk_size=100,
                    memory_limit_mb=0.001,
                )
            )
