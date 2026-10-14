"""A-only archival capture of Edogawa council's Shimokamata demolition bill PDF.

This proposed and municipally voted contract source DOES NOT certify that
demolition has started/finished, or that the former campus is currently closed.
The PDF itself records a bill; approval is documented on the separate council
meeting results page, NOT inferred from the bill's text alone.

python data-research/tools/archive_edogawa_demolition_contract.py --out-dir /external/new
python data-research/tools/archive_edogawa_demolition_contract.py --verify-dir /external/new
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

OFFICIAL_PDF = "https://www.gikai.city.edogawa.tokyo.jp/voices/GikaiDoc/attach/Gk/Gk2792_gian64.pdf"
VOTE_RESULT_PAGE = (
    "https://www.gikai.city.edogawa.tokyo.jp/g07_giketsu.asp?"
    "BUNRUI=&EXP=AND&KAIGI=2026%2F06%2F12%2C2026%2F07%2F01%2C152"
    "&KEKKA=&KENSU=100&KWORD1=&KWORD2=&NENFROM=&NENTO=&SMODE=2&Sflg=2"
)
PURPOSE = "A_EDOGAWA_2026_SHIMOKAMATA_DEMOLITION_COUNCIL_BILL_UNAPPROVED"
FILENAME = "official_council_bill64_2026_demolition_original.pdf"
MAX_BYTES = 2_000_000
FLAGS = {
    "c_independent_site_approved": False,
    "municipal_flood_site_current_open_verified": False,
    "demolition_work_completed_verified": False,
    "disaster_plan_new_old_site_version_reconciled": False,
    "flood_scenario_status_changes": 0,
}


class EvidenceError(ValueError):
    pass


def trusted_url(url):
    if not isinstance(url, str):
        raise EvidenceError("Original URL invalid")
    u = urlsplit(url)
    expected = urlsplit(OFFICIAL_PDF)
    if (u.scheme != "https" or u.hostname != expected.hostname
        or u.path != expected.path or u.query or u.fragment
        or u.username or u.password or u.port not in (None, 443)):
        raise EvidenceError("Original council PDF was redirected or substituted")


def check_pdf(raw):
    if (not isinstance(raw, bytes) or not 100 < len(raw) <= MAX_BYTES
        or not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-2048:]):
        raise EvidenceError("Council original is not a valid bounded PDF")


def download(timeout=40):
    trusted_url(OFFICIAL_PDF)
    with urlopen(Request(OFFICIAL_PDF, headers={
        "User-Agent": "HINANEX-A-official-council-evidence/1.0",
    }), timeout=timeout) as r:
        url = r.geturl()
        trusted_url(url)
        if r.status != 200:
            raise EvidenceError("Official council PDF was not HTTP 200")
        data = r.read(MAX_BYTES + 1)
        check_pdf(data)
        return data, url, {
            "content_type": r.headers.get("Content-Type"),
            "last_modified": r.headers.get("Last-Modified"),
            "etag": r.headers.get("ETag"),
        }


def archive(folder, fetch=download, now=None):
    folder = Path(folder)
    if (folder.is_symlink() or (folder.exists() and
        (not folder.is_dir() or any(folder.iterdir())))):
        raise EvidenceError("Archive destination must be new or empty")
    raw, final, headers = fetch()
    trusted_url(final)
    check_pdf(raw)
    if not isinstance(headers, dict):
        raise EvidenceError("Official response metadata missing")
    stamp = now or datetime.now(timezone.utc)
    if stamp.utcoffset() is None or stamp.utcoffset().total_seconds() != 0:
        raise EvidenceError("Capture time must be UTC")
    manifest = {
        "purpose": PURPOSE, "captured_utc": stamp.isoformat(),
        "official_publisher": "江戸川区議会",
        "bill_pdf_url": OFFICIAL_PDF,
        "approval_record_page_for_separate_human_review": VOTE_RESULT_PAGE,
        "bill_number": 64,
        "bill_proposed_date_raw": "令和八年六月十二日",
        "bill_vote_status_derived_from_pdf": None,
        "source_filename": FILENAME,
        "source_sha256": sha256(raw).hexdigest(),
        "source_size_bytes": len(raw),
        "final_pdf_url": final,
        "http_content_type": headers.get("content_type"),
        "http_last_modified": headers.get("last_modified"),
        "http_etag": headers.get("etag"),
        "actual_construction_progress_human_confirmation_required": True,
        "official_pdf_page_content_independent_c_review_required": True,
        **FLAGS,
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / FILENAME).write_bytes(raw)
    (folder / "council_source_manifest_UNAPPROVED.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(folder):
    folder = Path(folder)
    mf = folder / "council_source_manifest_UNAPPROVED.json"
    rawpath = folder / FILENAME
    if (folder.is_symlink() or not folder.is_dir() or mf.is_symlink()
        or rawpath.is_symlink() or not mf.is_file() or not rawpath.is_file()):
        raise EvidenceError("Council evidence archive missing/unsafe")
    if {p.name for p in folder.iterdir()} != {mf.name, rawpath.name}:
        raise EvidenceError("Council archive original file set differs")
    try:
        m = json.loads(mf.read_text(encoding="utf-8"))
        t = datetime.fromisoformat(m["captured_utc"])
    except (OSError, TypeError, ValueError, KeyError) as exc:
        raise EvidenceError("Original manifest invalid") from exc
    if t.utcoffset() is None or t.utcoffset().total_seconds() != 0:
        raise EvidenceError("Original capture timestamp not UTC")
    if (m.get("purpose") != PURPOSE or m.get("bill_pdf_url") != OFFICIAL_PDF
        or m.get("final_pdf_url") != OFFICIAL_PDF
        or m.get("approval_record_page_for_separate_human_review") != VOTE_RESULT_PAGE
        or m.get("source_filename") != FILENAME
        or m.get("bill_number") != 64
        or m.get("bill_vote_status_derived_from_pdf") is not None
        or m.get("actual_construction_progress_human_confirmation_required") is not True
        or m.get("official_pdf_page_content_independent_c_review_required") is not True
        or any(type(m.get(k)) is not type(v) or m.get(k) != v for k,v in FLAGS.items())):
        raise EvidenceError("Archive claims unreviewed approval or altered original")
    data = rawpath.read_bytes()
    check_pdf(data)
    if (type(m.get("source_size_bytes")) is not int
        or m["source_size_bytes"] != len(data)
        or m.get("source_sha256") != sha256(data).hexdigest()):
        raise EvidenceError("Stored bill PDF digest differs from original manifest")
    return {
        "status": "A_COUNCIL_BILL_BYTES_VERIFIED_NOT_DEMOLITION_COMPLETION",
        "sha256": sha256(data).hexdigest(),
        "human_approved_site_pairs": 0,
        "flood_classification_changes": 0,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--out-dir",type=Path)
    g.add_argument("--verify-dir",type=Path)
    args=p.parse_args()
    try:
        result=archive(args.out_dir) if args.out_dir else verify(args.verify_dir)
        print(json.dumps(result,ensure_ascii=False))
    except (EvidenceError,OSError) as e:
        p.exit(2,"A independent council source rejected: "+str(e)+"\n")


if __name__=="__main__":
    main()
