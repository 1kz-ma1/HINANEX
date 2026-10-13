"""A: Source-pinned THREE-WAY water/GSI/D review leads; NEVER approve joins.

All outputs are unreviewed outside Git. Municipality water list, GSI's
earthquake-designated emergency places and D locations have different meanings.

python data-research/tools/edogawa_three_source_review.py \
 --water-html /external/water_facilities.html \
 --a-water-ledger /external/A_current_D_unapproved.json \
 --a-gsi-report /external/gsi_edogawa_review_UNREVIEWED.json \
 --current-d /external/edogawa_current_D_UNREVIEWED.json \
 --out /external/A_three_source_UNAPPROVED.json
"""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import unicodedata

from edogawa_review_ledger import official_rows

PURPOSE = "A_THREE_SOURCE_NAME_ADDRESS_REVIEW_LEADS_NOT_VERIFIED"
GSI_ORIGIN = "https://hinanmap.gsi.go.jp/hinanjocp/defaultFtpData/csv/mergeFromCity_2.csv"


def normalize_name(value):
    """Conservative, disclosed Japanese school abbreviation search KEY only."""
    s = re.sub(r"\s+", "", unicodedata.normalize("NFKC", value))
    s = re.sub(r"\(注\)$", "", s)
    for old, new in (
        ("江戸川区立", ""), ("都立", ""), ("私立", ""), ("区立", ""),
        ("高等学校", "高"), ("小学校", "小"), ("中学校", "中"),
        ("第一", "一"), ("第二", "二"), ("第三", "三"),
        ("第四", "四"), ("第五", "五"), ("第六", "六"),
        ("第七", "七"), ("第八", "八"), ("第九", "九"),
    ):
        s = s.replace(old, new)
    return s


