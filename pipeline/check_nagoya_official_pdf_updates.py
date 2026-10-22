"""Fail-closed, operator-run byte-change watch for five public Nagoya ward PDFs.

Offline tests never call the network. Real HTTPS collection occurs only when the
operator explicitly invokes --mode baseline or compare. This does NOT parse
content, approve official meaning, identify a physical site, evaluate shelter
safety/opening, publish data, or promote coordinates. SHA equality means that
the fetched bytes match a previous local observation and NOTHING MORE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import HTTPRedirectHandler, Request, build_opener

from nagoya_team_review_official_sources import OFFICIAL_INDEX_AS_OF, WARD_PDFS

SCHEMA_ID = "hinanex.nagoya-official-pdf-byte-watch.v1"
WATCH_SOURCES = tuple(sorted(WARD_PDFS.items()))
MAX_BYTES = 12 * 1024 * 1024
SAFETY = {
    "approved_for_map": False,
    "data_promotion_authorized": False,
    "official_facility_positions_accepted": 0,
}
CHANGED_STATUS = "SOURCE_BYTES_CHANGED_REVIEW_REQUIRED"
UNCHANGED_STATUS = "SOURCE_BYTES_UNCHANGED_CONTENT_NOT_VERIFIED"


class NoRedirect(HTTPRedirectHandler):
    """Do not silently follow a changed origin or file location."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("OFFICIAL_SOURCE_REDIRECT_REQUIRES_REVIEW")


def fetch_pdf(url: str) -> bytes:
    # Fixed allowlist, not an arbitrary URL supplied by JSON or CLI.
    if url not in WARD_PDFS.values():
        raise ValueError("PDF URL is not in the pinned official allowlist")
    opener = build_opener(NoRedirect)
    req = Request(url, headers={
        "User-Agent": "HINANEX-OfficialSourceBytesAudit/1.0 (manual review only)",
        "Accept": "application/pdf",
    })
    with opener.open(req, timeout=20) as response:
        if response.status != 200 or response.url != url:
            raise ValueError("Unexpected HTTP response or source URL")
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type not in ("application/pdf", "application/octet-stream"):
            raise ValueError("Unexpected MIME type for official PDF")
        data = response.read(MAX_BYTES + 1)
    if len(data) < 8 or len(data) > MAX_BYTES or not data.startswith(b"%PDF-"):
        raise ValueError("Unexpected or oversized official PDF body")
    return data


def utc_capture_time() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def capture_snapshot(fetcher=fetch_pdf, captured_at: str | None = None) -> dict:
    rows = []
    # No partial publication. One failed official download aborts all five.
    for ward, url in WATCH_SOURCES:
        payload = fetcher(url)
        if not isinstance(payload, bytes) or len(payload) < 8 or len(payload) > MAX_BYTES or not payload.startswith(b"%PDF-"):
            raise ValueError("Official-source PDF validation failed")
        rows.append({
            "ward": ward,
            "url": url,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "byte_size": len(payload),
        })
    result = {
        "schema_id": SCHEMA_ID,
        "source_list_as_of": OFFICIAL_INDEX_AS_OF,
        "captured_at_utc": captured_at or utc_capture_time(),
        "safety": dict(SAFETY),
        "sources": rows,
    }
    validate_snapshot(result)
    return result


