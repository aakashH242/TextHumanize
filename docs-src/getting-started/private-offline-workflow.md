# Private Offline Workflow

TextHumanize can run a full audit and humanization workflow without cloud APIs,
telemetry, or network calls. This is the recommended pattern for on-prem,
Promopilot-style integrations, local CI, and privacy-sensitive content review.

## Workflow

1. Run `audit_report()` on the original text.
2. Use `clean_safe()` for obvious Unicode or metadata cleanup.
3. Run `humanize()` with `backend="local"`, `quality_gate="strict"`, and
   `minimal=True`.
4. Preserve brand terms, URLs, numbers, dates, quotes, and identifiers.
5. Run `audit_report()` again on the output.
6. Store only non-sensitive metrics when possible: scores, change ratio,
   quality score, and boolean preservation checks.

## Runnable Example

See [`examples/private_offline_workflow.py`](https://github.com/ksanyok/TextHumanize/blob/main/examples/private_offline_workflow.py).

```bash
python examples/private_offline_workflow.py
```

The example writes `private_offline_report.json` with:

- built-in AI-like risk before and after;
- watermark risk before and after;
- `quality_score` and `change_ratio`;
- whether brand, order id, and URL values were preserved;
- suggested next actions for review.

## Minimal Code

```python
from texthumanize import audit_report, clean_safe, humanize

text = "Furthermore, Acme Analytics provides a comprehensive solution.\u200b"

audit_before = audit_report(text, lang="en")
safe_text = clean_safe(text, lang="en")

result = humanize(
    safe_text,
    lang="en",
    profile="web",
    intensity=60,
    backend="local",
    quality_gate="strict",
    minimal=True,
    preserve={
        "urls": True,
        "numbers": True,
        "identifiers": True,
        "named_entities": True,
        "brand_terms": ["Acme Analytics"],
    },
    constraints={
        "max_change_ratio": 0.35,
        "keep_keywords": ["Acme Analytics"],
    },
    seed=42,
)

audit_after = audit_report(result.text, lang=result.lang)
```

## Network Guard

For high-assurance local workflows, wrap the run in a socket guard. The example
does this with `blocked_network()` so any accidental socket creation raises
immediately.

This is a workflow safeguard, not a requirement for TextHumanize itself. With
`backend="local"`, the library does not need API keys or external services.

## Recommended Defaults

| Option | Recommended Value | Why |
|--------|-------------------|-----|
| `backend` | `"local"` | Avoid cloud APIs and network calls |
| `quality_gate` | `"strict"` | Roll back risky rewrites |
| `minimal` | `True` | Edit only flagged text where possible |
| `max_change_ratio` | `0.25-0.35` | Keep changes reviewable |
| `seed` | Fixed integer | Reproducible output |
| `aggressive_watermark` | `False` by default | Review lexical changes before use |

## Review Checklist

- Confirm important terms and identifiers are preserved.
- Review before/after diffs for semantic drift.
- Treat built-in detector scores as internal quality signals.
- Keep external AI detector claims out of customer-facing reports.
- Add human review for legal, medical, academic, financial, and policy content.
