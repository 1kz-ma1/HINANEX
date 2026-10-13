"""C: fail-closed verification of an unapproved Edogawa water-facility ledger.

Example:
  python validation/validation/verify_edogawa_water_join.py \
    --water-html local_saved_city_page.html \
    --location-csv 20251211_hinanhokan.csv \
    --region-export edogawa.json \
    --a-ledger edogawa_review_ledger.json \
    --report local_c_evidence_audit.json

This is a snapshot integrity / provenance audit, NOT an independent fetch
from the municipal server, certified facility identity match or flood verdict.
Neither official source bytes nor the generated ledger should be committed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import unicodedata
from collections import Counter

WATER_URL = ("https://www.city.edogawa.tokyo.jp/e007/bosaianzen/"
             "bosai/kanrenmap/hazardmap/ikinaihinan.html")
WATER_HEADER = ("番号", "名称", "住所", "電話番号", "使用可能階数")
LOCATION_HEADER = ("名称", "URL", "災害種別記号", "コメント", "緯度", "経度")
HINT_CLASSES = {"NAME_ALIGNED_HINT", "NAME_ABBREVIATION_HINT", "MANUAL_REVIEW_REQUIRED"}


class AuditFailure(Exception):
    pass


def require(condition, message):
    if not condition:
        raise AuditFailure(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class SourceTables(HTMLParser):
    """Standalone C parser: do not import or trust A's parser."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.table, self.row, self.cell = [], None, None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            require(self.table is None, "Nested municipal tables")
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("th", "td") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("th", "td") and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def water_rows(raw):
    decoded = raw.decode("utf-8-sig")
    require(WATER_URL in decoded, "Official URL missing from saved HTML")
    parser = SourceTables()
    parser.feed(decoded)
    result = []
    table_count = 0
    for i, table in enumerate(parser.tables, start=1):
        if not table or tuple(table[0]) != WATER_HEADER:
            continue
        table_count += 1
        for j, cells in enumerate(table[1:], start=2):
            require(len(cells) == 5 and cells[1] and cells[2],
                    "Malformed water-source facility row")
            result.append({
                "official_table": i,
                "official_table_row": j,
                "official_number_raw": cells[0],
                "official_name_raw": cells[1],
                "official_address_raw": cells[2],
                "official_phone_raw": cells[3],
                "official_usable_floor_raw": cells[4],
            })
    require(result, "No municipality water-facility table")
    return result, table_count


def hint_name(name):
    name = unicodedata.normalize("NFKC", name)
    return re.sub(r"\(注\)$", "", re.sub(r"[\s\u3000]+", "", name))


def short_name(name):
    name = hint_name(name)
    for a, b in (("高等学校", "高校"), ("都立", ""), ("区立", ""),
                 ("第七", "七"), ("第六", "六"), ("第五", "五"),
                 ("第四", "四"), ("第三", "三"), ("第二", "二"), ("第一", "一")):
        name = name.replace(a, b)
    return name


