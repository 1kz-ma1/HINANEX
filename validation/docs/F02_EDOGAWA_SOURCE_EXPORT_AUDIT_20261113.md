# F02 C検証：江戸川区公式CSVとD出力の独立全行照合

## 目的と証拠（2026-11-13）
- 対象は B Issue #355 / Draft PR #357 の江戸川区 RegionExport 0.9・shelter_location のみに限定。
- 利用者がMacで独立取得した公式CSVとD保存 raw CSVのSHA256は一致：`64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea`。
- 現物D出力は152行、A-D READY、B構造と実Chrome表示はPASS（いずれも利用者実行ログ）。C全行照合はまだ未実施。
- C監査スクリプトはD Adapter/APIをimportしない。旧C water-join監査と異なり水害施設HTMLやA台帳を要求しない。

## 技術的な検証範囲
1. Cが別取得したCSV・D rawの**バイト一致**と指定SHA256。
2. CP932 CSVのヘッダ・全行数値・名称・座標。
3. 正規化JSONとRegionExportについて、CSV全行の名前、座標、安定ID、出典URL/コメント、住所の原文パススルー、保守的なnull属性。
4. 江戸川区コード13123、shelter_location、Schema 0.9、Assessment件数、Dataset evidenceの元URLとpublished_atの扱い。
5. 不一致は `C_SOURCE_TO_EXPORT_HOLD`、一致は `C_SOURCE_TO_EXPORT_CONSISTENT`。原本の行数152は固定しない。

## Macからの実行方法（既存Bブランチを変更しない）
Git管理外の `$HOME/HINANEX-f02-c-evidence` に検証コードと証拠を保存する。

```bash
cd "$HOME/HINANEX-f02"
git fetch origin feature/c-f02-edogawa-source-export-audit-20261113
git show FETCH_HEAD:validation/validation/verify_f02_edogawa_source_export.py > "$HOME/HINANEX-f02-c-evidence/verify_f02_edogawa_source_export.py"
git show FETCH_HEAD:validation/validation/test_verify_f02_edogawa_source_export.py > "$HOME/HINANEX-f02-c-evidence/test_verify_f02_edogawa_source_export.py"
source pipeline/.venv312/bin/activate
python -m unittest discover -s "$HOME/HINANEX-f02-c-evidence" -p "test_verify_f02_edogawa_source_export.py" -v
python "$HOME/HINANEX-f02-c-evidence/verify_f02_edogawa_source_export.py" \
  --official-csv "$HOME/HINANEX-f02-c-evidence/edogawa-official.csv" \
  --d-raw-csv "pipeline/data/raw/edogawa/20251211_hinanhokan.csv" \
  --normalized "pipeline/data/normalized/edogawa_shelters.json" \
  --region-export "pipeline/data/output/edogawa.json" \
  --expected-sha256 64b1c02377ac6caa2cf58faaf45e34ed76d01b7230c9c4d4590432864700d7ea \
  --report "$HOME/HINANEX-f02-c-evidence/f02-edogawa-c-audit-$(date +%Y%m%d-%H%M%S).json"
```

## 判断の境界
- 全行一致はDが元CSVを既定の形式へ変換したことの技術証拠に限定。施設安全性や災害適合・現況・公式指定・入口・敷地/校舎同一性ではない。
- 所在と属性について推測追加は行わない。source URLが一致しても発行元の真正性・更新日・再利用条件の最終承認は別。
- 元CSVと監査レポートはGit/Renderに保存しない。レポートはSHA、行数、判定と限界だけ。読み取り専用でD/B本番ファイルは書き換えない。
- Cの技術判定が通っても、A/Cによる公式原本・施設単位の意味の承認と公開ゲートはHOLD。Draft PR #357はmainへ自動統合しない。

関連: validation/docs/EDOGAWA_REAL_C_COMPARATOR_HANDOFF_20261019.md、validation/AGENTS.md。
