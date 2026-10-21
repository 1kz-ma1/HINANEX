"""C independent evidence review for A's Edogawa school-campus timeline archive.

Does not perform automatic physical-site joins, date/effective-period signoff,
source-data correction or flood Scenario classification. A historical PDF's
signature is NOT verification of its contents; a C human must review its pages.

python validation/validation/verify_edogawa_campus_history.py \
  --archive-dir /external/campus-history --report /external/campus_C_review_UNAPPROVED.json
"""
from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit

CITY = "https://www.city.edogawa.tokyo.jp"
EXPECTED = {
    "hirai_minami_rebuild": (
        "hirai_minami_rebuild.html",
        CITY + "/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/hiraiminamisyo.html",
        ("平井南小学校", "旧小松川第三中学校", "令和11年9月")),
    "edogawa_school_rebuild_index": (
        "school_rebuild_overview.html",
        CITY + "/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/kaichikugaiyo.html",
        ("平井南小学校", "平井5丁目3番11号")),
    "shimokamata_rebuild": (
        "shimokamata_rebuild.html",
        CITY + "/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/shimokamatatougoukou.html",
        ("下鎌田小学校", "下鎌田西小学校", "令和7年9月")),
    "shimokamata_integration": (
        "shimokamata_integration.html",
        CITY + "/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/togo/shimokamatachiiki.html",
        ("下鎌田小学校", "下鎌田西小学校", "令和5年4月")),
    "school_district_map_guidance": (
        "school_district_2025.html",
        CITY + "/e069/kosodate/kyoiku/kyouiku/shisetuitiran/syogakko/kuikizu.html",
        ("下鎌田小学校", "東瑞江3丁目11番1号", "令和7年9月")),
    "historical_shimokamata_site_plan_2021": (
        "shimokamata_2021_campus_plan.pdf",
        CITY + "/documents/21357/shimokamatasyo.pdf", ()),
    "historical_hirai_board_minutes_2024": (
        "hirai_2024_school_board_minutes.pdf",
        CITY + "/documents/57803/r6-20gijiroku.pdf", ()),
}
STATUS = "C_SCHOOL_HISTORY_SOURCE_INTEGRITY_CHECKED_SITE_AND_DATE_UNAPPROVED"
FLAGS = (
    "school_campus_identity_human_approved",
    "school_campus_effective_date_human_approved",
    "water_facility_site_link_human_approved",
    "flood_only_semantics_human_approved",
)
PRIORITY_REVIEWS = {
    "平井南小学校": {
        "water_source_number": "7",
        "concern": "2025 temporary campus and current-source representative coordinates",
        "independent_html_source_keys": [
            "hirai_minami_rebuild", "edogawa_school_rebuild_index",
        ],
        "historical_pdf_source_keys": ["historical_hirai_board_minutes_2024"],
        "original_gsi_vs_d_distance_m_previous_review_only": 429.34,
    },
    "下鎌田小学校": {
        "water_source_number": "42",
        "concern": "different pre-merger campus vs post-merger new campus opened in 2025",
        "independent_html_source_keys": [
            "shimokamata_rebuild", "shimokamata_integration",
            "school_district_map_guidance",
        ],
        "historical_pdf_source_keys": ["historical_shimokamata_site_plan_2021"],
        "original_gsi_vs_d_distance_m_previous_review_only": 189.03,
    },
    "瑞江小学校": {
        "water_source_number": "39",
        "concern": "GSI/D representative point difference; no timeline source here resolves it",
        "independent_html_source_keys": [],
        "historical_pdf_source_keys": [],
        "original_gsi_vs_d_distance_m_previous_review_only": 106.80,
    },
    "三葛西小学校": {
        "water_source_number": "23",
        "concern": "malformed municipal water-list address; do not rewrite original",
        "independent_html_source_keys": [],
        "historical_pdf_source_keys": [],
        "original_gsi_vs_d_distance_m_previous_review_only": 39.59,
    },
}


class CSchoolHistoryFailure(ValueError):
    pass


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.data = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "template"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template") and self.skip:
            self.skip -= 1

    def handle_data(self, value):
        if not self.skip:
            self.data.append(value)


def check_source_content(key, raw):
    if not isinstance(raw, bytes) or len(raw) < 100 or len(raw) > 9_000_000:
        raise CSchoolHistoryFailure("C original source length/format invalid")
    filename, url, markers = EXPECTED[key]
    if filename.endswith(".pdf"):
        if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-2048:]:
            raise CSchoolHistoryFailure("Historical PDF does not have original PDF structure")
        return { "validation": "PDF_BYTE_STRUCTURE_CHECKED_MANUAL_PAGE_REVIEW_REQUIRED",
                 "markers_in_html_visible_text": None }
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise CSchoolHistoryFailure("Official HTML encoding invalid") from exc
    if "<html" not in text.lower() or "<body" not in text.lower():
        raise CSchoolHistoryFailure("C source is not HTML")
    parser = VisibleText()
    parser.feed(text)
    visible = " ".join(parser.data)
    for marker in markers:
        if marker not in visible:
            raise CSchoolHistoryFailure(
                "Source content does not support expected date/campus context: " + key
            )
    return {
        "validation": "HTML_SOURCE_CONTEXT_PRESENT_NOT_TEMPORAL_PROOF",
        "markers_in_html_visible_text": list(markers),
    }


