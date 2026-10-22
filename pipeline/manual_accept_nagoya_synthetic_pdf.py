"""Manual standalone acceptance: real synthetic Japanese PDFs, no real data.

Use: python manual_accept_nagoya_synthetic_pdf.py
Requires optional PyMuPDF from requirements_nagoya_pdf_triage.txt.
Generates nine entirely fictitious records across the existing five ward
labels in memory, and tests unchanged / add / delete / rename / address /
row-note / footnote / PDF metadata mutations through the actual extractor.
No network calls, no PDF writing, no raw disaster data, no approval/promotion.
This script is NOT a substitute for real-PDF source-content audit.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from contextlib import ExitStack
from unittest.mock import patch

try:
    import pymupdf
except ImportError:
    sys.exit("PyMuPDF required for manual synthetic PDF acceptance: "
             "python -m pip install -r requirements_nagoya_pdf_triage.txt")

import triage_nagoya_pdf_facility_changes as triage
from check_nagoya_official_pdf_updates import (
    SAFETY, WATCH_SOURCES, capture_snapshot,
)

# These names and addresses are deliberately fictitious and are NOT official
# facilities. Wards here serve only as source-group labels for test routing.
GROUP_SIZES = {"天白区": 3, "守山区": 3, "緑区": 1, "東区": 1, "中村区": 1}
SYNTHETIC_BY_WARD = {
    ward: tuple((f"架空{ward}施設{n}", f"架空{ward}町{n}-10{n}")
                for n in range(1, count + 1))
    for ward, count in GROUP_SIZES.items()
}
SYNTHETIC_FACILITIES = tuple(sorted(
    ((ward, name, address)
     for ward, pairs in SYNTHETIC_BY_WARD.items()
     for name, address in pairs)
))


def synthetic_pdf(ward: str, scenario="baseline") -> bytes:
    """Build an actual searchable Japanese PDF entirely in memory."""
    if ward not in SYNTHETIC_BY_WARD:
        raise ValueError("Unknown synthetic source group")
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=840, height=740)
        page.insert_text((45, 45), "HINANEX SYNTHETIC TEST ONLY - NOT OFFICIAL",
                         fontsize=12)
        for index, (name, address) in enumerate(SYNTHETIC_BY_WARD[ward]):
            if index == 0 and scenario == "deleted":
                continue
            y = 125 + 65 * index
            if index == 0 and scenario == "renamed":
                name = "改称後の架空施設・検証専用"
            if index == 0 and scenario == "address_changed":
                address = "架空移転先町9-909"
            page.insert_text((55, y), name, fontsize=12, fontname="japan")
            page.insert_text((330, y), address, fontsize=12, fontname="japan")
            note = "備考変更B" if index == 0 and scenario == "row_note_changed" else "備考A"
            page.insert_text((585, y), note, fontsize=12, fontname="japan")
        if scenario == "added":
            page.insert_text((55, 525), "架空追加施設・検証専用", fontsize=12, fontname="japan")
            page.insert_text((330, 525), "架空新設町8-808", fontsize=12, fontname="japan")
        footer = "脚注変更B" if scenario == "footnote_changed" else "脚注A"
        page.insert_text((55, 640), footer, fontsize=12, fontname="japan")
        if scenario == "metadata_changed":
            doc.set_metadata({"title": "SYNTHETIC PDF REVISED METADATA"})
        return doc.tobytes(garbage=3, deflate=True)
    finally:
        doc.close()


def synthetic_capture(documents: dict[str, bytes]):
    by_url = {url: ward for ward, url in WATCH_SOURCES}
    return capture_snapshot(
        lambda url: documents[by_url[url]],
        captured_at="2026-10-22T10:00:00Z",
    )


def real_extraction_snapshot(documents: dict[str, bytes]):
    return triage.make_facility_snapshot(
        synthetic_capture(documents), documents,
        captured_at="2026-10-22T10:15:00Z",
    )


def validate_scenario(baseline: dict, variant: dict, scenario: str, ward: str) -> dict:
    result = triage.compare_facility_snapshots(baseline, variant)
    if result["safety"] != SAFETY:
        raise AssertionError("Unexpected safety gate mutation")
    if result["facility_count"] != 9 or result["baseline_extract_matched_count"] != 9:
        raise AssertionError("Synthetic nine-row baseline was not fully extractable")
    if len(result["facilities"]) != 9:
        raise AssertionError("Unexpected facility count / silent additions")
    if scenario == "unchanged":
        if (result["source_changed_count"], result["row_changed_candidate_count"],
                result["unresolved_extraction_count"], result["human_review_required_count"],
                result["current_extract_matched_count"]) != (0, 0, 0, 0, 9):
            raise AssertionError("Unchanged PDF incorrectly triggered review or missed rows")
    else:
        if result["source_changed_count"] != 1:
            raise AssertionError(f"{scenario}: expected one modified PDF source")
        # Even if the row text is unchanged, any source-byte revision requires
        # *all* the ward's tracked facilities to receive source-level review.
        affected = [x for x in result["facilities"] if x["ward"] == ward]
        if not all(x["classification"] != triage.SOURCE_UNCHANGED for x in affected):
            raise AssertionError(f"{scenario}: silent skipping of changed-source review")
        if result["human_review_required_count"] != len(SYNTHETIC_BY_WARD[ward]):
            raise AssertionError(f"{scenario}: wrong ward-level review count")

        expected_changed = 1 if scenario == "row_note_changed" else 0
        expected_unresolved = 1 if scenario in (
            "deleted", "renamed", "address_changed") else 0
        if result["row_changed_candidate_count"] != expected_changed:
            raise AssertionError(f"{scenario}: wrong modified-row count")
        if result["unresolved_extraction_count"] != expected_unresolved:
            raise AssertionError(f"{scenario}: unresolved rows were incorrectly promoted")
        if result["current_extract_matched_count"] != 9 - expected_unresolved:
            raise AssertionError(f"{scenario}: missing/renamed record was silently matched")
        if scenario in ("added", "footnote_changed", "metadata_changed"):
            if not all(r["classification"] == triage.SOURCE_CHANGED_ROW_UNCHANGED
                       for r in affected):
                raise AssertionError(f"{scenario}: source-only change misclassified as a row edit")
        if scenario == "row_note_changed":
            if Counter(x["classification"] for x in affected)[triage.SOURCE_CHANGED_ROW_CHANGED] != 1:
                raise AssertionError("Row-local annotation change not isolated")
        if scenario in ("deleted", "renamed", "address_changed"):
            if Counter(x["classification"] for x in affected)[triage.UNRESOLVED] != 1:
                raise AssertionError("A missing name/address is not a confirmed deletion")
    return {
        "scenario": scenario,
        "changed_pdf_count": result["source_changed_count"],
        "matched_facilities": result["current_extract_matched_count"],
        "row_changed_candidates": result["row_changed_candidate_count"],
        "unresolved": result["unresolved_extraction_count"],
        "human_review_required": result["human_review_required_count"],
        "pass": True,
    }


def run() -> dict:
    ward = next(w for w, count in GROUP_SIZES.items() if count == 3)
    baseline_documents = {w: synthetic_pdf(w) for w, _ in WATCH_SOURCES}
    with ExitStack() as stack:
        stack.enter_context(patch.object(triage, "BY_WARD", SYNTHETIC_BY_WARD))
        stack.enter_context(patch.object(triage, "FACILITIES", SYNTHETIC_FACILITIES))
        baseline = real_extraction_snapshot(baseline_documents)
        if sum(x["extract_status"] == "MATCHED" for x in baseline["facilities"]) != 9:
            raise AssertionError("Actual PyMuPDF extraction failed the synthetic baseline")
        results = []
        for scenario in ("unchanged", "added", "deleted", "renamed", "address_changed",
                         "row_note_changed", "footnote_changed", "metadata_changed"):
            modified = dict(baseline_documents)
            if scenario != "unchanged":
                modified[ward] = synthetic_pdf(ward, scenario)
                if hashlib.sha256(modified[ward]).digest() == hashlib.sha256(
                        baseline_documents[ward]).digest():
                    raise AssertionError(f"Test PDF did not actually change: {scenario}")
            new = real_extraction_snapshot(modified)
            results.append(validate_scenario(baseline, new, scenario, ward))
    return {
        "report_kind": "NAGOYA_SYNTHETIC_PDF_MUTATION_TEST_NOT_SOURCE_APPROVAL",
        "synthetic": True,
        "actual_official_pdf_downloads": 0,
        "pdf_bytes_persisted": False,
        "scenario_count": len(results),
        "results": results,
        "all_passed": True,
        "caution": (
            "Name/address changes or removals are UNRESOLVED, not proven "
            "deleted or relocated. Untracked additions trigger ward-level "
            "review, not a new approved facility. Text/layout matching "
            "does not certify original official meaning."
        ),
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "official_facility_positions_accepted": 0,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
