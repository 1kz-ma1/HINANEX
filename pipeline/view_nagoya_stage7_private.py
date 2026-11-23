"""Render a PRIVATE, local-only HTML reader for Stage-7 Nagoya manual review.

No HTTP, JavaScript, analytics, map tiles, remote assets, submission forms or
data promotion. Every facility string is HTML-escaped; only fixed official
municipal source links are included. This file must remain gitignored.
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
from collections import Counter
from pathlib import Path

from refine_nagoya_gsi_stage7 import ADDED_FIELDS, RANKS, STATES
from compare_nagoya_gsi_offline import PRIVATE_COMPARISON_FIELDS
from triage_nagoya_gsi_stage6 import EXTRA

OFFICIAL_PORTAL = "https://www.city.nagoya.jp/bousaiportal/hinan/1013390/1013492.html"
OFFICIAL_CHIKUSA = "https://www.city.nagoya.jp/_res/projects/default_project/_page_/001/013/492/okunai01chikusa0809.pdf"
COLUMNS = (*PRIVATE_COMPARISON_FIELDS, *EXTRA, *ADDED_FIELDS)

# Stage-7 files created before the header fix contain a second copy of
# "independent_site_position_approved" just before "manual_review_required".
# Keep historical PRIVATE outputs immutable and tolerate ONLY this known
# duplicate after verifying that the two values are equal, row by row.
LEGACY_DUPLICATE_FIELD = "independent_site_position_approved"
LEGACY_DUPLICATE_INDEX = COLUMNS.index("manual_review_required")
LEGACY_COLUMNS = (
    *COLUMNS[:LEGACY_DUPLICATE_INDEX],
    LEGACY_DUPLICATE_FIELD,
    *COLUMNS[LEGACY_DUPLICATE_INDEX:],
)


def read_stage7_private(path: Path) -> list[dict]:
    """Read canonical or precisely-known legacy Stage-7 CSV, fail closed."""
    raw = path.read_bytes()
    try:
        payload = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Stage-7 PRIVATE CSV must use UTF-8") from exc
    reader = csv.reader(io.StringIO(payload, newline=""))
    header = next(reader, None)
    if header == list(COLUMNS):
        legacy = False
    elif header == list(LEGACY_COLUMNS):
        legacy = True
    else:
        raise ValueError("Unexpected Stage-7 PRIVATE columns")
    first_approval_index = COLUMNS.index(LEGACY_DUPLICATE_FIELD)
    result = []
    for values in reader:
        if len(values) != len(header):
            raise ValueError("Malformed Stage-7 PRIVATE CSV row")
        if legacy and values[first_approval_index] != values[LEGACY_DUPLICATE_INDEX]:
            raise ValueError("Conflicting duplicate approval fields in legacy CSV")
        result.append(dict(zip(header, values)))
    return result


STYLE = """
:root{color-scheme:light;font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif}
body{background:#f5f6f7;color:#202428;margin:0 auto;padding:20px;max-width:1080px}
h1{font-size:1.55rem}h2{font-size:1.2rem;margin:0 0 8px}
p,li{line-height:1.55}a{color:#1d5e88}
nav{background:white;border:1px solid #d2d7dc;padding:12px 16px;border-radius:10px}
nav a{margin-right:20px}
article{background:white;border:1px solid #d2d7dc;border-radius:10px;padding:18px;margin:16px 0}
.label{font-size:.78rem;color:#566270;font-weight:600;display:block;margin-bottom:3px}
.value{word-break:break-word;white-space:pre-wrap;line-height:1.5;margin:4px 0 13px}
.review{background:#f1f3f5;padding:10px;border-left:3px solid #84919c}
.p0{border-left:5px solid #9b4e35}.p1{border-left:5px solid #b48d33}
.p2{border-left:5px solid #497968}
.warning{border:1px solid #ba726c;background:#fff7f5;border-radius:8px;padding:12px}
dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));column-gap:20px;margin:8px 0}
dt{font-size:.78rem;color:#566270}dd{margin:4px 0 12px;overflow-wrap:anywhere}
small{color:#566270}code{overflow-wrap:anywhere}
"""


def esc(value: object) -> str:
    return html.escape(str(value) if value is not None else "", quote=True)


def validate(rows: list[dict], summary: dict) -> None:
    if (summary.get("report_kind") !=
            "NAGOYA_STAGE7_VERSIONED_REFERENCE_AND_RENOVATION_REFINEMENT"
            or summary.get("approved_for_map") is not False
            or summary.get("data_promotion_authorized") is not False
            or summary.get("site_position_independently_verified") is not False
            or summary.get("official_facility_positions_accepted") != 0
            or summary.get("all_review_status_not_reviewed") is not True
            or summary.get("all_raw_gsi_reference_points_preserved") is not True
            or summary.get("historical_stage5_stage6_unchanged") is not True
            or summary.get("source_end_date_does_not_auto_reopen") is not True
            or summary.get("review_rows_total") != len(rows)
            or len(rows) != len({r.get("pilot_record_id") for r in rows})):
        raise ValueError("Invalid Stage-7 summary or review status")
    if not rows or any(set(row) != set(COLUMNS) for row in rows):
        raise ValueError("Stage-7 private CSV schema incompatible")
    if any(
        row["stage7_priority"] not in RANKS
        or row["stage7_classification"] not in STATES
        or row["stage7_review_status"] != "NOT_REVIEWED"
        or row["manual_review_required"] != "YES"
        or row["independent_site_position_approved"] != "NO"
        or row["facility_use_status_verified"] != "NO"
        or row["facility_reopening_verified"] != "NO"
        or row["approval_gate"] != "BLOCKED_PENDING_MANUAL_SITE_VERIFICATION"
        for row in rows
    ):
        raise ValueError("Stage-7 row approval gate changed")
    counts = Counter(row["stage7_priority"] for row in rows)
    if {key: counts[key] for key in RANKS} != summary.get("refined_priority_counts"):
        raise ValueError("Stage-7 priority counts changed")
    classes = Counter(row["stage7_classification"] for row in rows)
    if {key: classes[key] for key in STATES} != summary.get("refined_classifications"):
        raise ValueError("Stage-7 classification counts changed")


def field(label: str, value: object) -> str:
    return "<div><dt>" + esc(label) + "</dt><dd>" + esc(value) + "</dd></div>"


def render(rows: list[dict], summary: dict) -> str:
    validate(rows, summary)
    ordered = sorted(rows, key=lambda r: (
        RANKS.index(r["stage7_priority"]), r["facility_name"], r["pilot_record_id"],
    ))
    counts = Counter(r["stage7_priority"] for r in ordered)
    parts = [
        "<!doctype html><html lang='ja'><head><meta charset='utf-8'>",
        "<meta name='referrer' content='no-referrer'>",
        "<meta http-equiv='Content-Security-Policy' "
        "content=\"default-src 'none'; style-src 'unsafe-inline'; "
        "img-src 'none'; form-action 'none'; base-uri 'none'\">",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>HINANEX · PRIVATE Nagoya review</title>",
        "<style>", STYLE, "</style></head><body>",
        "<h1>HINANEX · 名古屋 施設位置確認（Macローカル専用）</h1>",
        "<div class='warning'><strong>全施設が未承認です。</strong>"
        "ABR/GSI参照点は施設の敷地・建物・入口や安全性を保証しません。"
        "工事終了予定日を過ぎても自動的に使用可能とは判定しません。"
        "このHTMLと元CSVは共有・GitHubコミットしないでください。</div>",
        "<p>読取専用の確認画面です。記録はローカルCSVに残し、"
        "GISやRegionExportへは反映しません。</p>",
        "<nav><strong>優先度別：</strong>",
    ]
    for level, caption in zip(RANKS, ("P0 · 運用/同一性", "P1 · 距離/地番", "P2 · 位置確認")):
        parts.append("<a href='#" + esc(level) + "'>" + esc(caption) +
                     "（" + str(counts[level]) + "件）</a>")
    parts.append("<p>公式資料：<a rel='noreferrer noopener' target='_blank' href='" +
                 OFFICIAL_PORTAL + "'>名古屋市・指定施設一覧</a> | " +
                 "<a rel='noreferrer noopener' target='_blank' href='" +
                 OFFICIAL_CHIKUSA + "'>千種区屋内施設一覧（2026-09-01時点）</a>"
                 "</p></nav>")
    for level in RANKS:
        parts.append("<section id='" + esc(level) + "'><h2>" + esc(level) +
                     "（" + str(counts[level]) + "件）</h2>")
        for idx, row in enumerate(r for r in ordered if r["stage7_priority"] == level):
            parts.append("<article class='" +
                         ("p0" if level == RANKS[0] else
                          "p1" if level == RANKS[1] else "p2") +
                         "'><h2>" + esc(row["facility_name"]) + "</h2><dl>")
            for label, key in (
                ("住所（元資料）", "official_listed_address"),
                ("照合分類", "stage7_classification"),
                ("要確認理由", "stage6_risk_flags"),
                ("ABRとGSI参照点の距離（m）", "gsi_abr_distance_meters"),
                ("元の施設登録種別", "gsi_registered_facility_type"),
                ("工事による使用不可・資料上の開始日", "source_renovation_start"),
                ("工事による使用不可・資料上の終了予定日", "source_renovation_end"),
                ("元の使用制限注記", "source_notice_verbatim_PRIVATE"),
                ("参照点の正式承認", "independent_site_position_approved"),
            ):
                if row.get(key):
                    parts.append(field(label, row[key]))
            parts.append("</dl><div class='review'><strong>人手確認すること</strong>"
                         "<p>①最新の自治体資料の日付と指定区分　"
                         "②施設名・住所・運用制限（P0）　"
                         "③公式施設図で敷地・建物・入口と候補点の関係（P1/P2）　"
                         "④出典URLと独立確認の限界</p>"
                         "<small>未確認。ここでの確認だけでは、施設を避難先として公開できません。</small>"
                         "</div></article>")
        parts.append("</section>")
    parts.append("</body></html>")
    return "".join(parts)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot-dir", required=True, type=Path)
    args = p.parse_args()
    root = (Path(__file__).resolve().parent / "data/geocoding_pilot").resolve()
    folder = args.pilot_dir.resolve()
    if folder != root and root not in folder.parents:
        p.error("Only a gitignored pilot directory is allowed")
    output = folder / "gsi_stage7_review_PRIVATE.html"
    if output.exists():
        p.error("PRIVATE HTML already exists; refuse to overwrite")
    try:
        rows = read_stage7_private(folder / "gsi_stage7_refined_PRIVATE.csv")
        summary = json.loads((folder / "gsi_stage7_refined_aggregate.json").read_text("utf-8"))
        page = render(rows, summary)
        with output.open("x", encoding="utf-8") as handle:
            handle.write(page)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.exit(1, "Local review HTML aborted [" + type(exc).__name__ +
               "]; no data promoted.\n")
    print(json.dumps({
        "report_kind": "NAGOYA_PRIVATE_STAGE7_REVIEW_HTML_LOCAL_ONLY",
        "private_review_rows": len(rows),
        "priority_counts": summary["refined_priority_counts"],
        "html_created": True,
        "approved_for_map": False,
        "official_facility_positions_accepted": 0,
        "data_promotion_authorized": False,
        "private_file_must_not_be_uploaded": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
