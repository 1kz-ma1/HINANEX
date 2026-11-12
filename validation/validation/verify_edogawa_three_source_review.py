"""C independent validation of unapproved Edogawa GSI + water + current-D leads.

This does not approve physical locations or hazard classification. An unchanged
UNKNOWN D Scenario is a required prerequisite.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re
import unicodedata

from audit_gsi_edogawa_original import audit as audit_original_gsi
from verify_edogawa_water_join import water_rows, AuditFailure


class ThreeSourceAuditFailure(ValueError):
    pass


def require(value, error):
    if not value:
        raise ThreeSourceAuditFailure(error)


def canonical_name(raw):
    s = re.sub(r"[\s\u3000]+", "", unicodedata.normalize("NFKC", raw))
    if s.endswith("(注)"):
        s = s[:-3]
    for a, b in (
        ("江戸川区立", ""), ("都立", ""), ("私立", ""), ("区立", ""),
        ("高等学校", "高"), ("小学校", "小"), ("中学校", "中"),
        ("第一", "一"), ("第二", "二"), ("第三", "三"),
        ("第四", "四"), ("第五", "五"), ("第六", "六"),
        ("第七", "七"), ("第八", "八"), ("第九", "九"),
    ):
        s = s.replace(a, b)
    return s


def canonical_address(raw):
    s = re.sub(r"[\s\u3000]+", "", unicodedata.normalize("NFKC", raw))
    if s.startswith("東京都"):
        s = s[3:]
    if s.startswith("江戸川区"):
        s = s[4:]
    s = re.sub(r"([一二三四五六七八九])丁目",
               lambda m: str("一二三四五六七八九".index(m.group(1))+1) + "-", s)
    for a, b in (("番地", "-"), ("丁目", "-"), ("番", "-"), ("号", "")):
        s = s.replace(a, b)
    return s.strip("-")


def geo_m(g_lat, g_lon, d_lat, d_lon):
    coords = [float(v) for v in (g_lat, g_lon, d_lat, d_lon)]
    require(all(map(math.isfinite, coords)), "Nonfinite original coordinates")
    phi1, l1, phi2, l2 = map(math.radians, coords)
    h = math.sin((phi2-phi1)/2)**2 + (
        math.cos(phi1)*math.cos(phi2)*math.sin((l2-l1)/2)**2
    )
    return round(12742000*math.asin(min(1, math.sqrt(h))), 2)


def audit(water_html, gsi_national, a_water_bytes, a_gsi_bytes,
          current_d_bytes, c_base_bytes, a_matrix_bytes):
    # Existing C verifier fully re-reads the original GSI 17MB and ensures
    # A extract/current D and C existing audit refer to the same revisions.
    original = audit_original_gsi(gsi_national, a_gsi_bytes,
                                 current_d_bytes, c_base_bytes)
    try:
        aw, ag, d, c, mat = map(
            json.loads, (a_water_bytes, a_gsi_bytes,
                         current_d_bytes, c_base_bytes, a_matrix_bytes)
        )
        water, _ = water_rows(water_html)
    except (TypeError, ValueError, AuditFailure, KeyError) as exc:
        raise ThreeSourceAuditFailure("Inputs cannot be parsed independently") from exc
    require(mat.get("purpose") == "A_THREE_SOURCE_NAME_ADDRESS_REVIEW_LEADS_NOT_VERIFIED"
            and mat.get("human_c_site_pairs_approved") == 0
            and mat.get("flood_classifications_added") == 0,
            "A matrix claims verified locations or classifications")
    sha = mat.get("source_sha256", {})
    require(sha.get("municipal_water_original") == sha256(water_html).hexdigest()
            and sha.get("a_source_pinned_water_ledger") == sha256(a_water_bytes).hexdigest()
            and sha.get("gsi_national_original") == sha256(gsi_national).hexdigest()
            and sha.get("a_gsi_original_extraction") == sha256(a_gsi_bytes).hexdigest()
            and sha.get("current_d_region_export") == sha256(current_d_bytes).hexdigest()
            and c.get("source_sha256", {}).get("city_saved_water_html") ==
            sha256(water_html).hexdigest(), "A/C original provenance mismatch")
    require(aw.get("all_reviewed_pairs") == aw.get("all_scenario_classifications_added") == 0
            and len(aw.get("rows", [])) == len(water),
            "A water source evidence has changed or claims approval")
    dsets = [x for x in d["datasets"] if x["requirement_code"] == "shelter_location"]
    require(len(dsets) == 1, "D locations ambiguous")
    d_by_id = {x["id"]: x for x in dsets[0]["records"]}
    require(len(d_by_id) == len(dsets[0]["records"]), "D IDs duplicated")
    g_rows = ag.get("edogawa_rows", [])
    require(len(g_rows) == original["edogawa_gsi_rows_independently_checked"],
            "GSI row source count differs")
    require(len(mat.get("water_rows", [])) == len(water) and
            mat.get("water_rows_total") == len(water) and
            mat.get("gsi_edogawa_rows_source") == len(g_rows) and
            mat.get("d_location_rows_source") == len(d_by_id),
            "Matrix source counts differ")
    counts, usage = Counter(), Counter()
    observed = []
    for src, a_water, matrix_row in zip(water, aw["rows"], mat["water_rows"]):
        require(matrix_row.get("water_source_record_trace") ==
                a_water["source_record_trace"] ==
                f"table={src['official_table']};row={src['official_table_row']}",
                "Water source row trace/ordering differs")
        for key, a_key, m_key in (
            ("official_number_raw", "number_raw", "water_number_raw"),
            ("official_name_raw", "name_raw", "water_name_raw"),
            ("official_address_raw", "address_raw", "water_address_raw"),
            ("official_usable_floor_raw", "usable_floor_raw", "water_floor_raw"),
        ):
            require(src[key] == a_water[a_key] == matrix_row.get(m_key),
                    "Municipal original water source row differs")
        require(matrix_row.get("cross_source_status") == "UNREVIEWED"
                and matrix_row.get("flood_specific_eligibility") == "UNKNOWN"
                and matrix_row.get("no_gsi_lead_does_not_mean_no_publication") is True,
                "A water row prematurely approved or excluded")
        dids = [v["location_facility_id"]
                for v in a_water["candidate_location_rows"]]
        require(matrix_row.get("a_d_name_hint_ids") == dids
                and len(set(dids)) == len(dids)
                and all(x in d_by_id for x in dids), "A matrix D hints differ")
        # Independently recompute ALL name/address leads; spatial proximity
        # CANNOT create a new lead. No hardcoded count of 111.
        expected = {}
        for entry in g_rows:
            row = entry["original_columns_unmodified"]
            same_name = canonical_name(src["official_name_raw"]) == canonical_name(row["施設・場所名"])
            same_address = canonical_address(src["official_address_raw"]) == canonical_address(row["住所"])
            if same_name or same_address:
                ident = row["共通ID"]
                expected[ident] = (entry, same_name, same_address)
        candidates = matrix_row.get("gsi_review_leads")
        require(isinstance(candidates, list)
                and len(candidates) == len(expected)
                and matrix_row.get("gsi_review_lead_count") == len(expected),
                "A matrix omitted/added GSI lead")
        got = set()
        for candidate in candidates:
            gid = candidate.get("gsi_common_id_raw")
            require(gid in expected and gid not in got, "GSI ID altered/repeated")
            got.add(gid)
            entry, same_name, same_address = expected[gid]
            g = entry["original_columns_unmodified"]
            for mk, gk in (
                ("gsi_name_raw", "施設・場所名"),
                ("gsi_address_raw", "住所"),
                ("gsi_flood_raw", "洪水"),
                ("gsi_earthquake_raw", "地震"),
                ("gsi_latitude_raw", "緯度"),
                ("gsi_longitude_raw", "経度"),
            ):
                require(candidate.get(mk) == g[gk], "Official GSI raw value mutated")
            require(candidate.get("gsi_national_source_line") == entry["original_national_csv_row"]
                    and candidate.get("review_name_key_equal") is same_name
                    and candidate.get("review_address_key_equal") is same_address
                    and candidate.get("gsi_common_id_is_not_d_id") is True
                    and candidate.get("c_human_same_site_approved") is False
                    and candidate.get("flood_scenario_result") == "UNCHANGED_UNKNOWN",
                    "A/GSI review hint changed to an unauthorized assertion")
            distances = candidate.get("d_source_hint_distances")
            require(isinstance(distances, list) and len(distances) == len(dids),
                    "A GSI-to-D source distance list incomplete")
            for dist, ident in zip(distances, dids):
                record = d_by_id[ident]
                require(dist["d_facility_id"] == ident
                        and dist["d_facility_name_raw"] == record["name"]
                        and dist["distance_m_not_identity"] ==
                        geo_m(g["緯度"], g["経度"], record["latitude"], record["longitude"]),
                        "A GSI-to-D source distance altered")
            flags = []
            if not same_name:
                flags.append("NAME_NORMALIZATION_DIFFERS_REVIEW")
            if not same_address:
                flags.append("ADDRESS_NORMALIZATION_DIFFERS_REVIEW")
            if any(distance["distance_m_not_identity"] > 100
                   for distance in distances):
                flags.append("GSI_VS_D_REPRESENTATIVE_POINT_OVER_100M_REVIEW")
            require(candidate.get("documentary_discrepancy_flags") == flags
                    and candidate.get("distance_threshold_is_not_eligibility_or_identity_gate") is True,
                    "Discrepancy flags missing/altered in A matrix")
            usage[gid] += 1
        counts[str(len(expected))] += 1
        observed.append({
            "water_source_trace": matrix_row["water_source_record_trace"],
            "gsi_candidate_ids_recomputed": sorted(expected),
            "gsi_leads_count": len(expected),
        })
    require(dict(sorted(counts.items())) ==
            mat.get("number_of_gsi_leads_per_water_row") and
            sorted(k for k, v in usage.items() if v > 1) ==
            mat.get("gsi_ids_proposed_for_multiple_water_sites"),
            "Matrix histogram or multi-site GSI collisions changed")
    return {
        "status": "C_THREE_SOURCE_RAW_CONSISTENCY_CHECKED_HUMAN_REVIEW_ONLY",
        "municipal_water_original_sha256": sha256(water_html).hexdigest(),
        "gsi_national_original_sha256": sha256(gsi_national).hexdigest(),
        "current_d_source_sha256": sha256(current_d_bytes).hexdigest(),
        "a_matrix_source_sha256": sha256(a_matrix_bytes).hexdigest(),
        "water_rows_independently_verified": len(water),
        "gsi_edogawa_original_rows_independently_verified": len(g_rows),
        "current_d_locations": len(d_by_id),
        "gsi_review_leads_per_water_row": dict(sorted(counts.items())),
        "gsi_id_multiple_water_site_review_conflicts": sorted(
            k for k, v in usage.items() if v > 1),
        "row_to_gsi_review_leads_without_site_signoff": observed,
        "any_name_or_address_key_match_is_not_evidence_of_physical_identity": True,
        "gsi_flood_blank_is_not_an_exclusion": True,
        "independent_c_human_site_pairs_approved": 0,
        "d_flood_classifications_added": 0,
        "all_current_d_flood_statuses_unknown": True,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("water-html", "gsi-national", "a-water-ledger", "a-gsi-report",
                 "current-d", "c-source-audit", "a-matrix", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    x = ap.parse_args()
    if x.out.exists():
        ap.error("Cannot overwrite C raw audit")
    result = audit(x.water_html.read_bytes(), x.gsi_national.read_bytes(),
                   x.a_water_ledger.read_bytes(), x.a_gsi_report.read_bytes(),
                   x.current_d.read_bytes(), x.c_source_audit.read_bytes(),
                   x.a_matrix.read_bytes())
    x.out.parent.mkdir(parents=True, exist_ok=True)
    x.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"],
                      "water_rows": result["water_rows_independently_verified"],
                      "gsi_leads_histogram": result["gsi_review_leads_per_water_row"],
                      "approved_pairs": 0, "flood_decisions": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
