# A担当 Evidence handoff for D testing

このディレクトリは、A担当が公式ソースから収集したEvidenceをD担当がAdapter/正規化テストへ渡すための引き渡し領域です。

## Files

- `HINANEX_A_final_handoff.json`
  - 3地域（江戸川区 / 新潟市 / 名古屋市）のEvidence Manifest
  - 洪水想定条件
  - アクセシビリティ照合結果
  - 残作業
  - GitHub上で確認した正式region_code / current D-MVP contract情報

## Current formal codes

- 江戸川区: `13123`
- 新潟市: `15100`
- 名古屋市: `23100`
- current implemented DataRequirement: `shelter_location`

洪水・アクセシビリティ等は現行D-MVPで正式なrequirement_codeが未実装のため、A側では推測せず `null` のまま保持しています。

## D testing notes

- Capability / Gap / Recommendation はA担当では判定していません。
- `NOT_FOUND` は「現在のHINANEX探索経路では確認できなかった」の意味です。
- 未確認値は推測せず `null` / `UNKNOWN` / `PARTIAL` 等で保持しています。
- A31a-2025 × N03-2026 の新潟市・名古屋市実空間intersectionは、Aの実行環境から国交省ZIP本体を取得できなかったため未実行です。D/E側で機械処理してください。
- アクセシビリティの未一致は「設備なし」ではありません。未確認として扱ってください。

## Excel

人間確認用Excelは会話成果物として別途保持しています。Repositoryにはgenerated artifactを追加せず、Dの自動テスト対象はJSONを正本とします。


## Machine-readable guarantees

- `human_review_required` is JSON boolean (`true` / `false`), not a string.
- `flood_conditions` and `accessibility_matches` contain the formal `region_code` for municipality-specific rows.
- `download_url` is either an actual HTTP(S) URL or `null`. Explanatory text belongs in `notes`.
- Confirmed `rainfall_duration_hours` and `rainfall_total_mm` values are JSON numbers.
- Undefined future DataRequirement codes remain `null`; A does not invent D-side requirement codes.


## Date metadata convention

- `updated_at` records the official source/page update date when that date is explicitly confirmed.
- A dataset reference date such as “YYYY-MM-DD時点” is not treated as the page update date; keep it in `notes`.
- If the update date cannot be confirmed, keep `updated_at` as `null` rather than inferring it.
