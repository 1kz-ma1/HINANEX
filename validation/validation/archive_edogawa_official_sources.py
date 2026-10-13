"""C-only official HTTP snapshot collector for Edogawa identity review.

This program captures original HTTP response bytes plus HTTP provenance.
It does *not* attest publisher authenticity, cross-source identity, city
hazard meaning, accessibility, opening state or site safety.

Run from repo root:
  python validation/validation/archive_edogawa_official_sources.py \
    --out-dir "C:\\HINANEX-evidence\\official-20261013"

Do not commit the output raw data or manifest into HINANEX Git.
A human C reviewer must still independently inspect both raw bytes and
the fact that each URL actually represents the intended institution.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SOURCES = {
    "water_facilities": (
        "water_facilities.html",
        "https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/"
        "kanrenmap/hazardmap/ikinaihinan.html",
    ),
    "municipal_locations": (
        "municipal_locations.csv",
        "https://www.city.edogawa.tokyo.jp/documents/4408/20251211_hinanhokan.csv",
    ),
    "municipal_school_list": (
        "municipal_school_list.html",
        "https://www.city.edogawa.tokyo.jp/e004/kuseijoho/gaiyo/"
        "shisetsuguide/bunya/gakko/toritsushiritsu.html",
    ),
    "municipal_primary_school_list": (
        "municipal_primary_school_list.html",
        "https://www.city.edogawa.tokyo.jp/e068/kuseijoho/gaiyo/"
        "shisetsuguide/bunya/gakko/shogakko.html",
    ),
    "municipal_2025_school_relocation": (
        "municipal_2025_school_relocation.html",
        "https://www.city.edogawa.tokyo.jp/e004/kuseijoho/"
        "kohokocho/press/2025/04/0421.html",
    ),
    "tokyo_kasaikoka_school_access": (
        "tokyo_kasaikoka_school_access.html",
        "https://www.metro.ed.jp/kasaikoka-h/access/access.html",
    ),
    "kanto_ichiko_school_overview": (
        "kanto_ichiko_school_overview.html",
        "https://www.kanto-ichiko.ac.jp/about/outline/",
    ),
}
TRUSTED_HOSTS = {
    "www.city.edogawa.tokyo.jp",
    "www.metro.ed.jp",
    "www.kanto-ichiko.ac.jp",
}
MAX_RAW_BYTES = 8_000_000


class SnapshotFailure(RuntimeError):
    pass


def ensure_trusted_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or
            parsed.hostname not in TRUSTED_HOSTS or
            parsed.username is not None or parsed.password is not None or
            parsed.port not in (None, 443)):
        raise SnapshotFailure("Untrusted or non-HTTPS source URL: " + str(url))


def official_fetch(url, timeout=25):
    ensure_trusted_url(url)
    req = Request(url, headers={"User-Agent": "HINANEX-C-evidence-archive/1.0"})
    with urlopen(req, timeout=timeout) as response:
        status = response.getcode()
        final_url = response.geturl()
        ensure_trusted_url(final_url)
        if status != 200:
            raise SnapshotFailure(f"HTTP {status}: {url}")
        raw = response.read(MAX_RAW_BYTES + 1)
        if not raw or len(raw) > MAX_RAW_BYTES:
            raise SnapshotFailure("Empty or over-size official response: " + url)
        return raw, final_url, {
            "content_type": response.headers.get("Content-Type"),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
        }


def capture(out_dir: Path, fetch=official_fetch, now=None):
    """Fetch all HTTPS sources before writing anything; fail without partial manifest."""
    out_dir = Path(out_dir)
    if out_dir.exists():
        if not out_dir.is_dir():
            raise SnapshotFailure("Destination is not a directory")
        if any(out_dir.iterdir()):
            raise SnapshotFailure("Output directory must be empty; use a new versioned folder")

    downloaded = []
    for name, (filename, url) in SOURCES.items():
        ensure_trusted_url(url)
        raw, final_url, headers = fetch(url)
        ensure_trusted_url(final_url)
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_RAW_BYTES:
            raise SnapshotFailure(f"Source has no acceptable response bytes: {name}")
        if not isinstance(headers, dict):
            raise SnapshotFailure(f"Malformed response headers: {name}")
        downloaded.append((name, filename, url, raw, final_url, headers))

    captured_at = (now or datetime.now(timezone.utc)).isoformat()
    manifest = {
        "purpose": "C_EVIDENCE_ARCHIVE_ONLY_NO_C_INDEPENDENT_ACCEPTANCE",
        "captured_at_utc": captured_at,
        "http_content_is_not_facility_identity": True,
        "flood_scenario_classifications_added": 0,
        "human_c_reviewer_signed_off": False,
        "source_items": [{
            "source_key": name,
            "requested_url": url,
            "final_url": final_url,
            "archive_filename": filename,
            "byte_size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "http_content_type": headers.get("content_type"),
            "http_last_modified": headers.get("last_modified"),
            "http_etag": headers.get("etag"),
            "official_publication_or_effective_date": None,
            "date_context_review_required": True,
        } for name, filename, url, raw, final_url, headers in downloaded],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    for _, filename, _, raw, _, _ in downloaded:
        (out_dir / filename).write_bytes(raw)
    (out_dir / "snapshot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest



def verify_snapshot(out_dir: Path):
    """Re-check stored byte/manifest consistency. Never approve facilities.

    A digest stored beside its bytes cannot independently prove publisher
    authenticity: C must retain a separately trusted copy of source hashes.
    """
    out_dir = Path(out_dir)
    if out_dir.is_symlink() or not out_dir.is_dir():
        raise SnapshotFailure("Snapshot directory is missing or is a symbolic link")
    manifest_file = out_dir / "snapshot_manifest.json"
    if manifest_file.is_symlink() or not manifest_file.is_file():
        raise SnapshotFailure("Snapshot manifest missing or unsafe")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError, OSError) as exc:
        raise SnapshotFailure("Snapshot manifest is unreadable") from exc

    if not isinstance(manifest, dict):
        raise SnapshotFailure("Snapshot manifest must be an object")
    if (manifest.get("purpose") !=
            "C_EVIDENCE_ARCHIVE_ONLY_NO_C_INDEPENDENT_ACCEPTANCE" or
            manifest.get("human_c_reviewer_signed_off") is not False or
            manifest.get("http_content_is_not_facility_identity") is not True or
            type(manifest.get("flood_scenario_classifications_added")) is not int or
            manifest["flood_scenario_classifications_added"] != 0):
        raise SnapshotFailure("Snapshot improperly claims identity or classification")

    timestamp = manifest.get("captured_at_utc")
    if not isinstance(timestamp, str):
        raise SnapshotFailure("Snapshot capture time missing")
    try:
        parsed_time = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise SnapshotFailure("Snapshot capture time malformed") from exc
    if parsed_time.utcoffset() is None or parsed_time.utcoffset().total_seconds() != 0:
        raise SnapshotFailure("Snapshot capture time must be UTC")

    items = manifest.get("source_items")
    if not isinstance(items, list) or len(items) != len(SOURCES):
        raise SnapshotFailure("Missing or extra official source entries")
    indexed = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("source_key"), str):
            raise SnapshotFailure("Malformed source item")
        key = item["source_key"]
        if key not in SOURCES or key in indexed:
            raise SnapshotFailure("Unknown or duplicate source item")
        indexed[key] = item
    if set(indexed) != set(SOURCES):
        raise SnapshotFailure("Incomplete official source set")

    expected_files = {"snapshot_manifest.json"} | {
        filename for filename, _ in SOURCES.values()
    }
    if {entry.name for entry in out_dir.iterdir()} != expected_files:
        raise SnapshotFailure("Snapshot directory contains missing or unexpected files")

    total_bytes = 0
    for key, (filename, requested_url) in SOURCES.items():
        item = indexed[key]
        if item.get("archive_filename") != filename or item.get("requested_url") != requested_url:
            raise SnapshotFailure("Snapshot source name or requested URL differs: " + key)
        final_url = item.get("final_url")
        if not isinstance(final_url, str):
            raise SnapshotFailure("Final source URL missing: " + key)
        ensure_trusted_url(final_url)
        if urlsplit(final_url).hostname != urlsplit(requested_url).hostname:
            raise SnapshotFailure("Source redirected to another publisher host: " + key)
        if (item.get("date_context_review_required") is not True or
                item.get("official_publication_or_effective_date") is not None):
            raise SnapshotFailure("Official effective date was asserted without review: " + key)
        file_path = out_dir / filename
        if file_path.is_symlink() or not file_path.is_file():
            raise SnapshotFailure("Source file missing or unsafe: " + key)
        raw = file_path.read_bytes()
        declared_size = item.get("byte_size")
        declared_sha = item.get("sha256")
        if (type(declared_size) is not int or
                declared_size != len(raw) or
                not 0 < declared_size <= MAX_RAW_BYTES or
                not isinstance(declared_sha, str) or
                declared_sha != hashlib.sha256(raw).hexdigest()):
            raise SnapshotFailure("Original source bytes/digest inconsistent: " + key)
        total_bytes += len(raw)

    return {
        "status": "ARCHIVE_BYTES_CONSISTENT_REVIEW_REQUIRED",
        "sources_verified": len(SOURCES),
        "source_bytes_verified": total_bytes,
        "human_c_reviewer_signed_off": False,
        "approved_cross_source_pairs": 0,
        "flood_scenario_classifications_added": 0,
        "publisher_authenticity_independently_attested": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--out-dir", type=Path, help="Fetch to a new empty directory")
    command.add_argument("--verify-dir", type=Path, help="Offline verify archived bytes")
    args = parser.parse_args()
    try:
        if args.verify_dir is not None:
            summary = verify_snapshot(args.verify_dir)
        else:
            result = capture(args.out_dir)
            summary = {
                "status": result["purpose"],
                "sources_archived": len(result["source_items"]),
                "human_c_reviewer_signed_off": False,
                "manifest": str(args.out_dir / "snapshot_manifest.json"),
            }
    except (OSError, SnapshotFailure) as exc:
        parser.exit(2, "Snapshot operation failed; no C approval: " + str(exc) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