def validate_snapshot(s: dict) -> dict:
    if not isinstance(s, dict) or set(s) != {
        "schema_id", "source_list_as_of", "captured_at_utc", "safety", "sources"
    }:
        raise ValueError("Snapshot structure mismatch")
    if s["schema_id"] != SCHEMA_ID or s["source_list_as_of"] != OFFICIAL_INDEX_AS_OF:
        raise ValueError("Unrecognized source-watch schema or source-list date")
    if not isinstance(s["safety"], dict) or s["safety"] != SAFETY:
        raise ValueError("Snapshot safety flags changed")
    instant = s["captured_at_utc"]
    if not isinstance(instant, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", instant):
        raise ValueError("Snapshot capture timestamp malformed")
    try:
        datetime.fromisoformat(instant.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid UTC capture time") from exc
    sources = s["sources"]
    if not isinstance(sources, list) or len(sources) != len(WATCH_SOURCES):
        raise ValueError("Wrong number of official sources")
    for row, (ward, url) in zip(sources, WATCH_SOURCES):
        if not isinstance(row, dict) or set(row) != {"ward", "url", "sha256", "byte_size"}:
            raise ValueError("Source record has invalid fields")
        if row["ward"] != ward or row["url"] != url:
            raise ValueError("Unexpected official source or ordering")
        if not isinstance(row["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError("Malformed raw-byte SHA")
        if (type(row["byte_size"]) is not int
                or not 8 <= row["byte_size"] <= MAX_BYTES):
            raise ValueError("Malformed raw-byte length")
    return s


def compare_snapshots(previous: dict, current: dict) -> dict:
    validate_snapshot(previous)
    validate_snapshot(current)
    diffs = []
    for old, new in zip(previous["sources"], current["sources"]):
        changed = (old["sha256"] != new["sha256"] or old["byte_size"] != new["byte_size"])
        diffs.append({
            "ward": old["ward"],
            "url": old["url"],
            "raw_bytes_changed": changed,
            "previous_sha256": old["sha256"],
            "current_sha256": new["sha256"],
            "previous_byte_size": old["byte_size"],
            "current_byte_size": new["byte_size"],
        })
    changed_count = sum(item["raw_bytes_changed"] for item in diffs)
    return {
        "report_kind": "NAGOYA_PUBLIC_PDF_BYTE_COMPARISON_NOT_SITE_APPROVAL",
        "status": CHANGED_STATUS if changed_count else UNCHANGED_STATUS,
        "source_list_as_of": OFFICIAL_INDEX_AS_OF,
        "previous_captured_at_utc": previous["captured_at_utc"],
        "current_captured_at_utc": current["captured_at_utc"],
        "changed_source_count": changed_count,
        "sources": diffs,
        "safety": dict(SAFETY),
        "human_original_content_review_required": bool(changed_count),
        "official_site_position_human_review_completed": False,
        "shelter_opening_or_disaster_safety_evaluated": False,
        "warning": "Byte-level comparison alone cannot establish official meaning, facility identity, location, opening, or safety.",
    }


def local_file(folder: Path, basename: str) -> Path:
    if re.fullmatch(r"official_pdf_(snapshot|comparison)_[a-z0-9_]*LOCAL\.json", basename) is None:
        raise ValueError("Output must be a local official_pdf_*_LOCAL.json basename")
    return folder / basename


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=["baseline", "compare"])
    parser.add_argument("--pilot-dir", required=True, type=Path)
    parser.add_argument("--baseline-name", default="official_pdf_snapshot_LOCAL.json")
    parser.add_argument("--output-name")
    args = parser.parse_args()
    root = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    folder = args.pilot_dir.resolve()
    if root not in folder.parents:
        parser.error("Only a dedicated gitignored local pilot subdirectory is accepted")
    if not folder.is_dir():
        parser.error("Local pilot directory does not exist")
    try:
        baseline_path = local_file(folder, args.baseline_name)
        name = args.output_name or (
            "official_pdf_snapshot_LOCAL.json" if args.mode == "baseline"
            else "official_pdf_comparison_LOCAL.json")
        output = local_file(folder, name)
        if output.exists():
            raise ValueError("Output exists; refusing to overwrite any prior audit or review")
        if args.mode == "baseline":
            if name == args.baseline_name and baseline_path.exists():
                raise ValueError("Baseline exists; refusing to overwrite it")
            result = capture_snapshot()
        else:
            if not baseline_path.is_file():
                raise ValueError("Baseline missing; no implicit baseline acceptance")
            previous = json.loads(baseline_path.read_text(encoding="utf-8"))
            validate_snapshot(previous)
            current = capture_snapshot()
            result = compare_snapshots(previous, current)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        # ValueError messages are locally authored guard reasons; don't print
        # unexpected HTTP exception details, PRIVATE local paths or raw content.
        detail = str(exc) if type(exc) is ValueError else type(exc).__name__
        parser.exit(1, "Official PDF watch aborted: " + detail
                    + ". No source accepted or promoted; local prior files unchanged.\n")
    # Do not print raw document content, URL-bearing evidence or facility records.
    print(json.dumps({
        "report_kind": result.get("report_kind", "NAGOYA_OFFICIAL_PDF_BASELINE_UNREVIEWED"),
        "status": result.get("status", "BASELINE_CAPTURED_UNREVIEWED"),
        "source_count": len(result["sources"]),
        "changed_source_count": result.get("changed_source_count"),
        "official_facility_positions_accepted": 0,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "output_is_local_only": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