def review(archive):
    archive = Path(archive)
    if archive.is_symlink() or not archive.is_dir():
        raise CSchoolHistoryFailure("C original archive missing/unsafe")
    manifest_path = archive / "campus_history_manifest_UNAPPROVED.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise CSchoolHistoryFailure("A source manifest missing/unsafe")
    raw_manifest = manifest_path.read_bytes()
    try:
        manifest = json.loads(raw_manifest)
        t = datetime.fromisoformat(manifest["captured_at_utc"])
    except (TypeError, ValueError, KeyError) as exc:
        raise CSchoolHistoryFailure("A manifest malformed") from exc
    if t.utcoffset() is None or t.utcoffset().total_seconds() != 0:
        raise CSchoolHistoryFailure("A archive timestamp is not UTC")
    if (manifest.get("purpose") != "A_EDOGAWA_CAMPUS_TIMELINE_ORIGINAL_BYTES_UNAPPROVED"
        or manifest.get("official_publication_and_effective_dates_human_reviewed") is not False
        or manifest.get("pdf_campus_map_and_meeting_context_human_review_required") is not True
        or any(manifest.get(flag) is not False for flag in FLAGS)
        or type(manifest.get("approved_cross_source_pairs")) is not int
        or manifest["approved_cross_source_pairs"] != 0
        or type(manifest.get("flood_scenario_classifications_added")) is not int
        or manifest["flood_scenario_classifications_added"] != 0):
        raise CSchoolHistoryFailure("A source manifest claims unsupported approval")
    items = manifest.get("source_items")
    if not isinstance(items, list) or len(items) != len(EXPECTED):
        raise CSchoolHistoryFailure("Seven original campus source items required")
    if {p.name for p in archive.iterdir()} != (
        {x[0] for x in EXPECTED.values()} |
        {"campus_history_manifest_UNAPPROVED.json"}
    ):
        raise CSchoolHistoryFailure("Original source file missing/excess")
    verified, known = {}, set()
    for entry in items:
        if not isinstance(entry, dict):
            raise CSchoolHistoryFailure("Source manifest entry invalid")
        key = entry.get("source_key")
        if key not in EXPECTED or key in known:
            raise CSchoolHistoryFailure("Original source duplicated/unknown")
        known.add(key)
        file, url, _ = EXPECTED[key]
        final = entry.get("final_url")
        if not isinstance(final, str):
            raise CSchoolHistoryFailure("Final source URL missing")
        u = urlsplit(final)
        if (u.scheme != "https" or u.hostname != "www.city.edogawa.tokyo.jp"
            or u.username is not None or u.password is not None
            or u.port not in (None, 443)):
            raise CSchoolHistoryFailure("Source publisher not official municipal host")
        if (entry.get("requested_url") != url or entry.get("archive_filename") != file
            or entry.get("document_format") != ("pdf" if file.endswith(".pdf") else "html")
            or entry.get("reported_page_update_date_not_equivalent_to_effective_date") is not True):
            raise CSchoolHistoryFailure("A source file identity mismatch")
        path = archive / file
        if path.is_symlink() or not path.is_file():
            raise CSchoolHistoryFailure("Stored original missing or symbolic link")
        raw = path.read_bytes()
        if (type(entry.get("byte_size")) is not int
            or entry["byte_size"] != len(raw)
            or sha256(raw).hexdigest() != entry.get("sha256")):
            raise CSchoolHistoryFailure("Stored original SHA256 discrepancy")
        verified[key] = {
            "source_url": url, "source_sha256": entry["sha256"],
            "original_byte_size": len(raw),
            "http_last_modified_transport_only": entry.get("http_last_modified"),
            **check_source_content(key, raw),
        }
    cases = {}
    for school, setting in PRIORITY_REVIEWS.items():
        cases[school] = {
            "municipal_water_source_number": setting["water_source_number"],
            "original_source_revision_review": {
                k: verified[k] for k in setting["independent_html_source_keys"]
            },
            "pdfs_pending_manual_page_reviewer": {
                k: verified[k] for k in setting["historical_pdf_source_keys"]
            },
            "prior_gsi_d_spatial_discrepancy_m_for_triage_only":
                setting["original_gsi_vs_d_distance_m_previous_review_only"],
            "review_concern": setting["concern"],
            "school_campus_timeline_observations_are_not_a_d_facility_join": True,
            "requires_original_water_list_era_and_premises_id_review": True,
            "human_review_date": None,
            "human_reviewer": None,
            "source_effective_time_range_independently_signed": False,
            "c_human_same_physical_site_approved": False,
            "flood_scenario_status": "UNCHANGED_UNKNOWN",
        }
    return {
        "status": STATUS,
        "a_manifest_sha256": sha256(raw_manifest).hexdigest(),
        "captured_at_utc_from_a": manifest["captured_at_utc"],
        "official_source_originals_verified": len(verified),
        "official_html_originals_checked": 5,
        "historical_pdf_originals_byte_structure_checked": 2,
        "pdf_campus_map_page_content_independently_reviewed": False,
        "source_revision_and_school_site_era_human_accepted": False,
        "school_cases_for_future_human_review": cases,
        "unrelated_risk_or_coordinates_not_reclassified": True,
        "c_human_site_pairs_approved": 0,
        "new_flood_eligible_or_excluded": 0,
        "no_D_or_UI_mutation": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive-dir", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    args = p.parse_args()
    if args.report.exists():
        p.error("Refusing to overwrite a previous C review artifact")
    try:
        report = review(args.archive_dir)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    except (OSError, CSchoolHistoryFailure) as exc:
        p.exit(2, "C campus-history original audit failed: " + str(exc) + "\n")
    print(json.dumps({"status": report["status"],
                      "original_sources": report["official_source_originals_verified"],
                      "site_identity_approved": 0, "flood_status_changes": 0},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
