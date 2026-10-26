# Location Verification Engine — 第1段階・市川市UNREVIEWED実証（2026-10-26）

**状態：D内部のオフラインtriageのみ。ルーティング・GIS表示・公開・C人的承認は一切不可。**

## 分離する3つの位置概念

- `reference_point`：GSI原本のPoint座標。原本参照用であり、入口や安全な避難地点とは**証明されていない**。
- `facility_geometry`：建物・公園・広場の公式敷地/区域。**本PRではすべてnull**。GSIのPointから敷地形状を生成しない。
- `navigation_endpoint`：実際に利用できることが検証された入口・集合地点。**本PRではすべてnull**。住所ジオコーディング、OSMの未審査入口、代表座標を代用しない。

このモジュールは入力ソースの文字列一致と例外抽出だけを行い、`may_publish_reference_point=false`・`may_offer_navigation=false`・`navigation_allowed_count=0` を必ず返す。名称・住所の一致は施設同一性・開設・安全を保証しない。

## 第1段階の入力と出力

- 入力① GitHub Actions [#40258746945](https://github.com/1kz-ma1/HINANEX/actions/runs/40258746945) が保存した実GSI `skhb02` GeoJSON（タイル z10/909/403）。原本はGit管理外、SHA256をC台帳で固定。
- 入力② C側の [Draft #316](https://github.com/1kz-ma1/HINANEX/pull/316) にあるAI転記未承認の市川市対照台帳 `validation/reference/ichikawa_skhb02_20261026_AI_UNREVIEWED.json`。本PRはC側コードをimportせず、ファイルもコピーしない。
- 町名/住所・名称の完全一致を`NAME_ADDRESS_TEXT_MATCH_UNAPPROVED`に分類。
- 名前/住所の不一致、河川敷・緑地・公園・グラウンド等の**名称文字列から推測される要確認パターン**を例外キューに振り分ける。文字列heuristicは確定的な施設範囲・危険度評価ではない。地先表記は区域の広がりが曖昧なものとして追加レビュー。
- 台帳からの対象レコード欠落・重複、原本SHA不一致、GSIの災害属性・座標・タイル不一致、URL偽装、AI転記を承認済みに変更した入力は拒否する。
- `human_location_review_queue`は位置の例外キュー。**例外ゼロでも、元資料の独立人的承認や利用者向けナビ許可にはならない**。

### 実データの未承認入力を使う手順（C #316がmainへ統合されてから）

```bash
cd pipeline
python -m src.hinanex.location_verification \
  --gsi-raw /outside-repo/skhb02-10-909-403.geojson \
  --c-reference ../validation/reference/ichikawa_skhb02_20261026_AI_UNREVIEWED.json \
  --report-out /outside-repo/ichikawa_location_triage_UNAPPROVED.json
```

実データ件数は**原本・転記台帳の検証後に計算**する。29件中28件の文字列一致・#571の住所差異という既存監査結果は、実原本を投入したときに再計算するための期待ケース。未照合の施設を自動追加しない。

## 次の段階（別PR）

1. **A**：公式共通IDが実際に付与され、取得できる場合のみその原文を保持する。市川市の29件に共通IDを推測付与しない。
2. **C**：PDF原本の版・ハッシュ・各行の独立人的承認と#571の住所範囲・敷地境界の確認。今の #316 は未承認。
3. **D**：出典つき `facility_geometry`（単なるOSM polygonを公的根拠に昇格させない）、真正な入口の検証と危険区域の証跡。公式の避難場所の指定と現在の開設は別。
4. **E**：Cが受け入れた参照地点のみ利用条件付きで表示。ナビ可否は別の安全基準と人的承認が必要。今回のD出力はEへ接続しない。

**スコープ：pipeline/**のみ。RegionExport/Schema、既存D評価ロジック、GIS、live consumerの変更なし。合成テストは `python -m unittest discover -s tests -p test_location_verification.py -v`、さらに通常Dテスト `python -m unittest discover -s tests -v`。 `verify_d_mvp.py` は生成済みruntime出力がない場合は実施不可であり、CIの成功とは分けて報告。
