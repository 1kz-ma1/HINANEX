"""A-only source archive: official Edogawa school relocation/merger timelines.

Never use this archive to approve a D location, select an evacuation facility,
alter a flood Scenario, or reinterpret a historical water-facility source.
The municipal publisher's current HTML pages and historical PDF versions
are independent records; their dates and scopes require HUMAN review.

python data-research/tools/archive_edogawa_campus_history.py --out-dir /external/school-history
python data-research/tools/archive_edogawa_campus_history.py --verify-dir /external/school-history
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

OFFICIAL_HOST = "www.city.edogawa.tokyo.jp"
PREFIX = "https://" + OFFICIAL_HOST
MAX_BYTES = 9_000_000
PURPOSE = "A_EDOGAWA_CAMPUS_TIMELINE_ORIGINAL_BYTES_UNAPPROVED"

# Publisher URL, independent document role and content markers.
# PDF authenticity/content must be human inspected; magic bytes alone do NOT
# validate individual address or relocation claims contained in the PDF.
SOURCES = {
    "hirai_minami_rebuild": (
        "hirai_minami_rebuild.html",
        PREFIX + "/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/hiraiminamisyo.html",
        "html", ("平井南小学校", "旧小松川第三中学校", "令和11年9月"),
    ),
    "edogawa_school_rebuild_index": (
        "school_rebuild_overview.html",
        PREFIX + "/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/kaichikugaiyo.html",
        "html", ("平井南小学校", "平井5丁目3番11号"),
    ),
    "shimokamata_rebuild": (
        "shimokamata_rebuild.html",
        PREFIX + "/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/shimokamatatougoukou.html",
        "html", ("下鎌田小学校", "下鎌田西小学校", "令和7年9月"),
    ),
    "shimokamata_integration": (
        "shimokamata_integration.html",
        PREFIX + "/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/togo/shimokamatachiiki.html",
        "html", ("下鎌田小学校", "下鎌田西小学校", "令和5年4月"),
    ),
    "school_district_map_guidance": (
        "school_district_2025.html",
        PREFIX + "/e069/kosodate/kyoiku/kyouiku/shisetuitiran/syogakko/kuikizu.html",
        "html", ("下鎌田小学校", "東瑞江3丁目11番1号", "令和7年9月"),
    ),
    "historical_shimokamata_site_plan_2021": (
        "shimokamata_2021_campus_plan.pdf",
        PREFIX + "/documents/21357/shimokamatasyo.pdf",
        "pdf", (),
    ),
    "historical_hirai_board_minutes_2024": (
        "hirai_2024_school_board_minutes.pdf",
        PREFIX + "/documents/57803/r6-20gijiroku.pdf",
        "pdf", (),
    ),
}
APPROVAL_FLAGS = {
    "school_campus_identity_human_approved": False,
    "school_campus_effective_date_human_approved": False,
    "water_facility_site_link_human_approved": False,
    "flood_only_semantics_human_approved": False,
    "approved_cross_source_pairs": 0,
    "flood_scenario_classifications_added": 0,
}


class CampusArchiveFailure(ValueError):
    pass


class Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.invisible = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "template"}:
            self.invisible += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "template"} and self.invisible:
            self.invisible -= 1

    def handle_data(self, data):
        if not self.invisible:
            self.parts.append(data)


def official_url(url):
    if not isinstance(url, str):
        raise CampusArchiveFailure("Invalid source URL type")
    x = urlsplit(url)
    if (x.scheme != "https" or x.hostname != OFFICIAL_HOST or
            x.username is not None or x.password is not None or
            x.port not in (None, 443) or x.fragment or x.query):
        raise CampusArchiveFailure("Untrusted source URL")


def validate_body(source, raw):
    _, _, kind, markers = SOURCES[source]
    if not isinstance(raw, bytes) or not 100 < len(raw) <= MAX_BYTES:
        raise CampusArchiveFailure("Missing/oversized official source " + source)
    if kind == "pdf":
        # PDF structure and page content are for manual verification.
        if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-2048:]:
            raise CampusArchiveFailure("Official PDF bytes do not look like a PDF")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeError as exc:
            raise CampusArchiveFailure("Official HTML encoding changed") from exc
        if "<html" not in text.lower() or "<body" not in text.lower():
            raise CampusArchiveFailure("Official source is not recognizable HTML")
        parser = Visible()
        parser.feed(text)
        visible = " ".join(parser.parts)
        for marker in markers:
            if marker not in visible:
                raise CampusArchiveFailure(
                    "Official source missing school timeline context: " + source +
                    " / " + marker
                )


def fetch(url, timeout=40):
    official_url(url)
    req = Request(url, headers={"User-Agent": "HINANEX-A-campus-evidence/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        final = resp.geturl()
        official_url(final)
        if urlsplit(final).hostname != urlsplit(url).hostname or resp.status != 200:
            raise CampusArchiveFailure("Official publisher/HTTP response changed")
        raw = resp.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise CampusArchiveFailure("Publisher response over maximum size")
        return raw, final, {
            "content_type": resp.headers.get("Content-Type"),
            "last_modified": resp.headers.get("Last-Modified"),
            "etag": resp.headers.get("ETag"),
        }


def capture(dest, downloader=fetch, at=None):
    dest = Path(dest)
    if dest.is_symlink() or (dest.exists() and
       (not dest.is_dir() or any(dest.iterdir()))):
        raise CampusArchiveFailure("Destination must be new/empty")
    downloaded = []
    for key, (filename, url, kind, _) in SOURCES.items():
        official_url(url)
        raw, final, headers = downloader(url)
        official_url(final)
        if urlsplit(final).hostname != urlsplit(url).hostname:
            raise CampusArchiveFailure("Official source moved to another publisher")
        if not isinstance(headers, dict):
            raise CampusArchiveFailure("Official HTTP headers missing")
        validate_body(key, raw)
        downloaded.append((key, filename, url, kind, raw, final, headers))
    timestamp = at or datetime.now(timezone.utc)
    if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
        raise CampusArchiveFailure("Capture timestamp must be UTC")
    manifest = {
        "purpose": PURPOSE,
        "captured_at_utc": timestamp.isoformat(),
        "official_publication_and_effective_dates_human_reviewed": False,
        "pdf_campus_map_and_meeting_context_human_review_required": True,
        **APPROVAL_FLAGS,
        "source_items": [{
            "source_key": key,
            "archive_filename": fn,
            "requested_url": url,
            "final_url": final,
            "document_format": kind,
            "byte_size": len(raw),
            "sha256": sha256(raw).hexdigest(),
            "http_content_type": headers.get("content_type"),
            "http_last_modified": headers.get("last_modified"),
            "http_etag": headers.get("etag"),
            "reported_page_update_date_not_equivalent_to_effective_date": True,
        } for key, fn, url, kind, raw, final, headers in downloaded],
    }
    dest.mkdir(parents=True, exist_ok=True)
    for _, filename, _, _, raw, _, _ in downloaded:
        (dest / filename).write_bytes(raw)
    (dest / "campus_history_manifest_UNAPPROVED.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def verify(folder):
    folder = Path(folder)
    if folder.is_symlink() or not folder.is_dir():
        raise CampusArchiveFailure("Archive missing or unsafe")
    manifest_path = folder / "campus_history_manifest_UNAPPROVED.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CampusArchiveFailure("Manifest missing")
    try:
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        t = datetime.fromisoformat(m["captured_at_utc"])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise CampusArchiveFailure("Invalid provenance manifest") from exc
    if t.utcoffset() is None or t.utcoffset().total_seconds() != 0:
        raise CampusArchiveFailure("Archive timestamp is not UTC")
    if (m.get("purpose") != PURPOSE or
            m.get("official_publication_and_effective_dates_human_reviewed") is not False or
            m.get("pdf_campus_map_and_meeting_context_human_review_required") is not True or
            any(m.get(k) != v or type(m.get(k)) is not type(v)
                for k, v in APPROVAL_FLAGS.items())):
        raise CampusArchiveFailure("Archive claims false site or flood approvals")
    entries = m.get("source_items")
    if not isinstance(entries, list) or len(entries) != len(SOURCES):
        raise CampusArchiveFailure("Archive original source count mismatch")
    expected = {"campus_history_manifest_UNAPPROVED.json"} | {
        x[0] for x in SOURCES.values()
    }
    if {p.name for p in folder.iterdir()} != expected:
        raise CampusArchiveFailure("Archive unexpected/missing source file")
    observed = set()
    for item in entries:
        if not isinstance(item, dict):
            raise CampusArchiveFailure("Invalid original file manifest entry")
        key = item.get("source_key")
        if key not in SOURCES or key in observed:
            raise CampusArchiveFailure("Duplicate or unknown official source key")
        observed.add(key)
        name, url, kind, _ = SOURCES[key]
        if (item.get("archive_filename") != name or
            item.get("requested_url") != url or
            item.get("document_format") != kind or
            item.get("reported_page_update_date_not_equivalent_to_effective_date") is not True):
            raise CampusArchiveFailure("Original source identity/version changed")
        official_url(item.get("final_url"))
        path = folder / name
        if path.is_symlink() or not path.is_file():
            raise CampusArchiveFailure("Original source is missing/unsafe")
        raw = path.read_bytes()
        if (type(item.get("byte_size")) is not int or
            len(raw) != item["byte_size"] or
            sha256(raw).hexdigest() != item.get("sha256")):
            raise CampusArchiveFailure("Original document SHA256 mismatch")
        validate_body(key, raw)
    return {
        "status": "A_CAMPUS_ORIGINAL_BYTES_VERIFIED_NO_SITE_OR_FLOOD_APPROVAL",
        "official_originals": len(SOURCES),
        "html_originals": sum(x[2] == "html" for x in SOURCES.values()),
        "pdf_originals": sum(x[2] == "pdf" for x in SOURCES.values()),
        "sha256": {x["source_key"]: x["sha256"] for x in entries},
        "human_approved_campus_pairs": 0,
        "new_flood_classifications": 0,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    flags = p.add_mutually_exclusive_group(required=True)
    flags.add_argument("--out-dir", type=Path)
    flags.add_argument("--verify-dir", type=Path)
    args = p.parse_args()
    try:
        result = verify(args.verify_dir) if args.verify_dir else capture(args.out_dir)
    except (OSError, CampusArchiveFailure) as exc:
        p.exit(2, "Campus history archive rejected: " + str(exc) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
