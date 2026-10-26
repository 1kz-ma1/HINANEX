"""C-side conservative text-only comparison of skhb02 raw versus AI-transcribed city pages.

This is an unapproved cross-document textual audit. A matching facility name
and address cannot prove facility identity, source currentness, hazard safety,
opening status, publication permission or human independent C acceptance.
No live network calls, no GIS consumer or RegionExport mutations.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

PREFIX = "千葉県市川市"
SOURCE_URL = "https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
CITY_URL = "https://www.city.ichikawa.lg.jp/page/40332.html"
PDFS = {
    "A": "https://www.city.ichikawa.lg.jp/uploaded/attachment/55017.pdf",
    "C": "https://www.city.ichikawa.lg.jp/uploaded/attachment/55026.pdf",
}
STATUS = "C_AI_TRANSCRIBED_TEXT_CROSSCHECK_UNAPPROVED"
ALLOWED_REF_KEYS = {
    "status", "gsi_source_url", "gsi_sha256", "expected_total_tile_features",
    "candidate_address_prefix", "city_page_url", "city_page_update_date",
    "transcription_method", "municipal_pdf_hazard_column_label", "rows",
}
ALLOWED_ROW_KEYS = {
    "gsi_feature_index", "city_section", "city_row_number", "city_name",
    "city_address", "city_pdf_url", "landslide_symbol_transcribed",
}


def compare_textual_sources(raw: bytes, reference: dict) -> dict:
    """Every address-prefix candidate must be accounted for; no fuzzy matching.

    Reference rows are *AI transcriptions*, NOT independent authoritative
    evidence or proof that the PDFs have not changed since inspection.
    """
    if type(raw) is not bytes or not 0 < len(raw) <= 12_000_000:
        raise ValueError("SOURCE_BYTES_INVALID")
    if not isinstance(reference, dict) or set(reference) != ALLOWED_REF_KEYS:
        raise ValueError("REFERENCE_SCHEMA_INVALID")
    pinned = {
        "status": "AI_TRANSCRIBED_OFFICIAL_TABLE_UNAPPROVED",
        "gsi_source_url": SOURCE_URL, "candidate_address_prefix": PREFIX,
        "city_page_url": CITY_URL, "city_page_update_date": "2026-09-08",
        "transcription_method":
            "AI_EXTRACTED_FROM_OFFICIAL_HTML_AND_PDF_RENDER_NOT_HUMAN_APPROVED",
        "municipal_pdf_hazard_column_label": "土砂災害",
    }
    for key, value in pinned.items():
        if type(reference[key]) is not type(value) or reference[key] != value:
            raise ValueError("REFERENCE_SOURCE_OR_STATUS_MISMATCH:" + key)
    digest = sha256(raw).hexdigest()
    if reference["gsi_sha256"] != digest:
        raise ValueError("SOURCE_DIGEST_MISMATCH")
    try:
        doc = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("SOURCE_JSON_INVALID") from exc
    if not isinstance(doc, dict) or doc.get("type") != "FeatureCollection":
        raise ValueError("SOURCE_NOT_FEATURE_COLLECTION")
    features = doc.get("features")
    if not isinstance(features, list) or (
        type(reference["expected_total_tile_features"]) is not int
        or reference["expected_total_tile_features"] != len(features)
    ):
        raise ValueError("SOURCE_TILE_COUNT_MISMATCH")
    if not isinstance(reference["rows"], list):
        raise ValueError("REFERENCE_ROWS_INVALID")
    candidate_indices = set()
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
            raise ValueError("SOURCE_FEATURE_INVALID")
        address = feature["properties"].get("address")
        if isinstance(address, str) and address.startswith(PREFIX):
            candidate_indices.add(index)
    recorded_indices = set()
    city_names = set()
    entries = []
    for row in reference["rows"]:
        if not isinstance(row, dict) or set(row) != ALLOWED_ROW_KEYS:
            raise ValueError("REFERENCE_ROW_SCHEMA_INVALID")
        index = row["gsi_feature_index"]
        if type(index) is not int or index not in candidate_indices:
            raise ValueError("REFERENCE_ROW_NOT_GSI_CITY_CANDIDATE")
        if index in recorded_indices:
            raise ValueError("DUPLICATE_GSI_INDEX")
        recorded_indices.add(index)
        section = row["city_section"]
        if section not in PDFS or row["city_pdf_url"] != PDFS[section]:
            raise ValueError("MUNICIPAL_PDF_SOURCE_MISMATCH")
        if type(row["city_row_number"]) is not int or row["city_row_number"] <= 0:
            raise ValueError("MUNICIPAL_ROW_NUMBER_INVALID")
        name, address = row["city_name"], row["city_address"]
        if any(type(v) is not str or not v.strip() for v in (name, address)):
            raise ValueError("MUNICIPAL_ROW_FIELDS_INVALID")
        if name in city_names:
            raise ValueError("DUPLICATED_OFFICIAL_NAME_AMBIGUOUS")
        city_names.add(name)
        if row["landslide_symbol_transcribed"] != "○":
            raise ValueError("MUNICIPAL_LANDSLIDE_SYMBOL_NOT_EXPECTED")
        p = features[index]["properties"]
        if type(p.get("disaster2")) is not int or p["disaster2"] != 1:
            raise ValueError("GSI_LANDSLIDE_MARKER_NOT_VERIFIED")
        name_ok = p.get("name") == name
        address_ok = p.get("address") == PREFIX + address
        if name_ok and address_ok:
            result = "NAME_ADDRESS_TEXT_AGREE_UNAPPROVED"
        elif name_ok:
            result = "NAME_TEXT_ONLY_ADDRESS_REVIEW_REQUIRED"
        else:
            result = "NAME_DIFFERENCE_REVIEW_REQUIRED"
        entries.append({
            "gsi_feature_index": index,
            "municipal_section": section,
            "municipal_row_number": row["city_row_number"],
            "gsi_name_raw": p.get("name"),
            "gsi_address_raw": p.get("address"),
            "municipal_name_ai_transcribed": name,
            "municipal_address_ai_transcribed": address,
            "municipal_pdf_url": row["city_pdf_url"],
            "municipal_landslide_symbol_ai_transcribed": "○",
            "result": result,
            "facility_identity_approved": False,
            "currently_open_or_safe": False,
        })
    if candidate_indices != recorded_indices:
        raise ValueError("CANDIDATE_COVERAGE_NOT_RECONCILED")
    exact = sum(r["result"] == "NAME_ADDRESS_TEXT_AGREE_UNAPPROVED" for r in entries)
    name_only = sum(r["result"] == "NAME_TEXT_ONLY_ADDRESS_REVIEW_REQUIRED"
                    for r in entries)
    other = len(entries) - exact - name_only
    return {
        "status": STATUS,
        "tile_only_source_sha256": digest,
        "tile_total_features": len(features),
        "city_prefix_candidate_count": len(entries),
        "text_name_and_address_agreement_count": exact,
        "text_name_only_address_review_count": name_only,
        "other_difference_count": other,
        "municipal_document_transcription_authenticated": False,
        "official_pdf_byte_hash_checked": False,
        "municipality_boundary_verified": False,
        "independent_human_c_approved": False,
        "facility_identity_approved": False,
        "disaster_use_approved": False,
        "current_shelter_opening_verified": False,
        "safe_destination_count_approved": 0,
        "rows": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.report_out.exists() or args.report_out.is_symlink():
            raise ValueError("OUTPUT_ALREADY_EXISTS")
        if args.raw.stat().st_size > 12_000_000:
            raise ValueError("SOURCE_TOO_LARGE")
        output = compare_textual_sources(
            args.raw.read_bytes(),
            json.loads(args.reference.read_text(encoding="utf-8")),
        )
        args.report_out.write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "status": output["status"],
            "source_sha256": output["tile_only_source_sha256"],
            "city_prefix_candidates": output["city_prefix_candidate_count"],
            "exact_text_agreements": output["text_name_and_address_agreement_count"],
            "name_only_address_review": output["text_name_only_address_review_count"],
            "independent_human_c_approved": False,
        }, ensure_ascii=False))
        return 0
    except (ValueError, OSError, TypeError) as exc:
        print("C ICHIKAWA TEXT CHECK BLOCKED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
