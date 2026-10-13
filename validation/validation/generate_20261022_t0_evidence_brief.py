#!/usr/bin/env python3
"""2026-10-22 C-only evidence slide from independently checked raw-source reports.

Offline output for a short 7-minute HINANEX presentation, NOT the B app,
not life-safety information, not historical predictive evaluation or #89 DoD.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import sys
import zipfile

ARTIFACTS = {
    "school": ("C_edogawa_2019_school_roster_UNAPPROVED.json",
               "hinanex.c.edogawa_2019_school_roster_source_audit.v0.1",
               "89fc7de1810685aaf48a5c6fd6f4c79d6888e1ffb3d6314756fa5665d652b380"),
    "campus": ("C_2019_campus_vs_shelter_UNAPPROVED.json",
               "hinanex.c.edogawa_2019_school_campus_source_audit.v0.1",
               "542d615df1df07139c37eab45d65e0ea3e4ac87783e868471f79746702a673df"),
    "newsletter": ("C_edogawa_2018_night-school_UNAPPROVED.json",
                   "hinanex.c.2018_edogawa_school_identity_gate.v0.1",
                   "c44db027ac7d75444a5684e0a1c37973c6c6dc50fbe9974374c566713c219e33"),
    "cross": ("C_2019_actual_shelter_building_LINK_BLOCKED.json",
              "hinanex.c.2019_event_shelter_building_link_gate.v0.1", None),
}
OFFICIAL = {
    "school": "https://www.city.edogawa.tokyo.jp/documents/17316/19matome.pdf",
    "campus": "https://www.city.edogawa.tokyo.jp/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/komanichu.html",
    "newsletter": "https://www.city.edogawa.tokyo.jp/documents/26598/300820.pdf",
}
RUNS = {
    "school": "https://github.com/1kz-ma1/HINANEX/actions/runs/38344307696",
    "campus": "https://github.com/1kz-ma1/HINANEX/actions/runs/38350260260",
    "newsletter": "https://github.com/1kz-ma1/HINANEX/actions/runs/38349472925",
    "cross": "https://github.com/1kz-ma1/HINANEX/actions/runs/38351185440",
}
MAX_JSON = 1024 * 1024


class EvidenceError(ValueError):
    pass


def check(value, expected, reason):
    if value != expected:
        raise EvidenceError(reason + ": expected " + repr(expected))
    return True


def read_c_report(archive_path: Path, key: str) -> dict:
    member, schema, sha = ARTIFACTS[key]
    with zipfile.ZipFile(archive_path) as z:
        files = z.namelist()
        if files != [member]:
            raise EvidenceError("missing, duplicate or unexpected C artifact members: " + key)
        metadata = z.getinfo(member)
        if metadata.file_size <= 10 or metadata.file_size > MAX_JSON:
            raise EvidenceError("C report payload size outside limit: " + key)
        obj = json.loads(z.read(member))
    check(obj.get("schema_id"), schema, key + " schema")
    if sha is not None:
        digest = obj.get("raw_sha256") if key == "campus" else obj.get("source_sha256")
        check(digest, sha, key + " raw source identity")
    return obj


def compose(school: dict, campus: dict, newsletter: dict, cross: dict) -> dict:
    check(school.get("status"), "C_SOURCE_TO_OUTPUT_CONFIRMED__POST_EVENT_ONLY__NO_ASOF_APPROVAL",
          "school T0 status")
    for k,n in (("groups",65),("detail_rows",66),("evacuees",26761),
                ("physical_facility_pairs_approved",0),
                ("historical_asof_input_approved",False),
                ("prediction_accuracy_evaluated",False),
                ("school_middle_night_detail_verified",True)):
        check(school.get(k),n,"source truth "+k)
    check(campus.get("status"), "C_PAGE_CAMPUS_CLAIMS_VERIFIED__SHELTER_SITE_UNAPPROVED",
          "campus raw C result")
    for k,v in (("source_school_normal_campus_district","小松川2丁目"),
                ("source_school_night_campus_district","平井3丁目"),
                ("source_normal_campus_street_address","小松川2丁目10番2号"),
                ("source_night_campus_street_address",None),
                ("actual_shelter_used_building_for_205",None),
                ("actual_shelter_used_building_for_11",None),
                ("historical_page_revision_asof_approved",False),
                ("shelter_identity_pairs_approved",0)):
        check(campus.get(k),v,"school != event shelter "+k)
    check(newsletter.get("status"),
          "C_2018_SCHOOL_LABELS_AND_ORIGINAL_BYTES_VERIFIED__IDENTITY_NOT_APPROVED",
          "newsletter T0 result")
    for k,v in (("day_school_label_present",True),
                ("night_class_label_present_separately",True),
                ("school_night_same_physical_site_2019",None),
                ("physical_site_pairs_approved",0),
                ("historical_asof_input_approved",False)):
        check(newsletter.get(k),v,"2018 names != site "+k)
    check(cross.get("status"),
          "BLOCKED_ACTUAL_EVENT_SHELTER_BUILDING_LINK__NEEDS_OFFICIAL_OPERATION_LOG",
          "cross-report expected BLOCKED")
    for k,v in (("c_source_reports_cross_checked",3),
                ("source_operational_groups",1),
                ("distinct_source_reporting_rows",2),
                ("identified_physical_shelter_buildings",0),
                ("approved_occupancy_to_building_pairs",0),
                ("historical_asof_input_approvals",0),
                ("predictive_match_mismatch_cases",0),
                ("prediction_accuracy_evaluated",False)):
        check(cross.get(k),v,"cross-report "+k)
    details = cross.get("decisions")
    if not isinstance(details,list) or len(details)!=2:
        raise EvidenceError("205/11 two details not represented separately")
    if sorted((r.get("occupancy_detail_id"),r.get("reported_persons"))
              for r in details) != [("night_11",11),("ordinary_205",205)]:
        raise EvidenceError("wrong detailed 205/11 source rows")
    if any(r.get("actual_2019_shelter_building_id") is not None or
           r.get("status") != "BLOCKED_NO_BUILDING_LEVEL_EVENT_SOURCE" for r in details):
        raise EvidenceError("invented source row physical site or verdict")
    if set(cross.get("input_manifest_sha256",{})) != {
        "a_ledger","c_campus_report","c_newsletter_report","c_ops_report"
    }:
        raise EvidenceError("cross-report source audit lineage digests missing")
    if any(not isinstance(d,str) or len(d)!=64 for d in cross["input_manifest_sha256"].values()):
        raise EvidenceError("invalid digest in cross-report source lineage")
    return {
        "schema_id": "hinanex.c.midterm_t0_evidence_walkthrough.v0.1",
        "purpose": "2026-10-22 7-minute midterm; historical T0 evidence segment only",
        "foundation_89_acceptance": "NOT_SIGNED_OFF_BY_THIS_REPORT",
        "historical_t0_original_source_checks": "PASSED_IN_PRIOR_AUTOMATED_C_CHECKS__HUMAN_ACCEPTANCE_PENDING",
        "school_operational_groups": 65,
        "school_occupancy_detail_rows": 66,
        "reported_school_evacuees": 26761,
        "junior_high_number_2": {"regular":205,"night":11,
                                  "reporting_group_count":1,"detail_count":2},
        "school_campus_2019_districts": {
            "regular": "小松川2丁目", "night": "平井3丁目",
            "regular_school_street_address": "小松川2丁目10番2号",
            "night_school_street_address": None,
        },
        "real_event_shelter_building_match":"BLOCKED__NOT_EVALUABLE",
        "approved_actual_building_pairs":0,
        "approved_historical_prediction_inputs":0,
        "t1_opening_prediction_accuracy":"NOT_EVALUABLE",
        "t2_hazard_prediction_accuracy":"NOT_RUN",
        "prediction_numerator":None,
        "prediction_denominator":None,
        "school_diary_operational_leads_not_source_audited":True,
        "sources":[
            {"role":k,"official_url":OFFICIAL[k],"C_machine_run_url":RUNS[k],
             "official_raw_sha256":ARTIFACTS[k][2]} for k in ("school","campus","newsletter")
        ],
        "cross_report_run": RUNS["cross"],
        "safe_demo_message": "学校運営場所と災害当日の避難先建物を混同せず、未確認の予測成績を表示しない",
    }


def markdown(report: dict) -> str:
    return """# HINANEX 10/22 — Cが原本へ戻って検証できること（約60秒）