def normalize_address(value):
    """Compare only standard municipality / chome-ban-go renderings."""
    s = re.sub(r"\s+", "", unicodedata.normalize("NFKC", value))
    for prefix in ("東京都", "江戸川区"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    s = re.sub(r"([一二三四五六七八九])丁目",
               lambda m: str("一二三四五六七八九".index(m.group(1)) + 1) + "-",
               s)
    return s.replace("丁目", "-").replace("番地", "-").replace("番", "-").replace("号", "").strip("-")


def meters(a, b, c, d):
    aa, bb, cc, dd = map(math.radians, (float(a), float(b), float(c), float(d)))
    h = math.sin((cc-aa)/2)**2 + math.cos(aa)*math.cos(cc)*math.sin((dd-bb)/2)**2
    return round(12742000 * math.asin(min(1, math.sqrt(h))), 2)


def generate(water_raw, a_water_raw, gsi_report_raw, d_raw):
    water = official_rows(water_raw)
    aw, g, d = map(json.loads, (a_water_raw, gsi_report_raw, d_raw))
    if (aw.get("all_reviewed_pairs") != 0 or
        aw.get("all_scenario_classifications_added") != 0 or
        len(aw.get("rows", [])) != len(water) or
        {x.get("sha256") for x in aw.get("source_documents", [])} !=
        {sha256(water_raw).hexdigest(), sha256(d_raw).hexdigest(),
         next((x["sha256"] for x in aw["source_documents"]
               if x.get("type") == "municipal_location_csv"), None)}):
        raise ValueError("Water/A source version or unreviewed boundary invalid")
    if (g.get("status") != "GSI_EDOGAWA_ROWS_FOUND_UNREVIEWED" or
        g.get("independent_c_site_approvals") != 0 or
        g.get("new_flood_classifications") != 0 or
        g.get("none_of_this_data_was_joined_to_current_d") is not True or
        g.get("source_manifest", {}).get("requested_url") != GSI_ORIGIN):
        raise ValueError("GSI source report or approval boundary invalid")
    if str(d.get("region", {}).get("code")) != "13123":
        raise ValueError("Not Edogawa current D")
    dsets = [x for x in d.get("datasets", []) if x.get("requirement_code") == "shelter_location"]
    if len(dsets) != 1 or len(d.get("scenarios", [])) != 1:
        raise ValueError("Current D location and Scenario required")
    byid = {r["id"]: r for r in dsets[0]["records"]}
    if len(byid) != len(dsets[0]["records"]):
        raise ValueError("Ambiguous D IDs")
    results = d["scenarios"][0].get("facility_results", [])
    if (len(results) != len(byid) or
        {r["facility_id"] for r in results} != set(byid) or
        any(r["status"] != "UNKNOWN" or r["fact"]["join_status"] != "UNVERIFIED"
            for r in results)):
        raise ValueError("Current D flood Scenario is not unreviewed")
    gitems = g["edogawa_rows"]
    if not isinstance(gitems, list) or len({x["original_columns_unmodified"]["共通ID"] for x in gitems}) != len(gitems):
        raise ValueError("GSI common IDs duplicate")
    matrix, counts, used = [], Counter(), Counter()
    for water_row, a_row in zip(water, aw["rows"]):
        if (water_row["source_record_trace"] != a_row["source_record_trace"] or
            water_row["name_raw"] != a_row["name_raw"] or
            water_row["address_raw"] != a_row["address_raw"] or
            a_row.get("review_status") not in ("UNREVIEWED", "CONFLICT") or
            a_row.get("flood_scenario_status") != "UNCHANGED_UNKNOWN"):
            raise ValueError("Water source row mutated in A ledger")
        dids = [x["location_facility_id"] for x in a_row["candidate_location_rows"]]
        if len(set(dids)) != len(dids) or any(i not in byid for i in dids):
            raise ValueError("A contains unsupported D facility ID")
        matches = []
        for item in gitems:
            row = item["original_columns_unmodified"]
            # These are independently observed strings, NOT authoritative identity keys.
            name = normalize_name(water_row["name_raw"]) == normalize_name(row["施設・場所名"])
            addr = normalize_address(water_row["address_raw"]) == normalize_address(row["住所"])
            if not (name or addr):
                continue
            gid = row["共通ID"]
            used[gid] += 1
            spatial = [{
                "d_facility_id": ident,
                "d_facility_name_raw": byid[ident]["name"],
                "distance_m_not_identity": meters(
                    row["緯度"], row["経度"],
                    byid[ident]["latitude"], byid[ident]["longitude"]),
            } for ident in dids]
            matches.append({
                "gsi_common_id_raw": gid,
                "gsi_national_source_line": item["original_national_csv_row"],
                "gsi_name_raw": row["施設・場所名"],
                "gsi_address_raw": row["住所"],
                "gsi_flood_raw": row["洪水"],
                "gsi_earthquake_raw": row["地震"],
                "gsi_latitude_raw": row["緯度"],
                "gsi_longitude_raw": row["経度"],
                "review_name_key_equal": name,
                "review_address_key_equal": addr,
                "d_source_hint_distances": spatial,
                "gsi_common_id_is_not_d_id": True,
                "c_human_same_site_approved": False,
                "flood_scenario_result": "UNCHANGED_UNKNOWN",
            })
        matches.sort(key=lambda v: v["gsi_common_id_raw"])
        counts[str(len(matches))] += 1
        matrix.append({
            "water_source_record_trace": water_row["source_record_trace"],
            "water_number_raw": water_row["number_raw"],
            "water_name_raw": water_row["name_raw"],
            "water_address_raw": water_row["address_raw"],
            "water_floor_raw": water_row["usable_floor_raw"],
            "a_d_name_hint_ids": dids,
            "gsi_review_leads": matches,
            "gsi_review_lead_count": len(matches),
            "cross_source_status": "UNREVIEWED",
            "no_gsi_lead_does_not_mean_no_publication": True,
            "flood_specific_eligibility": "UNKNOWN",
        })
    # An identical GSI ID proposed for multiple water sites is itself a conflict.
    collisions = sorted(k for k, v in used.items() if v > 1)
    return {
        "purpose": PURPOSE,
        "source_sha256": {
            "municipal_water_original": sha256(water_raw).hexdigest(),
            "a_source_pinned_water_ledger": sha256(a_water_raw).hexdigest(),
            "gsi_national_original": g["source_manifest"]["national_source_sha256"],
            "a_gsi_original_extraction": sha256(gsi_report_raw).hexdigest(),
            "current_d_region_export": sha256(d_raw).hexdigest(),
        },
        "water_rows_total": len(water),
        "gsi_edogawa_rows_source": len(gitems),
        "d_location_rows_source": len(byid),
        "number_of_gsi_leads_per_water_row": dict(sorted(counts.items())),
        "gsi_ids_proposed_for_multiple_water_sites": collisions,
        "source_name_address_key_comparisons_are_not_site_approvals": True,
        "no_spatial_distance_was_used_to_select_a_candidate": True,
        "water_rows": matrix,
        "human_c_site_pairs_approved": 0,
        "flood_classifications_added": 0,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("water-html", "a-water-ledger", "a-gsi-report", "current-d", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("Cannot overwrite existing evidence")
    out = generate(args.water_html.read_bytes(), args.a_water_ledger.read_bytes(),
                   args.a_gsi_report.read_bytes(), args.current_d.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "water_rows": out["water_rows_total"],
        "gsi_leads_per_row": out["number_of_gsi_leads_per_water_row"],
        "human_approved": 0,
        "new_flood_status": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
