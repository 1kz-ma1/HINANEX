"""C independent check of original Edogawa council vote HTML, not PDF bill.

Requires source's genuine exact bill #64 *row*, independent original bytes and
recorded hash. Does NOT certify building demolition, current flood standby
status, or D facility pairing.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, parse_qs
import unicodedata

NAME="municipal_council_vote_result_original.html"
MANIFEST="vote_manifest_UNAPPROVED.json"
PURPOSE="A_EDOGAWA_GIKAI_BILL64_SEPARATE_VOTE_ORIGINAL_UNAPPROVED"
SOURCE_URL=(
    "https://www.gikai.city.edogawa.tokyo.jp/g07_giketsu.asp?"
    "BUNRUI=&EXP=AND&KAIGI=2026%2F06%2F12%2C2026%2F07%2F01%2C152"
    "&KEKKA=&KENSU=100&KWORD1=&KWORD2=&NENFROM=&NENTO=&SMODE=2&Sflg=2"
)


class IndependentVoteFailure(ValueError):
    pass


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.words=[]
        self.excluded=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","template"):
            self.excluded+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","template") and self.excluded:
            self.excluded-=1
    def handle_data(self,content):
        if not self.excluded:
            self.words.append(content)


def source_vote_html(raw):
    if not isinstance(raw,bytes) or not 100 < len(raw) < 3_000_000:
        raise IndependentVoteFailure("Official vote original byte length invalid")
    html=None
    for enc in ("utf-8-sig","cp932"):
        try:
            html=raw.decode(enc)
            break
        except UnicodeDecodeError:
            pass
    if html is None or "<html" not in html.lower() or "<body" not in html.lower():
        raise IndependentVoteFailure("Official vote source not readable HTML")
    p=PlainText()
    p.feed(html)
    text=unicodedata.normalize("NFKC",re.sub(r"\s+","", " ".join(p.words)))
    # Isolate bill 64 from both the preceding and following neighboring votes:
    i=text.find("議案第64号")
    e=text.find("議案第65号",i+5)
    if i < 0 or e <= i or text.count("議案第64号") != 1:
        raise IndependentVoteFailure("Council vote bill #64 not uniquely delimited")
    segment=text[i:e]
    required=("旧下鎌田小学校校舎等解体工事請負契約",
              "令和8年7月1日","可決","全会一致")
    if any(token not in segment for token in required):
        raise IndependentVoteFailure("Cannot prove bill64 voted approved unanimously")
    if segment.count("可決") != 1:
        raise IndependentVoteFailure("Vote result ambiguous in bill64 row")
    return {"result":"可決","unanimous":True,"voted_at":"2026-07-01",
            "bill_number":64,"source_record_type":"council_vote_result_not_site_status"}


def verify(path):
    folder=Path(path)
    mf=folder/MANIFEST
    original=folder/NAME
    if (folder.is_symlink() or not folder.is_dir() or mf.is_symlink()
        or original.is_symlink() or not mf.is_file() or not original.is_file()):
        raise IndependentVoteFailure("Original council vote sources absent/unsafe")
    if {p.name for p in folder.iterdir()} != {MANIFEST,NAME}:
        raise IndependentVoteFailure("Archive inventory differs from source")
    try:
        raw_manifest=mf.read_bytes()
        m=json.loads(raw_manifest)
        t=datetime.fromisoformat(m["captured_utc"])
    except (KeyError,ValueError,TypeError,OSError) as exc:
        raise IndependentVoteFailure("A source manifest invalid") from exc
    if t.utcoffset() is None or t.utcoffset().total_seconds()!=0:
        raise IndependentVoteFailure("Missing original UTC capture date")
    url=m.get("final_url")
    if not isinstance(url,str):
        raise IndependentVoteFailure("Original response URL invalid")
    u=urlsplit(url)
    parts=parse_qs(u.query,keep_blank_values=True)
    if (u.scheme!="https" or u.hostname!="www.gikai.city.edogawa.tokyo.jp"
        or u.path!="/g07_giketsu.asp" or u.username or u.password
        or u.fragment or u.port not in (None,443)
        or parts.get("KAIGI")!=["2026/06/12,2026/07/01,152"]
        or parts.get("KENSU")!=["100"]):
        raise IndependentVoteFailure("Source vote-result page is not requested council meeting")
    if (m.get("purpose")!=PURPOSE or m.get("requested_url")!=SOURCE_URL
        or m.get("original_filename")!=NAME
        or m.get("council_bill_64_original_pdf_is_a_separate_source") is not True
        or m.get("source_row_machine_checked_not_independent_human_signoff") is not True
        or m.get("vote_is_a_demolition_completion_record") is not False
        or m.get("site_open_or_closed_verified") is not False
        or m.get("site_identity_human_signed") is not False
        or type(m.get("flood_classifications_added")) is not int
        or m.get("flood_classifications_added")!=0):
        raise IndependentVoteFailure("A falsely elevates a vote to safety proof")
    raw=original.read_bytes()
    if (type(m.get("original_bytes")) is not int
        or m["original_bytes"]!=len(raw)
        or m.get("original_sha256")!=sha256(raw).hexdigest()):
        raise IndependentVoteFailure("Original council vote source SHA256 mismatch")
    fields=source_vote_html(raw)
    a_obs=m.get("vote_row_observation")
    if (not isinstance(a_obs,dict)
        or a_obs.get("bill_number")!=64
        or a_obs.get("exact_vote_result_from_council_row")!=fields["result"]
        or a_obs.get("unanimous_result_visible") is not True
        or a_obs.get("vote_date_original")!="令和8年7月1日"
        or a_obs.get("vote_has_no_current_building_condition") is not True):
        raise IndependentVoteFailure("C independent result differs from A vote observation")
    return {
        "status":"C_COUNCIL_BILL64_VOTE_ORIGINAL_VERIFIED_NO_DEMOLITION_FINISH",
        "original_html_sha256":sha256(raw).hexdigest(),
        "a_original_manifest_sha256":sha256(raw_manifest).hexdigest(),
        "bill_64_vote_date":"2026-07-01",
        "bill_64_passed_unanimously_on_council_record":True,
        "source_reviewer_manual_site_status_signed":False,
        "bill_contract_execution_actual_date":None,
        "construction_started_date":None,
        "demolition_complete_date":None,
        "old_buildings_available_now":"UNKNOWN",
        "current_external_inland_flood_standby":"UNKNOWN",
        "C_human_accepted_site_links":0,
        "new_flood_candidates_or_exclusions":0,
        "does_not_mutate_region_export":True,
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive-dir",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    x=ap.parse_args()
    if x.out.exists():
        ap.error("Refuse to overwrite original C vote audit")
    try:
        result=verify(x.archive_dir)
        x.out.parent.mkdir(parents=True,exist_ok=True)
        x.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"status":result["status"],"C_approved_sites":0,
                          "D_new_flood_decisions":0},ensure_ascii=False))
    except (IndependentVoteFailure,OSError) as e:
        ap.exit(2,"Independent C council vote audit failed: "+str(e)+"\n")


if __name__=="__main__":
    main()
