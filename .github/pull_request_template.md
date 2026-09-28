## Summary

<!-- 何を変更したか -->

## Why

<!-- なぜ必要か -->

## Scope / 担当

- [ ] A / Data Research
- [ ] B / Frontend
- [ ] C / Validation
- [ ] D / Pipeline
- [ ] E / GIS
- [ ] Shared / 共通

## Dependency

- Depends on: none
<!-- 依存PRがある場合: Depends on: #123 -->

## Contract impact

- [ ] none
- [ ] additive
- [ ] breaking

### Contract変更がある場合

- schema_version:
- 変更フィールド:
- 影響する担当:
- migration:

## Tests

<!-- 実行したコマンドと結果。未実行なら理由を書く -->

## Data assumptions

<!-- 防災データについて推測で補完していないこと。確認不能点があれば明記 -->

## Known limitations

<!-- 未解決事項 -->

## Suggested labels

<!-- AIは .github/labels.json と AGENTS.md に従って提案する -->
- Area:
- Change metadata:
- Merge state:

## Checklist

- [ ] 最新の対象baseを確認した
- [ ] 必要なtests / CIを実行した、または未実行理由を記載した
- [ ] `score=null` と `score=0` を混同していない
- [ ] `NOT_FOUND` を自治体の未公開と断定していない
- [ ] Rawデータ・秘密情報・ローカル絶対パスをコミットしていない
- [ ] 必要なdocs/testsを更新した
- [ ] 前提PRがある場合は `Depends on: #...` を記載した
- [ ] AIが実装に関与した場合は `ai-authored` を推奨した
- [ ] mainへのmerge判断をMerge Captainに残している
