"""C independent council bill ORIGINAL audit; no demolition/safety determination.

Machine-check PDF source content plus A immutable source metadata. This PDF
is a contract bill, NOT proof of on-site demolition or direct evidence of
the council vote result, which belongs to a separately published vote page.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

URL="https://www.gikai.city.edogawa.tokyo.jp/voices/GikaiDoc/attach/Gk/Gk2792_gian64.pdf"
VOTE_PAGE=(
    "https://www.gikai.city.edogawa.tokyo.jp/g07_giketsu.asp?"
    "BUNRUI=&EXP=AND&KAIGI=2026%2F06%2F12%2C2026%2F07%2F01%2C152"
    "&KEKKA=&KENSU=100&KWORD1=&KWORD2=&NENFROM=&NENTO=&SMODE=2&Sflg=2"
)
NAME="official_council_bill64_2026_demolition_original.pdf"
PURPOSE="A_EDOGAWA_2026_SHIMOKAMATA_DEMOLITION_COUNCIL_BILL_UNAPPROVED"
FLAGS={
    "c_independent_site_approved":False,
    "municipal_flood_site_current_open_verified":False,
    "demolition_work_completed_verified":False,
    "disaster_plan_new_old_site_version_reconciled":False,
    "flood_scenario_status_changes":0,
}


class CouncilAuditFailure(ValueError):
    pass


def norm(text):
    return re.sub(r"\s+","",unicodedata.normalize("NFKC",text))


def pdf_details(raw):
    if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-2048:]:
        raise CouncilAuditFailure("Council source PDF structure absent")
    import fitz  # optional PyMuPDF dependency only in isolated council audit job
    try:
        doc=fitz.open(stream=raw,filetype="pdf")
        try:
            if doc.page_count != 3:
                raise CouncilAuditFailure("Expected exact three-page bill")
            pages=[norm(doc[i].get_text("text")) for i in range(3)]
        finally:
            doc.close()
    except (ValueError,RuntimeError) as exc:
        raise CouncilAuditFailure("Could not inspect source PDF pages") from exc
    targets=[
        ("page0",pages[0],("第六十四号議案","旧下鎌田小学校校舎等解体工事",
                           "令和八年六月十二日")),
        ("page1",pages[1],("旧下鎌田小学校校舎等解体工事請負契約",
                           "二億五千八百五十万円","株式会社フジムラ")),
        ("page2",pages[2],("東瑞江三丁目一一番一号","校舎棟解体",
                           "屋内運動場棟解体","令和九年三月十二日")),
    ]
    for key,page,required in targets:
        missing=[x for x in required if norm(x) not in page]
        if missing:
            raise CouncilAuditFailure("Council "+key+" content not confirmed: "+str(missing))
    return {
        "pdf_pages_checked":3,
        "bill_number":64,
        "contract_bill_submitted_at":"2026-06-12",
        "contract_value_yen_in_bill":258_500_000,
        "contractor_original_raw":"株式会社フジムラ",
        "former_campus_demolition_site_raw":"東瑞江三丁目一一番一号",
        "demolition_scopes_confirmed":["校舎棟","屋内運動場棟"],
        "planned_contract_end_date":"2027-03-12",
        "bill_itself_proves_final_council_approval":False,
        "construction_started_or_finished_verified":False,
        "real_time_flood_standby_opening_verified":False,
    }


def verify(folder):
    folder=Path(folder)
    mf=folder/"council_source_manifest_UNAPPROVED.json"
    pdf=folder/NAME
    if (folder.is_symlink() or not folder.is_dir() or mf.is_symlink()
        or pdf.is_symlink() or not mf.is_file() or not pdf.is_file()):
        raise CouncilAuditFailure("Council original/manifest missing or unsafe")
    if {x.name for x in folder.iterdir()} != {mf.name,pdf.name}:
        raise CouncilAuditFailure("Source original inventory changed")
    manifest_raw=mf.read_bytes()
    try:
        m=json.loads(manifest_raw)
        t=datetime.fromisoformat(m["captured_utc"])
    except (OSError,KeyError,ValueError,TypeError) as exc:
        raise CouncilAuditFailure("A manifest invalid") from exc
    if t.utcoffset() is None or t.utcoffset().total_seconds()!=0:
        raise CouncilAuditFailure("A original captured timestamp not UTC")
    if (m.get("purpose")!=PURPOSE or m.get("bill_pdf_url")!=URL
        or m.get("final_pdf_url")!=URL
        or m.get("approval_record_page_for_separate_human_review")!=VOTE_PAGE
        or m.get("source_filename")!=NAME or m.get("bill_number")!=64
        or m.get("bill_vote_status_derived_from_pdf") is not None
        or m.get("actual_construction_progress_human_confirmation_required") is not True
        or m.get("official_pdf_page_content_independent_c_review_required") is not True
        or any(type(m.get(k)) is not type(v) or m.get(k)!=v for k,v in FLAGS.items())):
        raise CouncilAuditFailure("Unapproved site/council source claims changed")
    raw=pdf.read_bytes()
    if (type(m.get("source_size_bytes")) is not int
        or not 100 < len(raw) < 2_000_000
        or m["source_size_bytes"]!=len(raw)
        or m.get("source_sha256")!=sha256(raw).hexdigest()):
        raise CouncilAuditFailure("Council original byte digest altered")
    content=pdf_details(raw)
    return {
        "status":"C_COUNCIL_CONTRACT_BILL_ORIGINAL_VERIFIED_OPERATIONS_UNKNOWN",
        "source_original_sha256":sha256(raw).hexdigest(),
        "a_manifest_sha256":sha256(manifest_raw).hexdigest(),
        "source_pdf_url":URL,
        "council_approval_page_for_independent_review":VOTE_PAGE,
        "original_bill_pdf_observations":content,
        "separate_vote_result_observed_on_public_council_page":
            "REQUIRES_MANUAL_OR_SEPARATE_SOURCE_SNAPSHOT",
        "demolition_completion_status":"UNKNOWN",
        "current_former_site_buildings_exist_and_usable_status":"UNKNOWN",
        "current_standby_site_is_open_status":"UNKNOWN",
        "2026_disaster_plan_site_listing_superseded":False,
        "C_human_same_building_identity_pairs_approved":0,
        "D_flood_candidate_or_excluded_added":0,
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive-dir",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists():
        ap.error("Refuse to overwrite previous C council independent review")
    try:
        item=verify(a.archive_dir)
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(item,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"status":item["status"],"source_sha256":item["source_original_sha256"],
                          "site_approved":0,"flood_status_changed":0},ensure_ascii=False))
    except (OSError,CouncilAuditFailure) as e:
        ap.exit(2,"C contract original invalid: "+str(e)+"\n")


if __name__=="__main__":
    main()