def normalize_a_ledger(a, hashes, csv_columns, by_id):
    """Support the A #133 proposal output and prior user-facing A review report.

    Both are *unapproved* hints. No classification or verified link is imported.
    """
    if "official_water_facility_ledger" in a:
        old_lookup = a.get("location_record_lookup", [])
        require(len(old_lookup) == len(by_id) and
                {i["id"] for i in old_lookup} == set(by_id),
                "A snapshot location lookup mismatches official location dataset")
        for item in old_lookup:
            d = by_id[item["id"]]
            for key in ("name", "latitude", "longitude", "address", "facility_type"):
                require(item.get(key) == d.get(key),
                        "A location lookup differs in " + key)
            require(str(item.get("flood_classification", "")).startswith("UNKNOWN"),
                    "A snapshot illegally claims a flood classification")
        return a["official_water_facility_ledger"]

    require("rows" in a, "Unrecognized A ledger schema")
    require(a.get("region_code") == "13123" and
            a.get("record_count_from_current_export") == len(by_id),
            "A ledger region or D record count inconsistent")
    require(a.get("location_csv_columns") == csv_columns,
            "A ledger municipal CSV header inconsistent")
    docs = a.get("source_documents", [])
    require(len(docs) == 3 and {d.get("sha256") for d in docs} == hashes,
            "A recorded source digests mismatch")
    require(a.get("all_reviewed_pairs") == 0 and
            a.get("all_scenario_classifications_added") == 0,
            "A ledger claims unapproved pairs/classifications")
    rows = []
    for r in a["rows"]:
        require(r.get("review_status") in ("UNREVIEWED", "CONFLICT"),
                "A review unexpectedly marks a verified pair")
        trace = re.fullmatch(r"table=(\d+);row=(\d+)",
                             r.get("source_record_trace", ""))
        require(trace, "A official row trace malformed")
        hints = r.get("candidate_location_rows", [])
        require(isinstance(hints, list), "A candidate rows missing")
        reason = {h.get("matching_basis") for h in hints}
        if len(hints) == 1:
            require(reason in ({"NAME_HINT_ONLY_NOT_VERIFIED"},
                               {"ABBREVIATION_HINT_ONLY_NOT_VERIFIED"}),
                    "A uses a forbidden auto-join basis")
            label = ("NAME_ALIGNED_HINT" if reason == {"NAME_HINT_ONLY_NOT_VERIFIED"}
                     else "NAME_ABBREVIATION_HINT")
        else:
            label = "MANUAL_REVIEW_REQUIRED"
        for hint in hints:
            ident = hint.get("location_facility_id")
            require(ident in by_id, "A candidate location ID not found")
            require(hint.get("location_name_raw") == by_id[ident]["name"],
                    "A candidate location name differs from D")
            require(hint.get("location_address_raw") == by_id[ident].get("address"),
                    "A invented a location-side address")
            require(hint.get("address_raw_exact_match") is None,
                    "A cannot certify address equality without location-side address")
        rows.append({
            "official_table": int(trace[1]),
            "official_table_row": int(trace[2]),
            "official_number_raw": r.get("number_raw"),
            "official_name_raw": r.get("name_raw"),
            "official_address_raw": r.get("address_raw"),
            "official_phone_raw": r.get("phone_raw"),
            "official_usable_floor_raw": r.get("usable_floor_raw"),
            "source_url": r.get("source_url"),
            "C_independent_verified": False,
            "D_scenario_status": r.get("flood_scenario_status"),
            "candidate_class": label,
            "candidate_count": len(hints),
            "candidate_location_ids": [h.get("location_facility_id") for h in hints],
            "candidate_location_names": [h.get("location_name_raw") for h in hints],
        })
    return rows




# Manual reference observations from the saved official water list and institution
# sites (2026-10-13). These are review prompts, NEVER an identity certificate.
# No live institution-site HTML is fetched or archived by this checker.
PRIORITY_SCHOOL_REFERENCES = (
    {
        "official_number": "108",
        "water_name": "都立 葛西工高等学校",
        "location_name": "都立葛西工科高校",
        "water_address": "一之江7丁目68番1号",
        "water_phone": "03-3653-4111",
        "water_floor_raw": "2階以上",
        "expected_location_id": "edogawa-d79a702373c6add7",
        "location_url": "https://www.metro.ed.jp/kasaikoka-h/",
        "institution_authority_url": "https://www.metro.ed.jp/kasaikoka-h/access/access.html",
        "city_directory_url": "https://www.city.edogawa.tokyo.jp/e004/kuseijoho/gaiyo/shisetsuguide/bunya/gakko/toritsushiritsu.html",
    },
    {
        "official_number": "109",
        "water_name": "私立 関東一高等学校",
        "location_name": "関東第一高校",
        "water_address": "松島2丁目10番11号",
        "water_phone": "03-3653-1541",
        "water_floor_raw": "3階以上",
        "expected_location_id": "edogawa-fbe048a8e7100768",
        "location_url": "http://www.kanto-ichiko.ac.jp/",
        "institution_authority_url": "https://www.kanto-ichiko.ac.jp/about/outline/",
        "city_directory_url": "https://www.city.edogawa.tokyo.jp/e004/kuseijoho/gaiyo/shisetsuguide/bunya/gakko/toritsushiritsu.html",
    },
)


