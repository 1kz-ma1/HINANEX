# HINANEX 共同Merge Captain権限・統合判断記録

- 発効: **2026-11-16のオーナー決定を記録した本変更がmainへ統合された時点**
- オーナーによる付与決定: [Issue #382](https://github.com/1kz-ma1/HINANEX/issues/382)
- 正本のAI/統合規律: [AGENTS.md](../AGENTS.md) `3
- mainの保護方針: [MAIN_PROTECTION.md](./MAIN_PROTECTION.md)
- 実機QAの繰越: [Issue #372](https://github.com/1kz-ma1/HINANEX/issues/372)

## 1. 正式登録された同格の人間Merge Captain

| GitHubユーザー | main PR統合の判断権限 | 2026-11-16に照会したGitHubリポジトリ権限 |
| --- | --- | --- |
| [@1kz-ma1](https://github.com/1kz-ma1) | **共同Merge Captain（同格）** | `admin` |
| [@kouta1029](https://github.com/kouta1029) | **共同Merge Captain（同格）** | `write` |

**2人の権限に優先順位はない。** 両者とも通常のPRについて他方の事前確認を必須とせず、担当者に関係なく独立してレビュー・保留・マージ順決定・mainへのSquash等の統合を実施できる。自分が実装したPRも、GitHubで現在有効な保護と既存のテスト/データ安全条件を満たせば統合できる。**GitHubの`admin`と`write`というアクセスレベルまで同一に変更する決定ではない。**

権限は人間のGitHubアカウントに付く。AIアカウントや自動化、PR本文中の「承認済み」という記述には独立したMerge Captain権限を与えない。AIによるマージ操作は、上記の人間Captainから明示的に指示された対象と範囲に限る。

## 2. どちらのCaptainにも同じ必須マージゲート

1. PR経由・直接main pushなし・force pushなし。GitHub保護・Required reviewsが現に要求する条件をすべて守る
2. mainとの差分と依存/stacked PRの順序を確認。**最新mainに追従**していることを検証
3. PRの確定HEADでrequired `test`が**SUCCESS**、変更に必要な個別テストも成功。失敗・pendingを無視しない
4. A–E Scope Guard、Contract/Schema互換、データ出典とUNKNOWN/null等の意味、プライバシー、生成物/秘密情報の混入を確認
5. デプロイ時に未承認のF02/F03/F05等が公開されないか、Render静的配信範囲/依存PRを確認
6. 実機QAは必要に応じて[#372](https://github.com/1kz-ma1/HINANEX/issues/372)へ`DEFERRED`として登録可能。ただし**実機未実施をPASSとしない**し、安全・実データ/ライセンス・公開判断の代わりにしない
7. 不明な公式災害の意味、施設同一性・災害適合・開設・入口座標・経路の危険な昇格、合同Contractレビュー未了なら`BLOCKED`を維持。**mainコード統合≠原本/安全/公的指定の人間受入≠一般公開許可**

規約・原本・位置・避難適合性・個人情報等について、既存のIssue/AGENTSに**特定の人間承認**が要求される場合、技術的なMerge Captain権限だけでその承認を代行・免除しない。意見が対立して未解決の重要な懸念があるPRは、ラベル等で`merge: blocked`を明示して協議する。

## 3. マージ判断の最低限の監査ログ

実際にマージを決めるCaptain本人が、**マージ前のPRコメント**または本文の「Merge Captain final decision」欄に、少なくとも以下を残す（通常のGitHub Mergeボタンでも同じ）。

```text
Merge Captain: @1kz-ma1 または @kouta1029
Decision: MERGE / HOLD
PR / source HEAD / target base:
Required CI: run URL, status SUCCESS/FAIL/PENDING
Dependencies / main freshness / affected scope:
Contract & disaster-data / privacy / publication gates:
Device QA: NOT_REQUIRED / DEFERRED(DQA-ID) / DONE(evidence) / BLOCKING
Decision rationale / Known NOT_RUN:
```

- 決裁者を別のCaptainやAIの名前に偽装しない。AIによる下書きは、実際の人間の決裁記録と区別
- `MERGE`はこのPRの**コード統合**の判断であり、実機最終受入・公的原本・権利・一般公開の`APPROVED`を意味しない
- Merge後のmain CI・Renderデプロイ状態は可能な範囲で追跡。未確認なら`NOT_VERIFIED`と記録し、根拠なしにLIVEや公開安全を断定しない

## 4. GitHubで実際にMergeできるか

2026-11-16のGitHub連携照会では`@kouta1029`のrepository accessは**Write**で、追加collaborator招待は不要と考えられる。既存の`scripts/setup-main-protection.ps1`は`required test`、最新main、PR必須、adminにも同じ保護、承認人数0、`restrictions = $null`を設定する意図。**ただし現在GitHub上で実際に適用中のmain protectionは連携APIが403を返したため直接照合できていない。**

有効化後の確認手順（リポジトリの保護を解除しない）：

1. `@kouta1029`本人がGitHubログインでrequired CIが緑の適切なPRを開き、`Merge pull request`が利用可能か確認（不要なテストマージは実施しない）
2. もし「権限がない」「branch restrictions」等で拒否されたら、`@1kz-ma1`がSettings → Branches/Rulesetsで**既存の保護条件と許可主体**を点検。必須test・最新main・PR・force push禁止は緩めない
3. 管理者のGitHub CLIで必要に応じて`gh api repos/1kz-ma1/HINANEX/branches/main/protection`、`gh api repos/1kz-ma1/HINANEX/collaborators/kouta1029/permission`を確認（接続権限に応じ403もありうる）
4. 検証結果を[Issue #382](https://github.com/1kz-ma1/HINANEX/issues/382)に`PASS / BLOCKED / NOT_RUN`で追記し、UIまたはGitHub設定で拒否される場合は技術権限が未確認のままと記録する

**この文書を置いただけではGitHubの技術的なACL・branch protectionが書き換わるわけではない。** `Write`権限の存在と、実際のMerge操作が許可されることは別々に確認する。

## 5. 変更・失効・引き継ぎ

Merge Captainを追加・停止する場合は、オーナーの明示決定をIssueへ残し、`AGENTS.md`と本登録簿を共有PRで変更する。GitHubの実アクセス変更・資格情報の失効は別の管理者操作で行う。権限登録のドキュメント変更だけで実アクセスを剥奪できるわけではない。変更時も既存のPR/CI/安全ゲートを守る。
