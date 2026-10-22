"""Operator-only, conservative P1 facility-row change triage for Nagoya PDFs.

A separate optional PyMuPDF dependency is required for real page extraction.
The first run *must* match the existing five-source byte baseline. A PDF table
row is accepted for comparison only when exactly one same-row official name
AND address pair is detectable; otherwise status is UNRESOLVED / human review.
Neither row-text equality nor difference is official meaning validation.
No raw documents, extracted document text, PRIVATE geocoding columns or
coordinates are persisted by this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from check_nagoya_official_pdf_updates import (
    SAFETY, WATCH_SOURCES, capture_snapshot, fetch_pdf,
    local_file as raw_basename, utc_capture_time, validate_snapshot,
)
from nagoya_team_review_official_sources import OFFICIAL_NAME_ADDRESS_WARD

SCHEMA = "hinanex.nagoya-facility-row-triage.v1"
OUTCOMES = frozenset(("MATCHED", "UNRESOLVED"))
SOURCE_UNCHANGED = "SOURCE_BYTES_UNCHANGED_NOT_OFFICIAL_APPROVAL"
SOURCE_CHANGED_ROW_CHANGED = "ROW_TEXT_CHANGED_HUMAN_REVIEW_REQUIRED"
SOURCE_CHANGED_ROW_UNCHANGED = "ROW_TEXT_UNCHANGED_SOURCE_CHANGED_REVIEW_REQUIRED"
UNRESOLVED = "ROW_EXTRACTION_UNRESOLVED_REVIEW_REQUIRED"
INCONSISTENT = "SAME_BYTES_DIFFERENT_EXTRACTION_HUMAN_REVIEW_REQUIRED"
ALL_STATES = frozenset((SOURCE_UNCHANGED, SOURCE_CHANGED_ROW_CHANGED,
                         SOURCE_CHANGED_ROW_UNCHANGED, UNRESOLVED, INCONSISTENT))
FACILITIES = tuple(sorted(
    ((ward, name, address) for (name, address), ward in OFFICIAL_NAME_ADDRESS_WARD.items())
))
BY_WARD = {ward: tuple((name, address) for w, name, address in FACILITIES if w == ward)
           for ward, _ in WATCH_SOURCES}


def extract_rows(pdf_bytes: bytes, ward: str) -> dict[tuple[str, str], str | None]:
    """Extract *candidate same-table-row* fingerprints; ambiguous rows are None.

    Never interpret disaster icons, floor numbers, or designated-shelter meaning.
    Any metadata PDF change remains flagged for human source-level review.
    """
    if ward not in BY_WARD:
        raise ValueError("Unrecognized official ward")
    try:
        import pymupdf  # PyMuPDF >=1.24, optional local/operator install
    except ImportError as exc:
        raise ValueError("PyMuPDF missing; install dedicated optional requirements") from exc
    results = {pair: [] for pair in BY_WARD[ward]}
    try:
        document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        try:
            if len(document) < 1 or len(document) > 30:
                raise ValueError("Unexpected PDF page count")
            for page in document:
                # Prevent ambiguous neighbouring rows from looking like one record.
                words = page.get_text("words")
                for name, address in BY_WARD[ward]:
                    names = page.search_for(name)
                    addresses = page.search_for(address)
                    candidate_pairs = [
                        (n, a) for n in names for a in addresses
                        if a.x0 > n.x1 and abs((n.y0 + n.y1) - (a.y0 + a.y1)) <= 9
                    ]
                    for n, a in candidate_pairs:
                        low = max(n.y0, a.y0) - 1
                        high = min(n.y1, a.y1) + 1
                        if high <= low:
                            continue
                        # Do not accidentally combine two adjacent facility rows.
                        tokens = sorted(
                            ((w[0], w[4]) for w in words
                             if w[2] >= n.x0 - 65
                             and w[1] <= high and w[3] >= low),
                            key=lambda item: item[0],
                        )
                        text = "\u001f".join(word for _, word in tokens)
                        if len(text) < len(name) + len(address) or len(text) > 2000:
                            continue
                        results[(name, address)].append(
                            hashlib.sha256(text.encode("utf-8")).hexdigest()
                        )
        finally:
            document.close()
    except (RuntimeError, OSError, ValueError) as exc:
        # Full ward becomes unresolved; do not silently classify a corrupt PDF
        # as an unchanged facility list.
        return {pair: None for pair in BY_WARD[ward]}
    return {pair: hashes[0] if len(hashes) == 1 else None
            for pair, hashes in results.items()}


def make_facility_snapshot(raw_snapshot: dict, fetched: dict[str, bytes],
                           extractor=extract_rows, captured_at=None) -> dict:
    validate_snapshot(raw_snapshot)
    if set(fetched) != set(BY_WARD):
        raise ValueError("Missing or unexpected ward source")
    expected = {row["ward"]: row for row in raw_snapshot["sources"]}
    sources = []
    findings = []
    for ward, url in WATCH_SOURCES:
        data = fetched[ward]
        if (not isinstance(data, bytes) or not data.startswith(b"%PDF-")
                or len(data) < 8 or len(data) > 12 * 1024 * 1024):
            raise ValueError("Malformed official PDF bytes")
        sha = hashlib.sha256(data).hexdigest()
        if sha != expected[ward]["sha256"] or len(data) != expected[ward]["byte_size"]:
            raise ValueError("Official PDF byte baseline mismatch; create a reviewed new baseline separately")
        sources.append({"ward": ward, "url": url, "sha256": sha})
        extracted = extractor(data, ward)
        if not isinstance(extracted, dict) or set(extracted) != set(BY_WARD[ward]):
            raise ValueError("Extractor did not return exact expected facility keys")
        for name, address in BY_WARD[ward]:
            digest = extracted[(name, address)]
            if digest is not None and (not isinstance(digest, str) or
                                       re.fullmatch(r"[0-9a-f]{64}", digest) is None):
                raise ValueError("Invalid extracted row fingerprint")
            findings.append({
                "ward": ward, "name": name, "address": address,
                "extract_status": "MATCHED" if digest else "UNRESOLVED",
                "row_text_sha256": digest,
            })
    result = {
        "schema_id": SCHEMA,
        "captured_at_utc": captured_at or utc_capture_time(),
        "safety": dict(SAFETY),
        "sources": sources,
        "facilities": findings,
    }
    validate_facility_snapshot(result)
    return result


def validate_facility_snapshot(data: dict) -> dict:
    if not isinstance(data, dict) or set(data) != {
        "schema_id", "captured_at_utc", "safety", "sources", "facilities"
    } or data["schema_id"] != SCHEMA or data["safety"] != SAFETY:
        raise ValueError("Invalid facility baseline contract or safety gate")
    instant = data["captured_at_utc"]
    if not isinstance(instant, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", instant):
        raise ValueError("Invalid capture timestamp")
    sources = data["sources"]
    if not isinstance(sources, list) or len(sources) != len(WATCH_SOURCES):
        raise ValueError("Wrong official PDF source count")
    for actual, (ward, url) in zip(sources, WATCH_SOURCES):
        if not isinstance(actual, dict) or set(actual) != {"ward", "url", "sha256"}:
            raise ValueError("Invalid official PDF source fields")
        if actual["ward"] != ward or actual["url"] != url or not isinstance(
                actual["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", actual["sha256"]):
            raise ValueError("Unauthorized PDF source or fingerprint")
    facilities = data["facilities"]
    if not isinstance(facilities, list) or len(facilities) != len(FACILITIES):
        raise ValueError("Wrong facility count")
    for rec, (ward, name, address) in zip(facilities, FACILITIES):
        if not isinstance(rec, dict) or set(rec) != {
            "ward", "name", "address", "extract_status", "row_text_sha256"
        } or (rec["ward"], rec["name"], rec["address"]) != (ward, name, address):
            raise ValueError("Facility identity changed or reordered")
        if rec["extract_status"] not in OUTCOMES:
            raise ValueError("Unexpected extraction status")
        digest = rec["row_text_sha256"]
        if (rec["extract_status"] == "MATCHED") != (
                isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None):
            raise ValueError("Extraction status or digest invalid")
    return data


def compare_facility_snapshots(old: dict, new: dict) -> dict:
    validate_facility_snapshot(old)
    validate_facility_snapshot(new)
    old_sources = {s["ward"]: s for s in old["sources"]}
    new_sources = {s["ward"]: s for s in new["sources"]}
    source_changed = {ward: old_sources[ward]["sha256"] != new_sources[ward]["sha256"]
                      for ward in old_sources}
    changes = []
    for a, b in zip(old["facilities"], new["facilities"]):
        ward = a["ward"]
        if a["extract_status"] != "MATCHED" or b["extract_status"] != "MATCHED":
            state = UNRESOLVED
        elif not source_changed[ward]:
            state = SOURCE_UNCHANGED if a["row_text_sha256"] == b["row_text_sha256"] else INCONSISTENT
        elif a["row_text_sha256"] != b["row_text_sha256"]:
            state = SOURCE_CHANGED_ROW_CHANGED
        else:
            state = SOURCE_CHANGED_ROW_UNCHANGED
        changes.append({
            "ward": ward, "name": a["name"], "address": a["address"],
            "source_url": next(url for w, url in WATCH_SOURCES if w == ward),
            "source_bytes_changed": source_changed[ward],
            "classification": state,
        })
    changed_rows = sum(r["classification"] == SOURCE_CHANGED_ROW_CHANGED for r in changes)
    unresolved = sum(r["classification"] in (UNRESOLVED, INCONSISTENT) for r in changes)
    human_review = sum(r["classification"] != SOURCE_UNCHANGED for r in changes)
    return {
        "report_kind": "NAGOYA_P1_PDF_ROW_DIFF_CANDIDATES_NOT_OFFICIAL_APPROVAL",
        "status": "HUMAN_REVIEW_REQUIRED" if human_review else "EXTRACTED_ROW_TEXT_UNCHANGED_NOT_APPROVAL",
        "previous_captured_at_utc": old["captured_at_utc"],
        "current_captured_at_utc": new["captured_at_utc"],
        "source_changed_count": sum(source_changed.values()),
        "facility_count": len(changes),
        # Compare reports have classification, not extract_status. Expose the
        # real per-snapshot counts so CLI summaries never falsely show 0/9.
        "baseline_extract_matched_count": sum(
            r["extract_status"] == "MATCHED" for r in old["facilities"]),
        "current_extract_matched_count": sum(
            r["extract_status"] == "MATCHED" for r in new["facilities"]),
        "row_changed_candidate_count": changed_rows,
        "unresolved_extraction_count": unresolved,
        "human_review_required_count": human_review,
        "facilities": changes,
        "safety": dict(SAFETY),
        "warning": "Text-row comparison is a screening hint only. Revalidate official PDFs and independent physical site identity; no approval inferred.",
    }


def get_pdf_bytes() -> dict[str, bytes]:
    # Fixed allowlist, no user-specified remote URLs.
    return {ward: fetch_pdf(url) for ward, url in WATCH_SOURCES}


def local_output(folder: Path, filename: str) -> Path:
    if re.fullmatch(r"official_pdf_facility_(snapshot|comparison)(?:_[a-z0-9_]+)?_LOCAL\.json",
                    filename) is None:
        raise ValueError("Only official_pdf_facility_*_LOCAL.json basename allowed")
    return folder / filename


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", required=True, choices=["baseline", "compare"])
    p.add_argument("--pilot-dir", required=True, type=Path)
    p.add_argument("--raw-baseline-name", default="official_pdf_snapshot_LOCAL.json")
    p.add_argument("--facility-baseline-name", default="official_pdf_facility_snapshot_LOCAL.json")
    p.add_argument("--output-name")
    args = p.parse_args()
    root = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    folder = args.pilot_dir.resolve()
    if root not in folder.parents or not folder.is_dir():
        p.error("Only existing local geocoding pilot subdirectories may be used")
    try:
        output = local_output(folder, args.output_name or
                              ("official_pdf_facility_snapshot_LOCAL.json"
                               if args.mode == "baseline"
                               else "official_pdf_facility_comparison_LOCAL.json"))
        if output.exists():
            raise ValueError("Output exists; refusing to overwrite previous reviewer evidence")
        if args.mode == "baseline":
            raw_path = raw_basename(folder, args.raw_baseline_name)
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            result = make_facility_snapshot(raw, get_pdf_bytes())
        else:
            previous_path = local_output(folder, args.facility_baseline_name)
            previous = json.loads(previous_path.read_text(encoding="utf-8"))
            validate_facility_snapshot(previous)
            pdf_data = get_pdf_bytes()
            # Every comparison capture is valid in its own right; previous PDFs
            # cannot be required to match after a genuine source-byte revision.
            current_source = capture_snapshot(lambda url: pdf_data[
                next(w for w, u in WATCH_SOURCES if u == url)])
            result = compare_facility_snapshots(
                previous, make_facility_snapshot(current_source, pdf_data))
        with output.open("x", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        p.exit(1, "Facility PDF triage aborted: " + reason
               + ". No previous local file overwritten or facility approved.\n")
    # Snapshot rows have extract_status, comparison rows have classification.
    # Never silently turn missing extract_status into a false zero count.
    matched = (sum(x["extract_status"] == "MATCHED" for x in result["facilities"])
               if args.mode == "baseline"
               else result["current_extract_matched_count"])
    print(json.dumps({
        "report_kind": result.get("report_kind", "NAGOYA_P1_PDF_ROW_BASELINE_UNREVIEWED"),
        "facility_count": len(result["facilities"]),
        "extract_matched_count": matched,
        "baseline_extract_matched_count": result.get("baseline_extract_matched_count"),
        "current_extract_matched_count": result.get("current_extract_matched_count"),
        "status": result.get("status", "BASELINE_UNREVIEWED"),
        "row_changed_candidate_count": result.get("row_changed_candidate_count"),
        "human_review_required_count": result.get("human_review_required_count"),
        "approved_for_map": False, "data_promotion_authorized": False,
        "official_facility_positions_accepted": 0,
        "output_is_local_only": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