def review_priority_identity_leads(water, location_raw_rows, records):
    """Validate snapshot/ID/source-URL claims; DO NOT approve cross-source join.

    Municipality water-standby and D location are different datasets without
    a common authoritative ID. The institution pages cited in the returned
    results must still be independently archived and checked by C.
    """
    results = []
    for reference in PRIORITY_SCHOOL_REFERENCES:
        official = [w for w in water
                    if w["official_number_raw"] == reference["official_number"]]
        if not official:
            continue  # Synthetic fixture / incomplete municipality snapshot.
        require(len(official) == 1, "Priority official row duplicated")
        w = official[0]
        for field, expected in (
            ("official_name_raw", reference["water_name"]),
            ("official_address_raw", reference["water_address"]),
            ("official_phone_raw", reference["water_phone"]),
            ("official_usable_floor_raw", reference["water_floor_raw"]),
        ):
            require(w[field] == expected,
                    "Priority official water row source changed: " + field)
        found = [r for r in records if r.get("name") == reference["location_name"]]
        source = [r for r in location_raw_rows
                  if r.get("名称") == reference["location_name"]]
        require(len(found) == len(source) == 1,
                "Priority D/CSV institution name missing or ambiguous")
        d, raw = found[0], source[0]
        require(d.get("id") == reference["expected_location_id"],
                "Priority D facility ID changed; manual re-review required")
        require(d.get("detail_url") == raw.get("URL") == reference["location_url"],
                "Priority official institution URL differs from location source")
        # Verify only an explicit source URL, never a geographic coordinate or
        # facility-name guess. Official site content not fetched here.
        results.append({
            "water_number": reference["official_number"],
            "water_name_raw": w["official_name_raw"],
            "water_address_raw": w["official_address_raw"],
            "water_floor_raw": w["official_usable_floor_raw"],
            "d_location_id": d["id"],
            "d_location_name_raw": d["name"],
            "d_original_csv_url": raw["URL"],
            "institution_authority_url": reference["institution_authority_url"],
            "city_directory_url": reference["city_directory_url"],
            "documentary_state": "CORROBORATION_LEAD_NOT_INDEPENDENTLY_ACCEPTED",
            "approved_cross_source_pair": False,
            "flood_specific_eligibility": "UNKNOWN",
        })

    old_water = [w for w in water if w["official_name_raw"] == "旧下小岩小学校"]
    current_water = [w for w in water if w["official_name_raw"] == "下小岩小学校"]
    if old_water:
        require(len(old_water) == len(current_water) == 1,
                "Old/current Shimo-Koiwa water rows ambiguous")
        old, current = old_water[0], current_water[0]
        require(old["official_address_raw"] == "南小岩7丁目8番1号" and
                current["official_address_raw"] == "南小岩5丁目5番1号" and
                old["official_usable_floor_raw"] == "大規模水害では使用不可",
                "Old/current school official addresses or conditions changed")
        former = [r for r in records if
                  r.get("name") == "旧下小岩小学校（体育館のみ使用）"]
        active = [r for r in records if r.get("name") == "下小岩小学校"]
        require(len(former) == len(active) == 1,
                "Old/current D schools must be distinguishable")
        f, a = former[0], active[0]
        require(f["id"] != a["id"] and
                (f["latitude"], f["longitude"]) !=
                (a["latitude"], a["longitude"]),
                "Old/current D facility IDs or coordinates collapsed")
        raw_former = [r for r in location_raw_rows
                      if r.get("名称") == f["name"]]
        raw_active = [r for r in location_raw_rows
                      if r.get("名称") == a["name"]]
        require(len(raw_former) == len(raw_active) == 1,
                "Old/current official location rows absent")
        require(raw_former[0]["URL"] == f.get("detail_url") and
                raw_active[0]["URL"] == a.get("detail_url"),
                "Old/current D URLs differ from municipality raw rows")
        results.append({
            "water_number": old["official_number_raw"],
            "water_name_raw": old["official_name_raw"],
            "water_address_raw": old["official_address_raw"],
            "old_water_floor_raw": old["official_usable_floor_raw"],
            "new_water_address_raw": current["official_address_raw"],
            "old_d_location_id": f["id"],
            "new_d_location_id": a["id"],
            "same_school_site_url_in_raw": bool(
                f.get("detail_url") and f["detail_url"] == a.get("detail_url")),
            "shared_school_site_url_is_not_a_facility_identity_key": True,
            "documentary_state": "DISTINCT_ADDRESSES_OLD_SITE_REVIEW_REQUIRED",
            "approved_cross_source_pair": False,
            "flood_specific_eligibility": "UNKNOWN",
        })
    return results

