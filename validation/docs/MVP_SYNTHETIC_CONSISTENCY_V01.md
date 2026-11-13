# C / MVP固定合成シナリオ整合性検証 v0.1

**状態:** C領域限定の実装・回帰仕様（2026-11-13）。公式Sourceの受入、災害時の安全判断、運用公開承認ではない。

## 目的と責務

2027-02-09の卒業制作MVP向けに、**架空の入力・出力スナップショット間の不整合**を再現可能な形で検知する。Issue [#305](https://github.com/1kz-ma1/HINANEX/issues/305)、[#360](https://github.com/1kz-ma1/HINANEX/issues/360)、[#372](https://github.com/1kz-ma1/HINANEX/issues/372) に対応するC専用の負例回帰である。

- 範囲: `validation/fixtures/mvp_synthetic_consistency_v01.json`、`validation/validation/verify_mvp_synthetic_scenarios.py`、専用回帰テスト、本仕様。
- Dの判定ロジックや`RegionExport`、既存の実原本監査、2019江戸川区歴史デモ、S0/H0状態処理、F01/F02/F05 UIは**読み込みも変更もしない**。
- 入力/出力形式は**検証用ローカルenvelope**。共有Contract案や正式な製品APIではない。fixtureの`SYNTH_*`・`FLOOD`・`LANDSLIDE`は架空ラベルで、地域・施設・災害適合の承認を示さない。
- ネットワークなし、実データなし、現在時刻への依存なし、個人情報なし。外部への書込み、配布、Render設定変更なし。

## 局所スナップショット契約

- トップレベルは`schema_id`固定、`synthetic_only: true`、`template.input/output`とケース列。各ケースは差分`input_delta`/`output_delta`でテンプレートへ再帰的に重ねる。`run: false`は実行しない。
- `input`: `mode`, `hazard`, `region`, `session_token`, `fixture_id`, `observed_at`, `evaluated_at`, `facts`。
- `output`: 上記に対応する`mode/hazard/region/session_token/fixture_id/observed_at`、`generated_at`, `valid_until`, `is_drill`, `facts`, `claims`。
- 時刻は明示的なタイムゾーン付きISO-8601。実行時のシステム時計は使用しない。`valid_until == evaluated_at`は有効、超過は期限切れ。
- `claims`は`facility_safety`, `facility_open`, `route_passability`の3キー。余分なclaimキーがあれば`BLOCKED`。合成データで許される値は `null`, `UNKNOWN`, `UNVERIFIED` のみ。真偽値・`CONFIRMED`・`CLOSED`を含む判断を**受け入れない**。安全な施設・開設中・通行可能といった意味は推論しない。
- `facts`は未変換のサンプルフィールド。`null`と`UNKNOWN`は出力でも同じ形で保持する。元入力にない確定値、元入力からの値変更を拒否する。これはサンプルの同値性確認であり、Dの正規化規則を定義しない。

## 検証順序と受入テスト

| 分類 | 必須検査 | 代表ケース |
| --- | --- | --- |
| モード | NORMAL/DRILL、出力モードと`is_drill`の一致 | `normal_labeled_drill`, `drill_output_switched_normal` |
| 対象 | hazard/regionの正確な一致 | `hazard_crossed`, `region_crossed` |
| 不明情報 | `null`/`UNKNOWN`の保存と新しい確定値の拒否 | `null_inferred_as_zero`, `untraced_new_fact` |
| 鮮度 | session/fixture/observed_atの一致、生成時刻と期限 | `session_changed_result_reused`, `expired_result` |
| 安全断定 | 合成の施設安全・開設・経路に確定値を置かない | `facility_safety_asserted`, `route_passable_asserted` |
| 保留 | 入力不足・不正な時刻は判断を保留 | `missing_expiry_blocks_review` |
| 未実施 | 意図的に保留した検証は実施済みと書かない | `mobile_device_rehearsal_placeholder` |

**各ケースの`actual`と`expected`は別々に出力する。** 意図的な負例の`actual=FAIL`は、`expected=FAIL`に一致している限り回帰として正常。回帰全体の`PASS`は公式データや実機のPASSではない。

## ステータスと終了コード

- `PASS`: 合成スナップショット間に今回のチェックで不整合がない。
- `FAIL`: 契約外のモード・地域・ハザード・期限・推論・未承認断定を検出。
- `BLOCKED`: 必須スナップショット・必要項目・日付・claim等が不足し、適否を判断できない。安全とみなさない。
- `NOT_RUN`: `run: false`で明示的に実行していない。実機QAも別途`NOT_RUN`。
- CLI `exit 0`: 全ケースの**期待した判定との一致**、`exit 1`: 回帰不一致、`exit 2`: fixture読込不能/不正。JSONレポートの`official_acceptance`は常に`false`、`device_qa`は`NOT_RUN`。

## 実行

リポジトリrootから:

```sh
python validation/validation/verify_mvp_synthetic_scenarios.py
python validation/validation/verify_mvp_synthetic_scenarios.py --json
python -m unittest discover -s validation/validation -p 'test_verify_mvp_synthetic_scenarios.py' -v
```

既存の`.github/workflows/test.yml`は`validation/validation/test_*.py`を自動検出するため、新たなCI編集は不要。既存のC監査群と別のコマンドでも再現できる。

## 統合時・発表時の安全上の境界

本ケースのPASSを、一次資料原本照合、C独立データ受入、人間による施設・災害対応の認定、現在の開設状況、参考経路の通行可能性、配信許可として引用しない。実際のS0/H0やUIとの結合は共有契約の別レビュー後に別PRで扱う。

本PRはPython CLIと合成fixtureに限り端末依存性がないため、Issue #372のPR区分は`Device QA: NOT_REQUIRED`（実機での自動検証範囲なし）。将来の実機デモは別のPR/QA枠で管理し、ここでは`NOT_RUN`のまま扱う。
