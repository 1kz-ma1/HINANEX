"""A archival original of independent Edogawa council vote list, not demolition state.

This source is separate from council *bill* PDF. It records council's recorded
vote, NOT whether contract works have commenced or site evacuation is open.
Run on an isolated official-network runner and store outputs outside Git.

python data-research/tools/archive_edogawa_council_vote.py --out-dir /outside-git/vote
python data-research/tools/archive_edogawa_council_vote.py --verify-dir /outside-git/vote
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

OFFICIAL_URL = (
    "https://www.gikai.city.edogawa.tokyo.jp/g07_giketsu.asp?"
    "BUNRUI=&EXP=AND&KAIGI=2026%2F06%2F12%2C2026%2F07%2F01%2C152"
    "&KEKKA=&KENSU=100&KWORD1=&KWORD2=&NENFROM=&NENTO=&SMODE=2&Sflg=2"
)
HOST = "www.gikai.city.edogawa.tokyo.jp"
FILENAME = "municipal_council_vote_result_original.html"
PURPOSE = "A_EDOGAWA_GIKAI_BILL64_SEPARATE_VOTE_ORIGINAL_UNAPPROVED"
MAX_BYTES = 3_000_000
FLAGS = {
    "vote_is_a_demolition_completion_record": False,
    "site_open_or_closed_verified": False,
    "site_identity_human_signed": False,
    "flood_classifications_added": 0,
}


class SourceError(ValueError):
    pass


class HTMLWords(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def decoded_html(raw):
    if not isinstance(raw, bytes) or not 100 < len(raw) <= MAX_BYTES:
        raise SourceError("Vote-page HTML missing or too large")
    for encoding in ("utf-8-sig", "cp932"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            pass
    else:
        raise SourceError("Vote page is not supported Japanese HTML")
    if "<html" not in text.lower() or "<body" not in text.lower():
        raise SourceError("Vote source is not recognizable HTML")
    p = HTMLWords()
    p.feed(text)
    visible = re.sub(r"\s+", "", " ".join(p.parts))
    start = visible.find("議案第64号")
    end = visible.find("議案第65号", start + 5)
    if start < 0 or end <= start:
        raise SourceError("Target vote row and following bill boundary absent")
    row = visible[start:end]
    if not all(token in row for token in (
        "旧下鎌田小学校校舎等解体工事請負契約",
        "令和8年7月1日", "可決", "全会一致",
    )):
        raise SourceError("Cannot attribute official approved vote to bill 64 only")
    if row.count("可決") != 1:
        raise SourceError("Vote decision unexpectedly ambiguous within bill 64")
    return {
        "bill_number": 64,
        "exact_vote_result_from_council_row": "可決",
        "unanimous_result_visible": True,
        "vote_date_original": "令和8年7月1日",
        "bill_original_name": "旧下鎌田小学校校舎等解体工事請負契約",
        "vote_has_no_current_building_condition": True,
    }


def official_url(url):
    if not isinstance(url, str):
        raise SourceError("Official source URL missing")
    u = urlsplit(url)
    if (u.scheme != "https" or u.hostname != HOST or u.path != "/g07_giketsu.asp"
        or u.port not in (None, 443) or u.username or u.password or u.fragment):
        raise SourceError("Council origin or vote endpoint substituted")


def download(timeout=50):
    official_url(OFFICIAL_URL)
    with urlopen(Request(OFFICIAL_URL, headers={
        "User-Agent": "HINANEX-A-official-vote-archive/1.0",
    }), timeout=timeout) as r:
        final = r.geturl()
        official_url(final)
        if r.status != 200:
            raise SourceError("Council vote listing did not return HTTP 200")
        raw = r.read(MAX_BYTES + 1)
        decoded_html(raw)
        return raw, final, {
            "content_type": r.headers.get("Content-Type"),
            "last_modified": r.headers.get("Last-Modified"),
            "etag": r.headers.get("ETag"),
        }


def capture(destination, fetch=download, now=None):
    folder = Path(destination)
    if folder.is_symlink() or (folder.exists() and
        (not folder.is_dir() or any(folder.iterdir()))):
        raise SourceError("Official vote archive must be new/empty")
    raw, final_url, headers = fetch()
    official_url(final_url)
    if not isinstance(headers, dict):
        raise SourceError("Source response headers missing")
    parsed = decoded_html(raw)
    t = now or datetime.now(timezone.utc)
    if t.utcoffset() is None or t.utcoffset().total_seconds() != 0:
        raise SourceError("Capture clock must be UTC")
    manifest = {
        "purpose": PURPOSE,
        "captured_utc": t.isoformat(),
        "official_publisher": "江戸川区議会",
        "requested_url": OFFICIAL_URL,
        "final_url": final_url,
        "original_filename": FILENAME,
        "original_sha256": sha256(raw).hexdigest(),
        "original_bytes": len(raw),
        "http_content_type": headers.get("content_type"),
        "http_last_modified": headers.get("last_modified"),
        "http_etag": headers.get("etag"),
        "council_bill_64_original_pdf_is_a_separate_source": True,
        "source_row_machine_checked_not_independent_human_signoff": True,
        "vote_row_observation": parsed,
        **FLAGS,
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / FILENAME).write_bytes(raw)
    (folder / "vote_manifest_UNAPPROVED.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def verify(folder):
    folder = Path(folder)
    mf = folder / "vote_manifest_UNAPPROVED.json"
    original = folder / FILENAME
    if (folder.is_symlink() or not folder.is_dir() or mf.is_symlink() or
        original.is_symlink() or not mf.is_file() or not original.is_file()):
        raise SourceError("Original vote evidence missing/unsafe")
    if {x.name for x in folder.iterdir()} != {mf.name, original.name}:
        raise SourceError("Unexpected vote source archive inventory")
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
        d = datetime.fromisoformat(m["captured_utc"])
    except (OSError, KeyError, ValueError, TypeError) as exc:
        raise SourceError("Original vote manifest invalid") from exc
    if d.utcoffset() is None or d.utcoffset().total_seconds() != 0:
        raise SourceError("Original source capture timestamp not UTC")
    official_url(m.get("final_url"))
    if (m.get("purpose") != PURPOSE or m.get("requested_url") != OFFICIAL_URL
        or m.get("original_filename") != FILENAME
        or m.get("council_bill_64_original_pdf_is_a_separate_source") is not True
        or m.get("source_row_machine_checked_not_independent_human_signoff") is not True
        or any(type(m.get(k)) is not type(v) or m.get(k) != v for k,v in FLAGS.items())):
        raise SourceError("Source version or no-approval contract altered")
    raw = original.read_bytes()
    if (type(m.get("original_bytes")) is not int or m["original_bytes"] != len(raw)
        or m.get("original_sha256") != sha256(raw).hexdigest()):
        raise SourceError("Original vote HTML SHA256 changed")
    parsed = decoded_html(raw)
    if parsed != m.get("vote_row_observation"):
        raise SourceError("Source row conclusion differs from original")
    return {
        "status": "A_OFFICIAL_BILL64_VOTE_ROW_ORIGINAL_VERIFIED_NO_SITE_STATUS",
        "official_vote_result_from_row": parsed["exact_vote_result_from_council_row"],
        "original_sha256": sha256(raw).hexdigest(),
        "new_flood_classifications": 0,
        "site_current_opening": "UNKNOWN",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--out-dir", type=Path)
    g.add_argument("--verify-dir", type=Path)
    a = p.parse_args()
    try:
        result = capture(a.out_dir) if a.out_dir else verify(a.verify_dir)
        print(json.dumps(result, ensure_ascii=False))
    except (SourceError, OSError) as exc:
        p.exit(2, "A official vote original failed closed: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
