"""Tests for packaged contributor JSON packs."""

from __future__ import annotations

from importlib import resources

import pytest

from texthumanize import (
    list_contributor_packs,
    load_contributor_pack,
    validate_contributor_pack,
)


def test_list_contributor_packs_exposes_all_pack_types():
    packs = list_contributor_packs()
    assert set(packs) == {
        "ai_markers",
        "synonyms",
        "collocations",
        "watermark_samples",
    }
    for meta in packs.values():
        assert meta["schema_version"] == "text-humanize.contributor_pack.v1"
        assert meta["license"]["id"] == "CC0-1.0"
        assert meta["entry_count"] >= 3
        assert "en" in meta["languages"]


@pytest.mark.parametrize(
    "pack",
    ["ai_markers", "synonyms", "collocations", "watermark_samples"],
)
def test_contributor_packs_are_valid(pack: str):
    report = validate_contributor_pack(pack)
    assert report == {
        "valid": True,
        "pack": pack,
        "entry_count": 3,
        "errors": [],
    }


def test_load_contributor_pack_filters_by_language_and_domain():
    pack = load_contributor_pack("synonyms", languages=["en"], domains=["support"])
    assert pack["pack"] == "synonyms"
    assert pack["entry_count"] == 1
    assert pack["languages"] == ["en"]
    assert pack["domains"] == ["support"]
    assert pack["entries"][0]["id"] == "syn_en_support_001"
    assert pack["entries"][0]["replacements"] == [
        "when you have a moment",
        "when you can",
    ]


def test_load_contributor_pack_accepts_hyphen_alias():
    pack = load_contributor_pack("watermark-samples", domains=["docs"])
    assert pack["pack"] == "watermark_samples"
    assert pack["entry_count"] == 1
    assert pack["entries"][0]["expected_findings"] == ["homoglyph_substitution"]


def test_validate_contributor_pack_reports_missing_required_fields():
    pack = load_contributor_pack("ai_markers")
    broken = dict(pack)
    broken["entries"] = [dict(pack["entries"][0])]
    broken["entries"][0].pop("marker")

    report = validate_contributor_pack(broken)
    assert report["valid"] is False
    assert report["pack"] == "ai_markers"
    assert "entries[0] missing: marker" in report["errors"]


def test_contributor_pack_resources_are_packaged():
    data_dir = resources.files("texthumanize").joinpath("data")
    for meta in list_contributor_packs().values():
        assert data_dir.joinpath(meta["file"]).is_file()
