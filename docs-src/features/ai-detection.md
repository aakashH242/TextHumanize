# AI Detection

Explainable built-in detector for internal style-risk scoring. No external API
keys, no network calls.

!!! note "External detector results"
    TextHumanize detector scores are internal quality signals. They do not
    guarantee passing GPTZero, Originality.ai, Turnitin, or any other external
    detector. See [Responsible Use](../responsible-use.md).

## Quick Start

```python
from texthumanize import detect_ai, detect_ai_sentences, detect_ai_mixed

# Single text
result = detect_ai("Text to check.", lang="en")
print(f"{result['score']:.0%} — {result['verdict']}")

# Per-sentence detection
for s in detect_ai_sentences(long_text, lang="en"):
    emoji = '🤖' if s['label'] == 'ai' else '👤'
    print(f"{emoji} {s['text'][:80]}")

# Mixed content detection
mixed = detect_ai_mixed(text, lang="en")
print(f"AI segments: {mixed['ai_ratio']:.0%}")
```

## Metrics

| Metric | What It Measures |
|:-------|:----------------|
| AI Patterns | Formulaic phrases ("it is important to note", "furthermore") |
| Burstiness | Sentence length uniformity (humans vary, AI doesn't) |
| Opening Diversity | Repetitive sentence starts |
| Entropy | Word predictability (Shannon entropy) |
| Vocabulary | Lexical richness (type-to-token ratio) |
| Perplexity | Character-level predictability |
| Stylometry | Writing style consistency |
| Coherence | Paragraph flow and transitions |
| Grammar Perfection | Suspiciously perfect grammar |
| Punctuation | Punctuation variety and patterns |
| Rhythm | Sentence cadence uniformity |
| Readability | Consistency of reading level |
| Zipf | Word frequency distribution |

## Ensemble

The detection uses three methods combined:

- **Weighted sum** (50%) — normalized metric scores
- **Strong signal detector** (30%) — any single metric above threshold
- **Majority voting** (20%) — count of metrics flagging AI

## Verdicts

| Verdict | Score Range | Meaning |
|---------|:-----------:|---------|
| `human_written` | < 35% | Likely written by a human |
| `mixed` | 35–65% | Uncertain or mixed content |
| `ai_generated` | ≥ 65% | Likely AI-generated |

## Batch Detection

```python
from texthumanize import detect_ai_batch

texts = ["Text 1", "Text 2", "Text 3"]
results = detect_ai_batch(texts, lang="en")
for r in results:
    print(f"{r['score']:.0%} — {r['verdict']}")
```
