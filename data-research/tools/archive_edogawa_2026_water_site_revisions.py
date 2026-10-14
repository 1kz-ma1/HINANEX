"""A research-only: archive dated river/inland-water standby source revisions.

2026 municipal disaster-plan PDF is a DIFFERENT source version from the
2025-era water HTML. NEVER reinterpret a dated list as a current open refuge.
Archive outside Git; source dates, premises, address typos and legal status
need independent human C/D review.

python data-research/tools/archive_edogawa_2026_water_site_revisions.py --out-dir /external/edogawa-water-versions
python data-research/tools/archive_edogawa_2026_water_site_revisions.py --verify-dir /external/edogawa-water-versions
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

HOST = "www.city.edogawa.tokyo.jp"
ROOT = "https://" + HOST
PURPOSE = "A_EDOGAWA_2026_EXTERNAL_INTERNAL_WATER_SITE_ORIGINALS_UNAPPROVED"
SOURCES = {
    "2026_disaster_plan_original": (
        "2026_disaster_plan_external_internal_water.pdf",
        ROOT + "/documents/68931/00006.pdf", "pdf",
        (),
    ),
    "2025_old_shimokamata_reuse_notice": (
        "2025_old_shimokamata_afteruse.pdf",
        ROOT + "/documents/40376/0704simokamata_1.pdf", "pdf",
        (),
    ),
    "2026_school_afteruse_page": (
        "school_afteruse_page.html",
        ROOT + "/e085/kuseijoho/zaisei/kokyoshisetsu/rikatuyou.html", "html",
        ("統廃合後の学校後利用", "旧下鎌田小学校"),
    ),
}
MAX_BYTES = 16_000_000
NO_APPROVAL = {
    "school_building_or_premises_identity_human_approved": False,
    "official_document_effective_date_human_approved": False,
    "external_vs_internal_flood_semantics_human_approved": False,
    "campus_to_d_identity_human_approved": False,
    "human_c_site_pairs_approved": 0,
    "new_flood_scenario_classifications": 0,
}


class ArchiveFailure(ValueError):
    pass


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "template"):
            self.ignore += 1

    def handle_endtag(self, tag):
        if tag in ("style", "script", "template") and self.ignore:
            self.ignore -= 1

    def handle_data(self, text):
        if not self.ignore:
            self.parts.append(text)


def require_official(url):
    if not isinstance(url, str):
        raise ArchiveFailure("Bad official URL type")
    u = urlsplit(url)
    if (u.scheme != "https" or u.hostname != HOST or u.port not in (None, 443)
        or u.username or u.password or u.fragment or u.query):
        raise ArchiveFailure("Untrusted municipal source URL")


def inspect_bytes(key, raw):
    filename, _, typ, markers = SOURCES[key]
    if not isinstance(raw, bytes) or not 100 < len(raw) < MAX_BYTES:
        raise ArchiveFailure("Official original bytes missing or over-limit: " + key)
    if typ == "pdf":
        if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-2048:]:
            raise ArchiveFailure("Official document is not an intact PDF: " + key)
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeError as exc:
            raise ArchiveFailure("Unrecognized city HTML charset") from exc
        if "<html" not in text.lower() or "<body" not in text.lower():
            raise ArchiveFailure("Official HTML original missing recognizable document")
        p = VisibleText()
        p.feed(text)
        visible = " ".join(p.parts)
        if any(t not in visible for t in markers):
            raise ArchiveFailure("Official source HTML missing document-specific markers")


def official_fetch(url, timeout=45):
    require_official(url)
    with urlopen(Request(url, headers={"User-Agent": "HINANEX-A-flood-site-version/1.0"}),
                 timeout=timeout) as response:
        final = response.geturl()
        require_official(final)
        if final != url or response.status != 200:
            raise ArchiveFailure("Official URL redirected/response changed")
        raw = response.read(MAX_BYTES + 1)
        return raw, final, {
            "content_type": response.headers.get("Content-Type"),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
        }


def capture(outdir, fetch=official_fetch, now=None):
    out = Path(outdir)
    if out.is_symlink() or (out.exists() and (not out.is_dir() or any(out.iterdir()))):
        raise ArchiveFailure("Destination must be new or empty")
    sources = []
    # All-or-nothing: no partial archive if a source fails.
    for key, (filename, url, kind, _) in SOURCES.items():
        require_official(url)
        raw, final, headers = fetch(url)
        require_official(final)
        if final != url or not isinstance(headers, dict):
            raise ArchiveFailure("Official final host or HTTP provenance changed")
        inspect_bytes(key, raw)
        sources.append((key, filename, url, kind, raw, headers))
    stamp = now or datetime.now(timezone.utc)
    if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
        raise ArchiveFailure("UTC capture timestamp required")
    manifest = {
        "purpose": PURPOSE,
        "captured_at_utc": stamp.isoformat(),
        "source_note": "2026-04-01 plan, historical 2025 reuse notice and 2026 CMS have different dates",
        "pdf_content_manually_signed_off": False,
        "as_of_date_never_proves_current_opening": True,
        "pdf_originals_are_distinct_from_prior_water_html": True,
        **NO_APPROVAL,
        "source_items": [{
            "source_key": key,
            "filename": name,
            "requested_url": url,
            "final_url": url,
            "format": kind,
            "sha256": sha256(raw).hexdigest(),
            "size": len(raw),
            "http_content_type": headers.get("content_type"),
            "http_last_modified": headers.get("last_modified"),
            "http_etag": headers.get("etag"),
            "date_scope_independent_review_required": True,
        } for key, name, url, kind, raw, headers in sources],
    }
    out.mkdir(parents=True, exist_ok=True)
    for _, name, _, _, raw, _ in sources:
        (out / name).write_bytes(raw)
    (out / "site_revisions_manifest_UNAPPROVED.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(folder):
    p = Path(folder)
    if p.is_symlink() or not p.is_dir():
        raise ArchiveFailure("Archive missing or symbolic")
    mf = p / "site_revisions_manifest_UNAPPROVED.json"
    if mf.is_symlink() or not mf.is_file():
        raise ArchiveFailure("Archive manifest missing")
    try:
        manifest = json.loads(mf.read_text(encoding="utf-8"))
        stamp = datetime.fromisoformat(manifest["captured_at_utc"])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ArchiveFailure("Original version manifest invalid") from exc
    if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
        raise ArchiveFailure("Manifest UTC timestamp invalid")
    if (manifest.get("purpose") != PURPOSE
        or manifest.get("pdf_content_manually_signed_off") is not False
        or manifest.get("as_of_date_never_proves_current_opening") is not True
        or manifest.get("pdf_originals_are_distinct_from_prior_water_html") is not True
        or any(manifest.get(k) != v or type(manifest.get(k)) is not type(v)
               for k, v in NO_APPROVAL.items())):
        raise ArchiveFailure("Source manifest falsely claims accepted site/hazard")
    items = manifest.get("source_items")
    if not isinstance(items, list) or len(items) != len(SOURCES):
        raise ArchiveFailure("Wrong original source set size")
    expected = {"site_revisions_manifest_UNAPPROVED.json"} | {v[0] for v in SOURCES.values()}
    if {x.name for x in p.iterdir()} != expected:
        raise ArchiveFailure("Original files missing/extra")
    seen = set()
    for x in items:
        if not isinstance(x, dict) or x.get("source_key") not in SOURCES:
            raise ArchiveFailure("Unknown original source item")
        key = x["source_key"]
        if key in seen:
            raise ArchiveFailure("Duplicate official source entry")
        seen.add(key)
        name, url, typ, _ = SOURCES[key]
        if (x.get("filename") != name or x.get("requested_url") != url
            or x.get("final_url") != url or x.get("format") != typ
            or x.get("date_scope_independent_review_required") is not True):
            raise ArchiveFailure("Official source URI/version identity changed")
        original = p / name
        if original.is_symlink() or not original.is_file():
            raise ArchiveFailure("Original file missing/unsafe")
        raw = original.read_bytes()
        if (type(x.get("size")) is not int or x["size"] != len(raw)
            or x.get("sha256") != sha256(raw).hexdigest()):
            raise ArchiveFailure("Official original SHA256 mismatch")
        inspect_bytes(key, raw)
    return {
        "status": "A_DATED_WATER_SITE_ORIGINALS_VERIFIED_UNAPPROVED",
        "original_sources_verified": len(seen),
        "original_sha256": {x["source_key"]: x["sha256"] for x in items},
        "human_approved_site_pairs": 0,
        "flood_scenario_changes": 0,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--out-dir", type=Path)
    group.add_argument("--verify-dir", type=Path)
    a = p.parse_args()
    try:
        result = capture(a.out_dir) if a.out_dir else verify(a.verify_dir)
        print(json.dumps(result, ensure_ascii=False))
    except (ArchiveFailure, OSError) as exc:
        p.exit(2, "A flood-site original archive rejected; no approval: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