**実証済み範囲: T0の機械的な原本・抽出照合。T1/T2の予測精度は未検証。**

| 見せる順番 | 実際の証拠 | 判定と限界 |
|---|---|---|
| ① 原本・集計 | 江戸川区の事後報告：**65運用グループ／66明細／26,761人** | 公式原本とC独立照合済み。物理的な65棟を意味しない |
| ② 欠損に見える違い | 小松川第二中学校：**通常205人・夜間11人** | 同じ運用番号2の**2明細**。人数を落とさない・建物を同一視しない |
| ③ 当時の施設配置 | 通常課程の校舎＝小松川2丁目、夜間学級＝平井3丁目 | 校舎所在地の資料であり、205/11人が当日避難した建物の証拠ではない |
| ④ 判断保留 | **当日使用した建物ID：0件承認** | 予測精度T1 **NOT_EVALUABLE**、T2 **NOT_RUN** |

**根拠**: [学校避難所報告](""" + OFFICIAL["school"] + """) ／ [2019年3月表示の改築資料](""" + OFFICIAL["campus"] + """) ／ [2018年広報](""" + OFFICIAL["newsletter"] + """)。

**再現可能なC独立監査**: [学校記録]("""+RUNS["school"]+""") ／ [校舎資料]("""+RUNS["campus"]+""") ／ [広報]("""+RUNS["newsletter"]+""") ／ [横断の保留判定]("""+RUNS["cross"]+""")。

> **発表で必ず伝えること**：公開済みの資料でも正しい時点の原本か確認し、名前や番号が一致しても施設を無断で結び付けません。避難経路・安全な施設の推薦はまだ行いません。

このレポートは #89 で要求される3地域D/B/E実ブラウザ受入・防災サービス安全性を代替しません。新規学校日記は原本未固定のため、このC済みの件数に含めません。
"""


def html_document(report: dict) -> str:
    # C-owned OFFLINE EVIDENCE SHEET, not a production B UI.
    messages = [
        ("01", "原本照合 / T0", "65グループ・66明細", "避難者数 26,761人。出典の行までC独立確認"),
        ("02", "集計の違いを検出", "205人 + 夜間11人", "同じ報告番号に2明細。1建物と断定しない"),
        ("03", "学校と避難所を区別", "小松川2丁目 ／ 平井3丁目", "学校運営場所は分かる。当日避難した建物は未確認"),
        ("04", "未確認なら保留", "建物対応 0件承認", "T1予測精度 未評価 / T2 未実行"),
    ]
    parts=[]
    for no,heading,value,desc in messages:
        parts.append('<article><span class="n">'+escape(no)+'</span><div><small>'+
                     escape(heading)+'</small><h2>'+escape(value)+'</h2><p>'+
                     escape(desc)+'</p></div></article>')
    links=' '.join('<a href="'+escape(RUNS[k],quote=True)+'">'+escape(k)+'</a>'
                   for k in ("school","campus","newsletter","cross"))
    return """<!doctype html><html lang="ja"><meta charset="utf-8">
<title>HINANEX 10/22 — C original evidence</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{color-scheme:light;font-family:system-ui,"Noto Sans JP",sans-serif;color:#202a31}
*{box-sizing:border-box}body{margin:0;background:#f4f6f7}
main{max-width:1040px;margin:auto;padding:36px 30px 50px}
h1{font-size:clamp(26px,4vw,43px);line-height:1.2;margin:8px 0 12px}
.lead{color:#475569;font-size:17px;line-height:1.65;margin:0 0 30px}
article{display:flex;gap:24px;align-items:center;background:white;padding:23px 26px;
border-radius:14px;margin:13px 0;border:1px solid #e5e9ed}
.n{font-size:30px;color:#8c9aa5;font-variant-numeric:tabular-nums;font-weight:650}
small{font-size:14px;font-weight:700;color:#546775}
h2{margin:4px 0;font-size:clamp(22px,3vw,31px)}
p{margin:4px 0;font-size:15px;line-height:1.55;color:#3d4a53}
footer{font-size:13px;line-height:1.7;margin-top:24px;color:#55636f}
a{color:#225c85}a+a{margin-left:16px}
</style>
<main><div>HINANEX / 検証証跡 / 2026.10.22</div>
<h1>分からない場所を、<br>安全な場所として扱わない。</h1>
<p class="lead">公式原本 → 独立検証 → 出典付き表示。<strong>予測精度の実証ではありません。</strong></p>
""" + "\n".join(parts) + """
<footer><strong>境界：</strong>これらは2019年の施設安全判定・避難勧告・開設予測ではありません。
<br>独立したC検証実行記録：""" + links + """
<br>10/22基礎受入 #89、実ブラウザ・3地域D契約の最終検証は別途必要。</footer>
</main></html>
"""


def produce(paths: dict, out_dir: Path):
    if out_dir.exists() and any(out_dir.iterdir()):
        raise EvidenceError("refuse to overwrite existing evidence deliverables")
    reports={key:read_c_report(paths[key],key) for key in ARTIFACTS}
    manifest=compose(reports["school"],reports["campus"],reports["newsletter"],reports["cross"])
    out_dir.mkdir(parents=True,exist_ok=True)
    (out_dir/"C_20261022_evidence_manifest.json").write_text(
        json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out_dir/"C_20261022_60sec_guide.md").write_text(markdown(manifest),encoding="utf-8")
    (out_dir/"C_20261022_offline_evidence.html").write_text(html_document(manifest),encoding="utf-8")
    return manifest


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ARTIFACTS:
        p.add_argument("--"+key+"-zip",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        out=produce({k:getattr(a,k+"_zip") for k in ARTIFACTS},a.out_dir)
        print(json.dumps({"status":out["historical_t0_original_source_checks"],
                          "building_links":out["approved_actual_building_pairs"],
                          "T1":out["t1_opening_prediction_accuracy"],
                          "T2":out["t2_hazard_prediction_accuracy"]},ensure_ascii=False))
        return 0
    except (EvidenceError,OSError,ValueError,TypeError,zipfile.BadZipFile) as exc:
        print("C_20261022_EVIDENCE_DEMO_FAILED: "+str(exc),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