def audit(html: bytes, csv_raw: bytes, export_raw: bytes, ledger_raw: bytes):
    municipality_rows, table_count = water_rows(html)
    source_rows = list(csv.DictReader(io.StringIO(csv_raw.decode("cp932"), newline="")))
    columns = list(source_rows[0]) if source_rows else []
    require(columns == list(LOCATION_HEADER), "Unexpected municipal location CSV columns")
    doc = json.loads(export_raw)
    require(str(doc.get("region", {}).get("code")) == "13123", "Wrong municipality in D export")
    datasets = [d for d in doc.get("datasets", [])
                if d.get("requirement_code") == "shelter_location"]
    require(len(datasets) == 1, "Missing/duplicate D shelter_location dataset")
    records = datasets[0]["records"]
    require(len(source_rows) == len(records), "Municipal CSV versus D row count mismatch")
    by_id = {}
    for line, (raw, d) in enumerate(zip(source_rows, records), start=2):
        require(raw["名称"].strip() == d["name"], f"Source/D name differs at row {line}")
        require(float(raw["緯度"]) == d["latitude"] and
                float(raw["経度"]) == d["longitude"],
                f"Source/D latitude or longitude differs at row {line}")
        material = (f"13123|{d['name']}|{d['latitude']:.7f}|{d['longitude']:.7f}")
        require(d["id"] == "edogawa-" + sha(material.encode())[:16],
                f"Source/D derived ID differs at row {line}")
        require(d["id"] not in by_id, "D source ID duplicate")
        require(d.get("address") is None, "D source has address not present in source CSV")
        require(d.get("supported_disasters") is None, "D inferred hazard from icon URL")
        by_id[d["id"]] = d

    for scenario in doc.get("scenarios", []):
        require(all(x.get("status") == "UNKNOWN"
                    for x in scenario.get("facility_results", [])),
                "This preapproval audit cannot accept Scenario candidate/exclusion")

    a = json.loads(ledger_raw)
    hashes = {sha(html), sha(csv_raw), sha(export_raw)}
    snapshots = a.get("summary", {}).get("raw_source_file_sha256", [])
    if snapshots:
        require(len(snapshots) == 3 and
                {x.get("sha256") for x in snapshots} == hashes,
                "A summary source SHA256 does not match submitted bytes")
    ledger = normalize_a_ledger(a, hashes, columns, by_id)
    require(len(ledger) == len(municipality_rows), "A and municipality row counts differ")

    status_counts = Counter()
    raw_floor_counts = Counter()
    known_name_hints = set()
    exceptions = []
    whitespace_only_phones = 0
    for number, (source, hint) in enumerate(zip(municipality_rows, ledger), start=1):
        for field, source_text in source.items():
            if field == "official_phone_raw" and hint.get(field) != source_text:
                # The previous A display version used BeautifulSoup's space
                # separator for two line-separated official phone numbers.
                squash = lambda v: re.sub(r"\s+", " ", v or "").strip()
                require(squash(hint.get(field)) == squash(source_text),
                        f"Official phone content differs at water row {number}")
                whitespace_only_phones += 1
            else:
                require(hint.get(field) == source_text,
                        f"Official {field} differs at water row {number}")
        require(hint.get("source_url") == WATER_URL, "Municipality URL mismatch")
        require(hint.get("C_independent_verified") is False,
                "A falsely claims C independent verification")
        require(hint.get("D_scenario_status") == "UNCHANGED_UNKNOWN",
                "A attempts unauthorized D classification")
        category = hint.get("candidate_class")
        require(category in HINT_CLASSES, "Unrecognized or approved A candidate status")
        ids = hint.get("candidate_location_ids")
        names = hint.get("candidate_location_names")
        require(isinstance(ids, list) and isinstance(names, list) and
                len(ids) == len(names) and len(ids) == len(set(ids)) and
                len(ids) == hint.get("candidate_count"),
                "A candidate list count / duplication invalid")
        for i, ident in enumerate(ids):
            require(ident in by_id and names[i] == by_id[ident]["name"],
                    f"A candidate ID/name inconsistent at water row {number}")
        if category == "NAME_ALIGNED_HINT":
            require(len(ids) == 1 and
                    hint_name(hint["official_name_raw"]) == hint_name(names[0]),
                    "A marks a nonmatching string as normalized-name hint")
        elif category == "NAME_ABBREVIATION_HINT":
            require(len(ids) == 1 and
                    hint_name(hint["official_name_raw"]) != hint_name(names[0]) and
                    short_name(hint["official_name_raw"]) == short_name(names[0]),
                    "A marks an unsupported abbreviation as matched")
        if category != "MANUAL_REVIEW_REQUIRED":
            require(ids[0] not in known_name_hints,
                    "A reuses the same facility across multiple official rows")
            known_name_hints.add(ids[0])
        else:
            exceptions.append(hint["official_name_raw"])
        status_counts[category] += 1
        raw_floor_counts[hint["official_usable_floor_raw"]] += 1

    return {
        "audit_status": "SOURCE_SNAPSHOT_CONSISTENCY_CHECKED_NOT_FACILITY_IDENTITY_ACCEPTED",
        "region_code": "13123",
        "source_sha256": {
            "city_saved_water_html": sha(html),
            "city_local_location_csv": sha(csv_raw),
            "old_d_region_export": sha(export_raw),
            "a_proposal_ledger": sha(ledger_raw)
        },
        "priority_identity_leads": review_priority_identity_leads(municipality_rows, source_rows, records),
        "water_rows": len(municipality_rows),
        "water_tables": table_count,
        "location_rows": len(source_rows),
        "csv_to_export_rows_rechecked": len(records),
        "unapproved_hints": dict(sorted(status_counts.items())),
        "official_usable_floor_raw": dict(sorted(raw_floor_counts.items())),
        "manual_review_names": exceptions,
        "phone_whitespace_only_ledger_differences": whitespace_only_phones,
        "historical_export_missing_scenarios": "scenarios" not in doc,
        "c_approved_pairs": 0,
        "flood_candidates_or_exclusions_added": 0,
        "not_verified": [
            "Independent retrieval and latest municipal site bytes / version agreement",
            "One-to-one facility identity between separate municipal sources",
            "Municipal water-disaster facility semantics as flood-only designation",
            "Current opening, routes, and safety at time of evacuation",
            "Independently accepted D flood Scenario; this audit changes no status"
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("water-html", "location-csv", "region-export", "a-ledger", "report"):
        parser.add_argument("--" + name, required=True, type=Path)
    paths = parser.parse_args()
    result = audit(paths.water_html.read_bytes(), paths.location_csv.read_bytes(),
                   paths.region_export.read_bytes(), paths.a_ledger.read_bytes())
    paths.report.parent.mkdir(parents=True, exist_ok=True)
    paths.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps({
        "status": result["audit_status"],
        "water_rows": result["water_rows"],
        "hints": result["unapproved_hints"],
        "approved_pairs": result["c_approved_pairs"]
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
