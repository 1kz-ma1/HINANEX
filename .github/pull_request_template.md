## 変更内容

<!-- 何を、なぜ変更したか -->

## 担当

- [ ] A / Data Research
- [ ] B / UI
- [ ] C / Validation
- [ ] D / Pipeline
- [ ] E / GIS
- [ ] 共通

## 影響範囲

- [ ] RegionExport契約に影響なし
- [ ] RegionExport契約に影響あり（下記にmigrationを記載）
- [ ] 評価ルールに影響あり
- [ ] 取得元/Evidenceに影響あり
- [ ] UI/GIS表示のみ

## 確認

- [ ] `python -m unittest discover -s tests -v` が成功した
- [ ] `score=null` と `score=0` を混同していない
- [ ] `NOT_FOUND` を自治体の未公開と断定していない
- [ ] Rawデータ・秘密情報・ローカル絶対パスをコミットしていない
- [ ] 必要なdocs/testsを更新した

## B/C契約変更がある場合

- schema_version:
- 変更フィールド:
- Bへの影響:
- Cへの影響:
- migration:
