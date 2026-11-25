# C証拠パケット → 証拠単位のレビュー作業票 v0.1

**2026-11-16 / C-only / read-only / SYNTHETIC TESTED / NOT AN APPROVAL CONTRACT**

## 目的
[PR #403](https://github.com/1kz-ma1/HINANEX/pull/403)でmainに追加された`preflight_facility_evidence_packet.py`は、原本SHA・施設同一性・災害記号の意味・資料利用条件について、提出された**参照メタデータの欠落や矛盾**を理由コードで表す。本PRはその結果を機械的に**証拠収集・照合・人間レビューの作業票**へ変換する。従来のC preflight判定やDのS1-P0/P1/P2を変更しない。

背景となる人間の未承認事項:
- [#134](https://github.com/1kz-ma1/HINANEX/issues/134): 異なる資料の施設・実際の建物の同一性。名前/近接/学校の運用グループは同一建物の証明にならない。
- [#48](https://github.com/1kz-ma1/HINANEX/issues/48): 新潟ODSの`災害種別_洪水`などの**該当資料に適用される正式な記号意味**。地図の別凡例を元CSVの独立証明として使わない。
- [#366](https://github.com/1kz-ma1/HINANEX/issues/366): 江戸川区F02の**当該CSVの版/範囲、第三者権利や例外、帰属表示**の個別確認。
- [#305](https://github.com/1kz-ma1/HINANEX/issues/305): S1の実データ適用ゲート。C合成フルチェーン #400は実施設承認ではない。

## 実装スコープ
`validation/validation/plan_facility_evidence_review.py` を追加する。`plan(packet)`は**毎回既存Cの`preflight(packet)`を呼び直す**。利用者が持ち込んだ「preflight PASS」のJSON報告だけを承認根拠にしない。新たなD/B/E/共有Contract・公式原本・ネットワーク通信・利用者情報・GitHub Issue自動起票・ファイル書き込みは行わない。

出力スキーマ（**C内部**）`hinanex.c.facility_evidence_review_work_queue.v0.1`:
- `status=REVIEW_WORK_QUEUE_ONLY__REAL_DATA_ADOPTION_HOLD`、`source_preflight_status`、ケース件数、理由別修正タスク件数、必須認証タスク件数を持つ。
- `cases[]`は、元のopaqueな`case_id`と`preflight_status`、`gap_reason_count`、`tasks[]`を保持。タスクは **(a) 検出した理由コードごとに1件の`GAP_REMEDIATION`** と **(b) 各ケース必ず4件の`INDEPENDENT_AUTHENTICATION`**。原本URL/Raw/人名/ハッシュそのものは出力しない。
- `tasks[]`は決定論的な`task_id`、`evidence_area`、`reason_code`、`responsible_roles`、`action_code`、`required_field_paths`、`status=OPEN__UNVERIFIED`、`requires_human_review=true`、`approval_granted=false`。担当は運用上の**役割候補**であって自動アサイン・実施済みではない。
- 理由コードと対象フィールドの対応は閉じたマップ。C preflightに新理由コードが追加された際は**未対応理由のタスクを黙って落とさず`WorkQueueError`**で停止し、独立の仕様更新を要する。

## 作業ゲート・依存

| 調査単位 | 担当候補 | 集めて独立検証する証拠（例） | 完了後も別途必要な確認 |
| --- | --- | --- | --- |
| `source` | A（原本）→C（バイト照合） | 元URL、Raw bytes/SHA、取得日時、原文行locator、資料の更新/対象時点 | Cによる原本バイトとSHAの独立照合、版/対象時点の真正性 |
| `identity` | A（両原本）・C（施設単位照合） | それぞれの原本・行ID・住所/施設建物単位の一次資料・別ソース審査記録 | 名前だけではなく**同じ建物/対象範囲**であるという独立の人間承認 |
| `hazard_meaning` | A/C/D | 該当自治体・該当列の生記号、正式な意味資料、災害種別/条件/資料版 | Dの判定への明示的意味決定、C独立照合、UNKNOWN維持 |
| `reuse` | A/OWNER | 当該資料の利用規約、第三者権利・個別例外の調査、出典/加工表示 | 公開対象に対する利用条件・帰属・誤認防止の人間の最終審査 |

**4つの独立審査タスクは、参照欄がすべて埋まっていても常に未完了。** 例えば提出された2つのSHA文字列が一致しても、別担当が実原本バイトを照合した証明にはならない。レビュー参照IDもレビュー本文の真正性・権限・採否を証明しない。

衝突したSHA/版・原文の災害範囲不整合・証拠`CONFLICTING`には`RECONCILE_CONFLICT_AND_RECHECK_SOURCE`の修正タスクを出す。別版のレビューを流用しない。古い資料や未確認を自治体の「データ不存在」に読み替えない。

## 固定安全宣言

どの入力でも以下を`false`に固定:
- `source_bytes_authenticated_by_this_run`
- `independent_human_approval_recorded_by_this_run`
- `official_facility_identity_approved`
- `hazard_semantics_approved`
- `dataset_reuse_approved`
- `eligible_for_s1_real_facilities`
- `publication_approved`

`human_decision_required=true`を固定する。S0→UIのDraft #386/#387の採否、F05/B2、RegionExport v0.9、Dの`UNKNOWN`、GIS公開は一切変更しない。

## 実行
リポジトリrootで（3件の**架空**参照パケット。URLは`example.invalid`、実施設は含まない）:

~~~sh
python validation/validation/plan_facility_evidence_review.py \
  --packet validation/fixtures/facility_evidence_packet_synthetic_v01.json --json
python -m unittest discover -s validation/validation \
  -p 'test_plan_facility_evidence_review.py' -v
~~~

既存の[入力仕様](FACILITY_EVIDENCE_PACKET_PREFLIGHT_V01.md)に従い、実資料の参照パケットは**Git管理外の制限された領域**に置く。CLIはstdoutへ作業票を表示するだけでファイル書込・原本取得・Issue作成・本番利用を行わない。正常な作業票生成の`exit 0`は**データ受入やレビュー完了のPASSではない**。不正入力・未知理由コードは`exit 2`で拒否。

## 検証と今後の境界
`test_plan_facility_evidence_review.py`は、完全なメタデータでも4レビューがOPEN、欠落理由をすべてタスク化、原本/別施設SHA不一致・個別ライセンス・災害範囲・未審査、入力改ざん・プライバシー不要な出力・決定論・非書き込み・未知コードのfail-closedを検査する。required `test`、C Scope Guard等はPR CIの正確なHEADで別記録する。

**Device QA:** Cの純粋Python作業票生成はNOT_REQUIRED。実機/B UI・個別原本・利用条件・災害時適合の確認、S1の実データ接続、一般公開はすべて未実施/NO-GO。別のA/C/D/Ownerによる実際のレビュー成果を、今回の作業票から自動的に承認へ反映させない。
