"""C independent 2026 Edogawa external/internal flood source-version review.
PDF parsing and SHA256 are machine evidence, not human same-campus approval.
Uses PyMuPDF on GitHub runner; never changes D or Render.
"""
from __future__ import annotations
import argparse
from datetime import datetime
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata


CITY = "https://www.city.edogawa.tokyo.jp"
FILES = {
    "2026_disaster_plan_original":
        ("2026_disaster_plan_external_internal_water.pdf",
         CITY + "/documents/68931/00006.pdf"),
    "2025_old_shimokamata_reuse_notice":
        ("2025_old_shimokamata_afteruse.pdf",
         CITY + "/documents/40376/0704simokamata_1.pdf"),
    "2026_school_afteruse_page":
        ("school_afteruse_page.html",
         CITY + "/e085/kuseijoho/zaisei/kokyoshisetsu/rikatuyou.html"),
}
FLAGS = ("school_building_or_premises_identity_human_approved",
         "official_document_effective_date_human_approved",
         "external_vs_internal_flood_semantics_human_approved",
         "campus_to_d_identity_human_approved")
PURPOSE = "A_EDOGAWA_2026_EXTERNAL_INTERNAL_WATER_SITE_ORIGINALS_UNAPPROVED"


class AuditError(ValueError):
    pass


class Visible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.ignore = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "template"):
            self.ignore += 1
    def handle_endtag(self, tag):
        if tag in ("style", "script", "template") and self.ignore:
            self.ignore -= 1
    def handle_data(self, data):
        if not self.ignore:
            self.parts.append(data)


def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))


def pdf_context(key, raw):
    import fitz  # isolated source-audit job installs PyMuPDF; core CI has no dependency
    if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-2048:]:
        raise AuditError("Official PDF header/end missing")
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        try:
            if key == "2026_disaster_plan_original":
                if doc.page_count < 5:
                    raise AuditError("2026 regional plan missing water standby pages")
                for n, hazard in ((2, "外水氾濫"), (4, "内水氾濫")):
                    s = norm(doc[n].get_text("text"))
                    markers = ["待避施設一覧表", hazard, "令和8年4月1日現在",
                               "下鎌田小", "旧下鎌田小", "瑞江4-19-1", "東瑞江3-11-1"]
                    missing = [x for x in markers if norm(x) not in s]
                    if missing:
                        raise AuditError("Missing 2026 source PDF context " + str(n) + ":" + str(missing))
                return {
                    "source_page_external_zero_based": 2,
                    "source_page_internal_zero_based": 4,
                    "source_original_as_of": "令和8年4月1日現在",
                    "new_and_old_site_rows_separately_present": True,
                    "source_new_address_raw": "瑞江4-19-1",
                    "source_old_address_raw": "東瑞江3-11-1",
                    "floor_by_hazard_signed_off": False,
                }
            if doc.page_count != 1:
                raise AuditError("Old campus reuse notice unexpected page count")
            visible = norm(doc[0].get_text("text"))
            if any(norm(x) not in visible for x in ("旧下鎌田小学校", "後利用", "解体")):
                raise AuditError("Former campus afteruse notice content missing")
            return {
                "postclosure_reuse_notice_page_zero_based": 0,
                "old_campus_demolition_language_present": True,
                "demolition_schedule_or_present_use_reviewed": False,
            }
        finally:
            doc.close()
    except (ValueError, RuntimeError) as exc:
        raise AuditError("Official PDF page read failed") from exc


