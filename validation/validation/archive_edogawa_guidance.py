"""Archive two Edogawa official water-evacuation guidance pages as separate evidence.

This is supplemental documentation, NOT a flood-only designation, live
opening status, school identity acceptance, or extension to the fixed 7-source
identity archive. Save raw evidence outside the repository.

  python validation/validation/archive_edogawa_guidance.py --out-dir /external/guidance-20261013
  python validation/validation/archive_edogawa_guidance.py --verify-dir /external/guidance-20261013
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit

from archive_edogawa_official_sources import (
    MAX_RAW_BYTES, SnapshotFailure, ensure_trusted_url, official_fetch,
)

GUIDANCE = {
    "municipal_water_evacuation_guidance": (
        "water_evacuation_guidance.html",
        "https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/"
        "kanrenmap/hazardmap/suigaihinan.html",
        ("待避施設", "避難する時間がない", "浸水"),
    ),
    "municipal_weather_evacuation_operations": (
        "weather_evacuation_operations.html",
        "https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/"
        "jijo/suigaihinan.html",
        ("風水害第二次態勢", "災害対策本部", "待避施設"),
    ),
}
PURPOSE = "C_EDOGAWA_GUIDANCE_ORIGINAL_BYTES_UNREVIEWED"


class GuidanceFailure(ValueError):
    pass


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.words = []
        self.skipped = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "template"}:
            self.skipped += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "template"} and self.skipped:
            self.skipped -= 1

    def handle_data(self, data):
        if not self.skipped:
            self.words.append(data)


def verify_html(raw, key):
    if (not raw or b"<html" not in raw.lower() or
            b"<body" not in raw.lower()):
        raise GuidanceFailure(key + ": HTTP 200 body is not recognizable HTML")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise GuidanceFailure(key + ": original encoding is unexpected") from exc
    parser = PlainText()
    parser.feed(decoded)
    visible = " ".join(parser.words)
    for expected in GUIDANCE[key][2]:
        if expected not in visible:
            raise GuidanceFailure(key + ": missing official context marker " + expected)


def capture(out_dir, fetch=official_fetch, now=None):
    folder = Path(out_dir)
    if folder.is_symlink() or (folder.exists() and
       (not folder.is_dir() or any(folder.iterdir()))):
        raise GuidanceFailure("Guidance output directory must be new or empty")
    snapshots = []
    for key, (filename, url, _) in GUIDANCE.items():
        ensure_trusted_url(url)
        try:
            raw, final_url, headers = fetch(url)
            ensure_trusted_url(final_url)
            if urlsplit(final_url).hostname != urlsplit(url).hostname:
                raise GuidanceFailure("Official guidance redirected to another publisher")
            if (not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RAW_BYTES
                    or not isinstance(headers, dict)):
                raise GuidanceFailure("Invalid official guidance HTTP response")
            verify_html(raw, key)
        except SnapshotFailure as exc:
            raise GuidanceFailure(key + ": " + str(exc)) from exc
        snapshots.append((key, filename, url, raw, final_url, headers))
    manifest = {
        "purpose": PURPOSE,
        "captured_at_utc": (now or datetime.now(timezone.utc)).isoformat(),
        "official_publication_date_reviewed": False,
        "official_scope_and_flood_only_semantics_accepted": False,
        "human_c_reviewer_signed_off": False,
        "approved_cross_source_pairs": 0,
        "flood_classifications_added": 0,
        "source_items": [{
            "source_key": key,
            "requested_url": url,
            "final_url": final_url,
            "archive_filename": filename,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_size": len(raw),
            "http_content_type": headers.get("content_type"),
            "http_last_modified": headers.get("last_modified"),
            "http_etag": headers.get("etag"),
            "semantic_interpretation_status": "HUMAN_D_C_REVIEW_REQUIRED",
        } for key, filename, url, raw, final_url, headers in snapshots],
    }
    folder.mkdir(parents=True, exist_ok=True)
    for _, filename, _, raw, _, _ in snapshots:
        (folder / filename).write_bytes(raw)
    (folder / "guidance_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def verify(out_dir):
    folder = Path(out_dir)
    if folder.is_symlink() or not folder.is_dir():
        raise GuidanceFailure("Guidance directory missing or unsafe")
    expected_files = {"guidance_manifest.json"} | {
        item[0] for item in GUIDANCE.values()
    }
    if {p.name for p in folder.iterdir()} != expected_files:
        raise GuidanceFailure("Guidance original files missing or unexpected")
    path = folder / "guidance_manifest.json"
    if path.is_symlink() or not path.is_file():
        raise GuidanceFailure("Guidance manifest missing or unsafe")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        stamp = datetime.fromisoformat(manifest["captured_at_utc"])
        if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError("Guidance capture time must be UTC")
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise GuidanceFailure("Guidance manifest invalid") from exc
    if (manifest.get("purpose") != PURPOSE or
            manifest.get("official_publication_date_reviewed") is not False or
            manifest.get("official_scope_and_flood_only_semantics_accepted") is not False or
            manifest.get("human_c_reviewer_signed_off") is not False or
            manifest.get("approved_cross_source_pairs") != 0 or
            manifest.get("flood_classifications_added") != 0):
        raise GuidanceFailure("Guidance evidence pretends approval")
    items = manifest.get("source_items")
    if (not isinstance(items, list) or len(items) != len(GUIDANCE)
            or {i.get("source_key") for i in items if isinstance(i, dict)} != set(GUIDANCE)):
        raise GuidanceFailure("Guidance source set malformed/duplicated")
    for key, (filename, url, _) in GUIDANCE.items():
        item = next(i for i in items if i["source_key"] == key)
        final_url = item.get("final_url")
        try:
            ensure_trusted_url(final_url)
        except (SnapshotFailure, TypeError) as exc:
            raise GuidanceFailure("Guidance final URL unsafe") from exc
        if (item.get("archive_filename") != filename or
                item.get("requested_url") != url or
                urlsplit(final_url).hostname != urlsplit(url).hostname or
                item.get("semantic_interpretation_status") != "HUMAN_D_C_REVIEW_REQUIRED"):
            raise GuidanceFailure("Guidance provenance changed")
        original_path = folder / filename
        if original_path.is_symlink() or not original_path.is_file():
            raise GuidanceFailure("Guidance raw original missing/unsafe")
        raw = original_path.read_bytes()
        if (type(item.get("byte_size")) is not int or
                item["byte_size"] != len(raw) or
                not 0 < len(raw) <= MAX_RAW_BYTES or
                item.get("sha256") != hashlib.sha256(raw).hexdigest()):
            raise GuidanceFailure("Guidance original byte SHA256 mismatch")
        verify_html(raw, key)
    return {
        "status": "GUIDANCE_ORIGINAL_BYTES_VERIFIED_HUMAN_D_C_REVIEW_REQUIRED",
        "source_count": len(GUIDANCE),
        "guidance_sha256": {i["source_key"]: i["sha256"] for i in items},
        "official_scope_and_flood_only_semantics_accepted": False,
        "human_c_reviewer_signed_off": False,
        "approved_cross_source_pairs": 0,
        "flood_classifications_added": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out-dir", type=Path)
    group.add_argument("--verify-dir", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.verify_dir) if args.verify_dir else capture(args.out_dir)
    except (GuidanceFailure, SnapshotFailure, OSError) as exc:
        parser.exit(2, "C guidance evidence rejected: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
