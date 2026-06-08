"""Contributor-friendly JSON packs for community data updates."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

_PACK_SCHEMA = "text-humanize.contributor_pack.v1"
_PACK_FILES = {
    "ai_markers": "contributor_ai_markers_v1.json",
    "synonyms": "contributor_synonyms_v1.json",
    "collocations": "contributor_collocations_v1.json",
    "watermark_samples": "contributor_watermark_samples_v1.json",
}
_COMMON_REQUIRED = {
    "id",
    "lang",
    "domain",
    "source",
    "license",
}
_PACK_REQUIRED = {
    "ai_markers": _COMMON_REQUIRED | {
        "category",
        "marker",
        "severity",
        "suggested_actions",
    },
    "synonyms": _COMMON_REQUIRED | {
        "source_phrase",
        "replacements",
        "register",
        "constraints",
    },
    "collocations": _COMMON_REQUIRED | {
        "phrase",
        "strength",
        "preferred_contexts",
        "blocked_replacements",
    },
    "watermark_samples": _COMMON_REQUIRED | {
        "category",
        "sample_text",
        "expected_findings",
        "safe_clean_text",
    },
}


def _pack_name(pack: str) -> str:
    normalized = pack.strip().lower().replace("-", "_")
    if normalized not in _PACK_FILES:
        valid = ", ".join(sorted(_PACK_FILES))
        raise ValueError(f"Unknown contributor pack {pack!r}; expected one of {valid}")
    return normalized


def _read_pack(pack: str) -> dict[str, Any]:
    pack_name = _pack_name(pack)
    pack_path = resources.files("texthumanize").joinpath("data").joinpath(
        _PACK_FILES[pack_name]
    )
    with pack_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise ValueError(f"Invalid contributor pack resource: {_PACK_FILES[pack_name]}")
    return data


def _filter_entries(
    entries: list[dict[str, Any]],
    *,
    languages: list[str] | None,
    domains: list[str] | None,
) -> list[dict[str, Any]]:
    wanted_languages = set(languages or [])
    wanted_domains = set(domains or [])
    return [
        dict(entry)
        for entry in entries
        if (not wanted_languages or entry.get("lang") in wanted_languages)
        and (not wanted_domains or entry.get("domain") in wanted_domains)
    ]


def load_contributor_pack(
    pack: str,
    *,
    languages: list[str] | None = None,
    domains: list[str] | None = None,
) -> dict[str, Any]:
    """Load a packaged contributor JSON pack.

    Packs are small, CC0-licensed examples that define the expected contribution
    shape for AI markers, synonyms, collocations, and watermark samples.
    """
    pack_name = _pack_name(pack)
    data = _read_pack(pack_name)
    entries = _filter_entries(
        data["entries"],
        languages=languages,
        domains=domains,
    )
    loaded = dict(data)
    loaded["pack"] = pack_name
    loaded["entries"] = entries
    loaded["entry_count"] = len(entries)
    loaded["languages"] = sorted({entry["lang"] for entry in entries})
    loaded["domains"] = sorted({entry["domain"] for entry in entries})
    return loaded


def list_contributor_packs() -> dict[str, dict[str, Any]]:
    """Return a compact index of available packaged contributor packs."""
    result: dict[str, dict[str, Any]] = {}
    for pack_name, file_name in sorted(_PACK_FILES.items()):
        data = _read_pack(pack_name)
        entries = data["entries"]
        result[pack_name] = {
            "schema_version": data.get("schema_version"),
            "name": data.get("name"),
            "file": file_name,
            "license": data.get("license"),
            "entry_count": len(entries),
            "languages": sorted({entry["lang"] for entry in entries}),
            "domains": sorted({entry["domain"] for entry in entries}),
        }
    return result


def validate_contributor_pack(pack: str | dict[str, Any]) -> dict[str, Any]:
    """Validate a contributor pack resource or already-loaded pack dict."""
    data = load_contributor_pack(pack) if isinstance(pack, str) else pack
    pack_name = _pack_name(str(data.get("pack", "")))
    errors: list[str] = []

    if data.get("schema_version") != _PACK_SCHEMA:
        errors.append(f"schema_version must be {_PACK_SCHEMA}")
    if data.get("license", {}).get("id") != "CC0-1.0":
        errors.append("pack license must be CC0-1.0")

    required = _PACK_REQUIRED[pack_name]
    seen_ids: set[str] = set()
    for index, entry in enumerate(data.get("entries", [])):
        missing = sorted(field for field in required if not entry.get(field))
        if missing:
            errors.append(f"entries[{index}] missing: {', '.join(missing)}")
        entry_id = str(entry.get("id", ""))
        if entry_id in seen_ids:
            errors.append(f"duplicate entry id: {entry_id}")
        seen_ids.add(entry_id)

    return {
        "valid": not errors,
        "pack": pack_name,
        "entry_count": len(data.get("entries", [])),
        "errors": errors,
    }