def verify(archive):
    folder=Path(archive)
    mf=folder/"site_revisions_manifest_UNAPPROVED.json"
    if folder.is_symlink() or not folder.is_dir() or mf.is_symlink() or not mf.is_file():
        raise AuditError("Archive or source manifest missing/unsafe")
    manifest_bytes=mf.read_bytes()
    try:
        m=json.loads(manifest_bytes)
        ts=datetime.fromisoformat(m["captured_at_utc"])
    except (ValueError, KeyError, TypeError) as exc:
        raise AuditError("Malformed source version manifest") from exc
    if ts.utcoffset() is None or ts.utcoffset().total_seconds()!=0:
        raise AuditError("Archive missing UTC timestamp")
    if (m.get("purpose") != PURPOSE
        or m.get("pdf_content_manually_signed_off") is not False
        or m.get("as_of_date_never_proves_current_opening") is not True
        or m.get("pdf_originals_are_distinct_from_prior_water_html") is not True
        or any(m.get(k) is not False for k in FLAGS)
        or type(m.get("human_c_site_pairs_approved")) is not int
        or m["human_c_site_pairs_approved"] != 0
        or type(m.get("new_flood_scenario_classifications")) is not int
        or m["new_flood_scenario_classifications"] != 0):
        raise AuditError("Source implies unsanctioned human approval")
    items=m.get("source_items")
    if not isinstance(items,list) or len(items)!=len(FILES):
        raise AuditError("Official source inventory incomplete")
    if {p.name for p in folder.iterdir()} != (
            {v[0] for v in FILES.values()} | {"site_revisions_manifest_UNAPPROVED.json"}):
        raise AuditError("Original source file set differs")
    found={}
    for item in items:
        if not isinstance(item, dict) or item.get("source_key") not in FILES:
            raise AuditError("Unrecognized source identity")
        key=item["source_key"]
        if key in found:
            raise AuditError("Duplicate official original")
        filename,url=FILES[key]
        if (item.get("requested_url")!=url or item.get("final_url")!=url
            or item.get("filename")!=filename
            or item.get("format")!=("pdf" if filename.endswith(".pdf") else "html")
            or item.get("date_scope_independent_review_required") is not True):
            raise AuditError("Official URL or edition substitution")
        f=folder/filename
        if f.is_symlink() or not f.is_file():
            raise AuditError("Original source missing/unsafe")
        raw=f.read_bytes()
        if (type(item.get("size")) is not int
            or not 100 < len(raw) < 16_000_000 or item["size"]!=len(raw)
            or sha256(raw).hexdigest()!=item.get("sha256")):
            raise AuditError("Official original bytes SHA256 changed")
        if filename.endswith(".pdf"):
            contents=pdf_context(key,raw)
        else:
            try:
                h=raw.decode("utf-8-sig")
            except UnicodeError as exc:
                raise AuditError("Old-campus reuse official HTML unreadable") from exc
            if "<html" not in h.lower() or "<body" not in h.lower():
                raise AuditError("Old-campus reuse HTML absent")
            p=Visible()
            p.feed(h)
            txt=norm(" ".join(p.parts))
            if any(norm(x) not in txt for x in ("統廃合後の学校後利用","旧下鎌田小学校")):
                raise AuditError("Wrong original municipal reuse page")
            contents={"reuse_page_context_present":True,"present_opening_reviewed":False}
        found[key]={"sha256":sha256(raw).hexdigest(),"raw_source_url":url,"content_evidence":contents}
    return {
        "status":"C_2026_EXTERNAL_INTERNAL_SOURCE_EDITION_VERIFIED_HUMAN_REVIEW_REQUIRED",
        "a_manifest_sha256":sha256(manifest_bytes).hexdigest(),
        "original_sources_independently_reviewed":len(found),
        "source_evidence":found,
        "2026_source_lists_old_and_new_separately":True,
        "2026_new_school_location_pdf_vs_school_directory_discrepancy":
            {"disaster_plan_raw":"瑞江4-19-1","school_directory_raw":"瑞江4丁目19番10号",
             "same_premises_human_approved":False},
        "old_watertable_version_replaced_or_reclassified":False,
        "source_as_of_does_not_certify_current_opening":True,
        "C_approved_physical_site_pairs":0,
        "D_flood_classifications_added":0,
        "previous_D_flood_152_unknown_retained":True,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive-dir",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    args=p.parse_args()
    if args.report.exists():
        p.error("C evidence report overwrite forbidden")
    try:
        z=verify(args.archive_dir)
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(z,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"status":z["status"],"sources":len(FILES),
                          "C_site_approvals":0,"flood_promotions":0},ensure_ascii=False))
    except (AuditError,OSError) as exc:
        p.exit(2,"C source/version validation failed: "+str(exc)+"\n")


if __name__=="__main__":
    main()
