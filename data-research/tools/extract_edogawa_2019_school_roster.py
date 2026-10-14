#!/usr/bin/env python3
"""A evidence extraction of 2019 Edogawa school's *post-event* operational rows.

Never use these rows as historical replay INPUT or as approved facility identity.
Preserves 65 operational groups and 66 occupancy detail rows, including the
separate Komatsugawa 2 night-class record. Requires pinned exact raw PDF SHA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

SOURCE_URL = "https://www.city.edogawa.tokyo.jp/documents/17316/19matome.pdf"
PINNED_PDF_SHA256 = "89fc7de1810685aaf48a5c6fd6f4c79d6888e1ffb3d6314756fa5665d652b380"
REPORT_PAGE_INDEX = 2
EXPECTED_GROUPS = {"elementary": 42, "junior_high": 21, "other": 2}
EXPECTED_DETAIL_ROWS = {"elementary": 42, "junior_high": 22, "other": 2}
EXPECTED_EVACUEES = {"elementary": 19061, "junior_high": 7564, "other": 136}
EXPECTED_STAFF_PRESENT = {"elementary": 397, "junior_high": 192, "other": 12}
EXPECTED_STAFF_ASSIGNED = {"elementary": 512, "junior_high": 261, "other": 16}


class ExtractionError(ValueError):
    pass


FIELDS = {
    "left": {
        "number": (44, 61), "name": (61, 164), "evac": (164, 200),
        "present": (200, 232), "assigned": (232, 253), "percent": (253, 282),
    },
    "right": {
        "number": (300, 315), "name": (315, 426), "evac": (428, 458),
        "present": (458, 485), "assigned": (485, 507), "percent": (507, 535),
    },
}


def text_in_range(line, bounds):
    a, b = bounds
    return " ".join(w[4] for w in sorted(line, key=lambda w: w[0]) if a <= w[0] < b).strip()


def line_groups(words, side, y_min, y_max):
    selected = [w for w in words if (w[0] < 280 if side == "left" else w[0] >= 290)
                and y_min < (w[1] + w[3]) / 2 < y_max]
    groups = []
    for w in sorted(selected, key=lambda w: (w[1] + w[3]) / 2):
        y = (w[1] + w[3]) / 2
        if groups and abs(groups[-1][0] - y) <= 2.5:
            groups[-1][1].append(w)
        else:
            groups.append((y, [w]))
    return [(y, {k: text_in_range(tokens, rng) for k, rng in FIELDS[side].items()})
            for y, tokens in groups]


def parse_detail_lines(words):
    result = {}
    configs = [
        ("elementary", "left", 100, 662),
        ("junior_high", "right", 100, 398),
        ("other", "right", 449, 478),
    ]
    for category, side, lo, hi in configs:
        lines = line_groups(words, side, lo, hi)
        markers = [(int(d["number"]), y) for y, d in lines if d["number"].isdigit()]
        expected_markers = list(range(1, EXPECTED_GROUPS[category] + 1))
        if [number for number, _ in markers] != expected_markers:
            raise ExtractionError(f"{category} numbered operational units inconsistent: {markers}")
        details = []
        for y, d in lines:
            if not d["name"]:
                continue
            if not (d["evac"] and d["present"] and d["assigned"] and d["percent"]):
                raise ExtractionError("missing reported value for named row")
            values = [d["evac"], d["present"], d["assigned"]]
            if not all(re.fullmatch(r"\d[\d,]*", n) for n in values):
                raise ExtractionError("malformed table numeral")
            if not re.fullmatch(r"\d+%", d["percent"]):
                raise ExtractionError("malformed staffing percentage")
            # The report prints row 2's number midway between two detail rows:
            # regular school + night classes. Assign by closest printed marker.
            group_number, diff = min(((number, abs(y - marker_y)) for number, marker_y in markers),
                                     key=lambda item: item[1])
            if diff > 8:
                raise ExtractionError("name row lacks an unambiguous numbered group")
            details.append({
                "category": category, "source_group_number": group_number,
                "printed_name": d["name"],
                "evacuees_reported": int(d["evac"].replace(",", "")),
                "municipal_staff_attended": int(d["present"].replace(",", "")),
                "municipal_staff_total": int(d["assigned"].replace(",", "")),
                "staff_attendance_rate_displayed": int(d["percent"][:-1]),
                "source_page_index": REPORT_PAGE_INDEX,
                "source_y_pt": round(y, 2),
                "normalized_facility_id": None,
                "facility_identity_review_state": "NOT_REVIEWED",
            })
        if len(details) != EXPECTED_DETAIL_ROWS[category]:
            raise ExtractionError(f"{category} detail count changed: {len(details)}")
        result[category] = details
    return result


def extract_report(raw: bytes) -> dict:
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != PINNED_PDF_SHA256:
        raise ExtractionError("original report SHA256 changed; manual source review required")
    try:
        import fitz
    except ImportError as exc:
        raise ExtractionError("PyMuPDF is required for text-coordinate source rows") from exc
    with fitz.open(stream=raw, filetype="pdf") as pdf:
        if len(pdf) <= REPORT_PAGE_INDEX:
            raise ExtractionError("the source table page is missing")
        words = pdf[REPORT_PAGE_INDEX].get_text("words")
        metadata = dict(pdf.metadata)
        page_count = len(pdf)
    grouped = parse_detail_lines(words)
    operational = []
    detail_rows = []
    for category, expected_count in EXPECTED_GROUPS.items():
        group_details = grouped[category]
        by_number = {}
        for row in group_details:
            n = row["source_group_number"]
            by_number.setdefault(n, []).append(row)
        if sorted(by_number) != list(range(1, expected_count + 1)):
            raise ExtractionError("not all numbered operational units were extracted")
        for n, rows in sorted(by_number.items()):
            if len(rows) != (2 if category == "junior_high" and n == 2 else 1):
                raise ExtractionError("unexpected number of detail lines inside operational group")
            group_id = f"{category}:{n:02d}"
            operational.append({
                "source_group_id": group_id, "category": category,
                "printed_group_number": n, "detail_count": len(rows),
                "evacuees_reported": sum(x["evacuees_reported"] for x in rows),
                "facility_id": None, "facility_identity_review_state": "NOT_REVIEWED",
                "is_confirmed_physical_site": False,
            })
            for idx, row in enumerate(rows, 1):
                row["source_group_id"] = group_id
                row["source_detail_id"] = f"{group_id}:{idx}"
                detail_rows.append(row)
    group_counts = {name: sum(g["category"] == name for g in operational)
                    for name in EXPECTED_GROUPS}
    for category in EXPECTED_GROUPS:
        if group_counts[category] != EXPECTED_GROUPS[category]:
            raise ExtractionError("category group count differs from printed report")
        if sum(x["evacuees_reported"] for x in grouped[category]) != EXPECTED_EVACUEES[category]:
            raise ExtractionError("category reported evacuees subtotal differs")
        if sum(x["municipal_staff_attended"] for x in grouped[category]) != EXPECTED_STAFF_PRESENT[category]:
            raise ExtractionError("category attendance subtotal differs")
        if sum(x["municipal_staff_total"] for x in grouped[category]) != EXPECTED_STAFF_ASSIGNED[category]:
            raise ExtractionError("category assigned staffing subtotal differs")
    if len(operational) != 65 or len(detail_rows) != 66:
        raise ExtractionError("expected 65 numbered groups with 66 detail entries")
    if sum(x["evacuees_reported"] for x in operational) != 26761:
        raise ExtractionError("overall evacuee total mismatch")
    return {
        "schema_id": "hinanex.a.edogawa_2019_school_operational_roster.v0.1",
        "case_id": "2019-typhoon19-edogawa",
        "source_url": SOURCE_URL, "source_raw_sha256": actual_sha,
        "pdf_page_count": page_count, "pdf_metadata_creation_date": metadata.get("creationDate"),
        "source_page_index": REPORT_PAGE_INDEX,
        "evidence_role": "POST_EVENT_TRUTH_CANDIDATE_ONLY",
        "source_published_at_2019_event_time": False,
        "asof_input_approved": False, "facility_id_pairs_approved": 0,
        "reporting_unit": "source_numbered_operational_group_NOT_PHYSICAL_SITE",
        "operational_groups_total": 65, "detail_rows_total": 66,
        "reported_evacuations_total": 26761,
        "note": "One numbered junior-high group has two occupancy detail rows (regular and night class).",
        "operational_groups": operational, "detail_rows": detail_rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pdf", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise ExtractionError("refusing to overwrite extracted evidence")
        output = extract_report(args.source_pdf.read_bytes())
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print("EDOGAWA_2019_ROSTER_FAILED: "+str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"status": "A_SOURCE_ROWS_EXTRACTED__C_UNREVIEWED",
                      "source_sha256": output["source_raw_sha256"],
                      "groups": 65, "details": 66, "reported_evacuations": 26761,
                      "asof_input_approved": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
