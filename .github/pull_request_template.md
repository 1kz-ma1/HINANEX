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

## Device QA disposition（実機QA分類を1つ選択）

<!-- 運用仕様: docs/strategy/HINANEX_IMPLEMENTATION_FIRST_DEVICE_QA_20261113.md
     実機QA共通Issue: https://github.com/1kz-ma1/HINANEX/issues/372
     原則: required CIを先に通す。実機QA未実施とデータ/公開未承認は別の状態。 -->
- [ ] `NOT_REQUIRED` — 実機固有の変更なし（理由と代替テストを記載）
- [ ] `DEFERRED` — 決めた実機QA回へ繰越（#372のDQA-IDまたはコメントURL必須）
- [ ] `DONE` — 人間の実機結果記録済み（対象SHA/端末/OS/ブラウザ/実行者・証跡）
- [ ] `BLOCKING` — 安全/端末特有の重大依存等により統合前の確認が必要（Issueと理由）

- 選択理由:
- DQA-ID/管理Issue: <!-- DEFERRED時必須 -->
- 予定実機QA回（暫定可）:
- 人間による実機実行者・端末・OS/ブラウザ・対象ビルドSHA（DONE時）:
- 実機テストのPassed / Failed / Not run:
- 一般公開・実データ・施設/経路の安全ゲート（main統合とは別）:

**注意:** `DEFERRED` はrequired `test`の省略、事故リスクの放置、未承認データのRender公開を許可しない。未確認の実機結果をPASSとしない。

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
- [ ] role-scoped PRでは変更が担当ディレクトリ内だけであることを確認した
- [ ] Shared / 他担当変更が必要なら別PRへ切り分けた
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
