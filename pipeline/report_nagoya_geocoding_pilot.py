"""Audit a local Nagoya ABR pilot and prepare a human-only site review worksheet.

Does not infer, approve, promote or publish coordinates. No network traffic.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def audit(manifest: dict, resolution: dict) -> tuple[dict, list[dict]]:
    if manifest.get("pilot_version") != 1 or resolution.get("pilot_version") != 1:
        raise ValueError("Invalid pilot version")
    if manifest.get("region_code") != "23100":
        raise ValueError("Not a Nagoya pilot")
    original_hash = manifest.get("source_dataset_sha256")
    if not isinstance(original_hash, str) or not original_hash:
        raise ValueError("Missing source dataset hash")
    if original_hash != resolution.get("source_dataset_sha256"):
        raise ValueError("Manifest/result source hash mismatch")
    if resolution.get("approved_for_map") is not False or resolution.get("data_promotion_authorized") is not False:
        raise ValueError("Report may only process entirely unapproved experiments")
    selected, rows = manifest.get("selected"), resolution.get("results")
    if not isinstance(selected, list) or not isinstance(rows, list) or not 1 <= len(selected) <= 50:
        raise ValueError("Missing/bad pilot rows")
    if len(selected) != len(rows) or resolution.get("count") != len(rows):
        raise ValueError("Result rows do not match selection count")
    indexes = {}
    for candidate in selected:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("record_id"), str):
            raise ValueError("Malformed manifest candidate")
        identifier = candidate["record_id"]
        if identifier in indexes:
            raise ValueError("Duplicate manifest ID")
        indexes[identifier] = candidate
    statuses = Counter()
    reasons = Counter()
    levels = Counter()
    wards = Counter()
    worksheet = []
    seen = set()
    for item in rows:
        if not isinstance(item, dict) or item.get("record_id") not in indexes:
            raise ValueError("Unexpected geocode result record")
        source = indexes[item["record_id"]]
        rid = item["record_id"]
        if rid in seen:
            raise ValueError("Duplicate resolved ID")
        seen.add(rid)
        for field in ("name", "ward", "source_address", "query_address"):
            if source.get(field) != item.get(field):
                raise ValueError("Result lost source identity: " + field)
        if item.get("approved_for_map") is not False:
            raise ValueError("Approved map coordinates forbidden in the pilot")
        status = item.get("status")
        if status not in ("UNVERIFIED_CANDIDATE", "NEEDS_REVIEW", "UNRESOLVED", "PROVIDER_ERROR"):
            raise ValueError("Unexpected status")
        if status in ("UNVERIFIED_CANDIDATE", "NEEDS_REVIEW"):
            geometry = item.get("derived_geometry")
            if not isinstance(geometry, dict) or "latitude" not in geometry or "longitude" not in geometry:
                raise ValueError("Expected tentative geometry")
        else:
            geometry = {}
        statuses[status] += 1
        reasons[str(item.get("reason", "unknown"))] += 1
        wards[item["ward"]] += 1
        if item.get("coordinates_level"):
            levels[str(item["coordinates_level"])] += 1
        worksheet.append({
            "record_id": rid, "name": item["name"], "ward": item["ward"],
            "official_source_address": item["source_address"],
            "query_address": item["query_address"],
            "pilot_status": status, "pilot_reason": item.get("reason", ""),
            "coordinate_level": item.get("coordinates_level", ""),
            "candidate_latitude": geometry.get("latitude", ""),
            "candidate_longitude": geometry.get("longitude", ""),
            "reference_source": item.get("coordinate_source", ""),
            "provider_response_sha256": item.get("provider_response_sha256", ""),
            "human_review": "NOT_REVIEWED",
            "independent_official_facility_source_url": "",
            "site_identity_confirmed": "",
            "position_accuracy_checked": "",
            "reviewer_note": "",
        })
    count = len(rows)
    eligible = statuses["UNVERIFIED_CANDIDATE"]
    return {
        "report_kind": "PILOT_PRELIMINARY_GEOCODE_DIAGNOSTIC_NOT_SITE_ACCEPTANCE",
        "source_dataset_sha256": original_hash,
        "provider": resolution.get("provider"),
        "provider_version": resolution.get("provider_version"),
        "provider_db_version": resolution.get("provider_db_version"),
        "sample_total": count,
        "unverified_candidate_count": eligible,
        "unverified_candidate_rate_percent": round(100 * eligible / count, 2),
        "requires_review_count": statuses["NEEDS_REVIEW"],
        "unresolved_count": statuses["UNRESOLVED"],
        "provider_error_count": statuses["PROVIDER_ERROR"],
        "statuses": dict(statuses), "reasons": dict(reasons),
        "coordinate_levels": dict(levels), "ward_sample_counts": dict(wards),
        "official_site_coordinates_accepted": 0,
        "site_accuracy_independently_verified": False,
        "approved_for_map": False,
        "data_promotion_authorized": False,
        "route_or_disaster_safety_verified": False,
    }, worksheet


def presentation_summary(summary: dict) -> str:
    """Address-candidate diagnostics for a presentation; not site acceptance."""
    total = summary["sample_total"]
    statuses = summary["statuses"]
    lines = [
        "# 名古屋市：住所から座標候補を生成する試験の結果",
        "",
        "**実験結果／施設位置の独立検証は未了。安全な避難先の判定ではありません。**",
        "",
        f"- 試験対象：{total}施設（名古屋市屋内施設データから抽出）",
        f"- 座標候補（未承認）：{summary['unverified_candidate_count']}/{total}"
        f"（{summary['unverified_candidate_rate_percent']:.2f}%）",
        f"- 同一点など要確認：{summary['requires_review_count']}/{total}",
        f"- 未解決：{summary['unresolved_count']}/{total}",
        f"- プロバイダ側エラー：{summary['provider_error_count']}/{total}",
        "- 公式施設位置として確認済み：**0件（独立照合は別工程）**",
        "",
        "## 判定別の内訳",
        "",
        "| 判定 | 件数 |",
        "| --- | ---: |",
    ]
    for status in ("UNVERIFIED_CANDIDATE", "NEEDS_REVIEW", "UNRESOLVED", "PROVIDER_ERROR"):
        lines.append(f"| {status} | {statuses.get(status, 0)} |")
    lines.extend([
        "",
        "## 区ごとの抽出件数",
        "",
        "| 行政区 | 件数 |",
        "| --- | ---: |",
    ])
    for ward, count in sorted(summary["ward_sample_counts"].items()):
        clean_ward = ward.replace("|", "").replace("\n", "")
        lines.append(f"| {clean_ward} | {count} |")
    lines.extend([
        "",
        "## 解釈と制約",
        "",
        "- 本集計はローカルABRの住所参照結果であり、建物・施設・入口の正確な位置を保証しない。",
        "- 座標候補の取得率を位置精度・施設同一性の検証完了率と混同しない。",
        "- 災害適合性、避難先開設、経路安全性は未評価。",
        "- 既存のRegionExport、元の座標、GIS、本番には反映しない。",
        "- 原本版・ABRデータ版と独立した人間の確認が必要。",
        "",
    ])
    return "\n".join(lines)


def create_report(directory: Path) -> dict:
    root = (Path(__file__).resolve().parent / "data" / "geocoding_pilot").resolve()
    directory = directory.resolve()
    if directory != root and root not in directory.parents:
        raise ValueError("Must report in gitignored pilot data directory")
    manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
    resolution = json.loads((directory / "resolution.json").read_text("utf-8"))
    summary, worksheet = audit(manifest, resolution)
    # Fail before any output if a previous report already exists.
    paths = [directory / name for name in
             ("summary.json", "human_review.csv", "presentation_summary.md")]
    if any(path.exists() for path in paths):
        raise FileExistsError("Existing report detected; use a new output directory")
    with (directory / "summary.json").open("x", encoding="utf-8") as output:
        json.dump(summary, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
    with (directory / "human_review.csv").open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(worksheet[0].keys()))
        writer.writeheader()
        writer.writerows(worksheet)
    with (directory / "presentation_summary.md").open("x", encoding="utf-8") as output:
        output.write(presentation_summary(summary))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(create_report(args.pilot_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
