# D 3地域再生成：承認後の前後差分照合（read-only、未承認では実行禁止）

**目的:** Issue #266。A #264 / C #265 の人間レビューを終える前にDを走らせるためのものではない。**今回追加したのは、既に別途生成・検証された2組の RegionExport を比較する閲覧専用ツール**。Git/Renderの本番データや共通Schema、Adapterは変更しない。

## 事前の必須条件（ツールはこれを承認しない）

- 2つの出力集合の元になった**公式原本スナップショット**、取得日時、manifest/source SHA256、A/Cの人間による個別承認、入力適用範囲を外部の証拠台帳へ記録する。CLIは署名を確認しない。
- A/Cに承認された入力だけで、D担当が隔離した非本番環境にて `python run_all_workflows.py` を実行する（本CLIにこの工程はない）。新しい原本を自動取得・更新する場合は独立した取得承認が必要。
- `python verify_d_mvp.py`、`python verify_a_handoff_integration.py`、`python verify_flood_scenario.py` の結果を別々に確認する。C側は公式raw→正規化・評価・出口まで独立して照合する。
- 過去の 152/566/1602 件は以前の観測値であり、固定期待値として使用しない。

## 実行方法

`pipeline/` にいる状態で、**異なる2つのスナップショットフォルダ**（各フォルダに `edogawa.json` / `niigata.json` / `nagoya.json` が必要）を用意し、**Git checkout外**にレポートを出力する。

```bash
cd /path/to/HINANEX/pipeline
python compare_three_region_replays.py \
  --before /private/baseline-output \
  --after /private/new-output \
  --report /private/review/d-three-region-delta-UNREVIEWED.json
```

CLIは**比較のみ**を行い、データ取得・Dワークフロー・Renderデプロイ・A/C承認・施設joinは行わない。同一/ネストした入力フォルダ、シンボリックリンク入力、欠落した3地域、契約違反の出力、重複した地点ID、出典Evidenceの欠落、比較レポートの上書き、入力ディレクトリ・リポジトリへのレポート出力は拒否する。

## 比較項目

- 各 `RegionExport` 原本**出力JSON自体**の SHA256、RegionCode、Schema version、生成日時。
- `shelter_location` 件数、ID集合のdigest、座標欠損数。新しい施設と古い施設を名前や位置で自動対応させない。
- Evidenceの件数と**出典メタデータ**digest（公式原本そのもののSHA256検証とは異なる）。
- 評価指標スコアの `null` / `0` / `1..4` を別々に数え、値を解釈し直さない。
- Capabilityのコード別ステータス、Gap・Recommendation件数。
- Scenarioの `CANDIDATE` / `EXCLUDED` / `UNKNOWN` とjoin状態（`DIRECT_SAME_SOURCE` / `UNVERIFIED`）の件数。ただし状態の増減を安全性評価に昇格させない。

**判定:** 生成物が不正なら失敗。両集合が妥当でもレポートstatusは常に `UNREVIEWED_REQUIRES_INDEPENDENT_C_AUDIT`、`data_promotion_authorized=false`。同一出力でも「現実の安全が確認できた」という意味にはならない。

**テスト:** `cd pipeline && python -m unittest discover -s tests -p 'test_compare_three_region_replays.py' -v`。オフラインfixture、12ケース。`python -m unittest discover -s tests -v` と required CI `test` も別途確認。

**未実施:** A/Cの人間承認、最新原本のD再生成、3地域実データ検証、公開・本番反映。条件未達のままこのCLIで生成される比較レポートを、Cの受入代替に使用しない。

## C独立レビューで追加した検出（2026-10-19）

同じ施設ID、同じ件数、同じ座標欠損数でも、**位置の緯度経度が実際に変わった場合**は `location_coordinates_sha256`、施設名・住所などのレコード内容が変わった場合は `location_records_sha256` で差分として残す。ID順に正規化するので、JSON配列の並び替え自体は意味的差分としない（ただし原本出力JSONのハッシュは変わる）。

Scenarioの集計件数だけでなく施設ID順で原値・根拠・位置を含む `scenarios[].facility_results_sha256` を残す。**施設ID単位の状態差**がある場合は `facility_status_transitions` に IDを公開せず件数だけを出す。既存 `assert_valid_region_export` による `UNKNOWN` 未承認状態の検査は維持する。

これらのSHAは**比較用の出力内容ハッシュ**であって自治体の公式原本、施設同一性、実災害指定状態の証明ではない。差分があればCの原本・行単位監査へ返す。