# B担当への引き渡し — UI

Bは自治体固有のCSV/Excelを直接読みません。Dが生成する1地域1JSONを利用します。

```text
data/output/edogawa.json
data/output/niigata.json
data/output/nagoya.json
```

## 固定トップレベル

```json
{
  "region": {},
  "datasets": [],
  "assessments": [],
  "capabilities": [],
  "gaps": [],
  "recommendations": [],
  "meta": {}
}
```

## UIで重要な扱い

- `score=null` を0点として表示しない。
- `UNKNOWN` を「悪い」と表現しない。
- `BLOCKED` はCapabilityが現在のデータでは成立しない状態であり、自治体評価ではない。
- `FULL` は現在の `shelter_location` が位置ベースのShelter Discovery条件を満たす意味に限定する。安全な避難所選定や災害適合性まで保証する表示にしない。
- `INVESTIGATION` は追加調査対象であり、改善不足の断定ではない。
- 緯度経度は`null`になり得る。地図上に無理に配置しない。

## 推奨表示単位

地域選択後に以下を同一画面で辿れるとよいです。

1. Capability状態
2. Data Quality / Application Readiness
3. Gap
4. Recommendation
5. Evidence / reason

### 名古屋市の現行Dataset scope

名古屋市の `shelter_location` は、D Adapterが取得する16区別の屋内施設Excelのみを対象にしています。同じ公式ページ上の屋外施設データは含まれないため、record件数を「名古屋市の全避難関連施設数」と表示しないでください。

JSON Schemaは `contracts/region_export.schema.json` を参照してください。

## 洪水Scenarioの任意Consumer対応

`RegionExport.scenarios[]` は位置探索とは別の任意データです。存在する場合のみ `scenario_id=flood_shelter_selection` の `facility_results` と `fact.official_status_raw` / `reason` / `source_url` を説明表示できます。`CANDIDATE` は安全保証、`EXCLUDED` は危険認定ではありません。`UNKNOWN` は候補外へ変換禁止です。最終仕様は `docs/FLOOD_SCENARIO_CONTRACT.md`。

**新潟市の利用階raw情報（A #43/D追加）**: `fact.usable_floor_raw` が `2階以上` / `3階以上` / `全階可` の場合、**Scenario status は UNKNOWN のまま**です。これは公式CSVに記載された生の階数表現であり、無条件に利用可能、安全、現在開設中を意味しません。UIでは `UNKNOWN` を隠して「利用不可」と表示せず、元の値・公式出典・意味論未検証の注意をセットで表示してください。`○/×/－`の現行ODS固有意味はA/C確認待ちです。
