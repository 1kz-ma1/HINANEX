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

## Integration readiness

- Target/base branch:
- Base vs latest main:
- Shared CI / Contract / repository structure の影響:
- Current state:
  - [ ] Implementation complete
  - [ ] PR created
  - [ ] Integration ready
  - [ ] Merge ready（Merge Captainのみ）

<!-- base更新が必要なら merge: needs-update。依存/未解決があれば merge: blocked -->

## Tests

### Passed

<!-- 成功したコマンドと結果 -->

### Failed

<!-- 失敗がなければ none -->

### Not run

<!-- 未実行がなければ none -->

### Reason / Notes

<!-- 失敗・未実行・base差分の影響など -->

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

- [ ] `git status` と現在branchを確認した
- [ ] PRのtarget/base branchを確認した
- [ ] target/base branchと最新mainの差分を確認した
- [ ] main側のshared CI / Contract / test infrastructure変更が今回へ影響しないか確認した
- [ ] 前提PR / stacked PRの有無を確認した
- [ ] tests結果を Passed / Failed / Not run に分けて記載した
- [ ] required checkがred/pendingならIntegration ready扱いにしていない
- [ ] 必要なら `merge: needs-update` / `merge: blocked` を提案した
- [ ] `score=null` と `score=0` を混同していない
- [ ] `NOT_FOUND` を自治体の未公開と断定していない
- [ ] Rawデータ・秘密情報・ローカル絶対パスをコミットしていない
- [ ] 必要なdocs/testsを更新した
- [ ] 前提PRがある場合は `Depends on: #...` を記載した
- [ ] AIが実装に関与した場合は `ai-authored` を推奨した
- [ ] mainへのmerge判断をMerge Captainに残している
