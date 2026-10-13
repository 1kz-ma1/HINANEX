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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = capture(args.out_dir)
    except (OSError, SnapshotFailure) as exc:
        parser.exit(2, "Snapshot capture failed; no C approval: " + str(exc) + "\n")
    print(json.dumps({
        "status": result["purpose"],
        "sources_archived": len(result["source_items"]),
        "human_c_reviewer_signed_off": False,
        "manifest": str(args.out_dir / "snapshot_manifest.json"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
