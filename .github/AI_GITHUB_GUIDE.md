# AI-guided GitHub Workflow

このガイドは、GitHub 操作に慣れていないメンバーが **自分の担当 AI に「次に何をすればいい？」と聞くだけで、安全に作業できる状態**を目的にしています。

AI は最初に `/AGENTS.md` と対象ディレクトリの `AGENTS.md` を読み、本ガイドを Git 操作の補助手順として使用してください。

## 1. 担当ブランチ

| 担当 | Role branch | Area label |
|---|---|---|
| A / Data Research | `role/a-data` | `area: data` |
| B / Frontend | `role/b-frontend` | `area: frontend` |
| C / Validation | `role/c-validation` | `area: validation` |
| D / Pipeline | `role/d-pipeline` | `area: pipeline` |
| E / GIS | `role/e-gis` | `area: gis` |

## 2. AI が作業開始時に案内すること

通常の feature 作業:

```powershell
git fetch origin
git switch <role-branch>
git pull origin <role-branch>
git switch -c feature/<role>-<topic>
```

例:

```powershell
git fetch origin
git switch role/b-frontend
git pull origin role/b-frontend
git switch -c feature/b-risk-card
```

AI はユーザーが GitHub に不慣れでも、現在の branch と `git status` を確認してからコマンドを案内してください。

## 3. 担当内 PR

feature branch の作業が終わったら、原則として対応する role branch へ PR を出します。

例:

```text
feature/b-risk-card
    ↓ PR
role/b-frontend
```

この段階では main に入れる必要はありません。


## 3.5 PR Creation Gate

feature branch の実装が終わっても、すぐに「統合準備完了」と判断しません。

AI は PR を作る前に次を確認します。

```text
Implementation complete
        ↓
target/base branch を確認
        ↓
最新 main との差分を確認
        ↓
依存 PR / shared change を確認
        ↓
tests / CI を確認
        ↓
PR created
        ↓
必要なら base 更新 + 再テスト
        ↓
Integration ready
        ↓
Merge Captain review
        ↓
Merge ready
```

### base が古い場合

role branch が main より古いこと自体は問題ではありません。
ただし、main 側の次の変更が今回の検証へ影響する場合は更新が必要です。

- `.github/workflows/**`
- shared Contract / Schema
- repository structure
- shared scripts
- AI / contribution rules
- test infrastructure

AI は `main...<target-base>` を比較し、影響する変更を取り込んでいない場合は `merge: needs-update` を提案してください。

### CI が red / pending の場合

- merge を勧めない。
- 通常の ready 状態として扱わない。
- base 更新で直るなら先に更新する。
- 直せない場合は Draft または `merge: blocked` / `merge: needs-update` として提出する。
- 「自分の差分が原因ではない」だけでは green 扱いにしない。

### テスト結果の書き方

```text
Passed:
- node --test: 6 passed

Failed:
- required check test: failed

Not run:
- browser E2E

Reason:
- target role branch が最新 main の CI 修正を未取り込み
```

一部成功を「すべて成功」とまとめないでください。

### 完了状態の言葉

- Implementation complete = 実装終了
- PR created = PR作成済み
- Integration ready = target branch へ統合可能な候補
- Merge ready = Merge Captain が最終確認済み

AI はこの4つを混同しません。

## 4. 前提 PR がある場合

前提変更が未マージでも開発を止める必要はありません。

PR 本文に必ず:

```text
Depends on: #123
```

を記載し、`depends-on` と `merge: blocked` を付けます。

必要なら前提 branch から後続 branch を切って stacked PR として進めます。

前提が解消したら:

1. 最新の target branch / main を取り込む
2. conflict を解消する
3. tests / CI を再実行する
4. `merge: needs-update` / `merge: blocked` を外す候補として人間へ報告する

AI は自分の判断だけで `merge: ready` にしません。

## 5. main に統合したいとき

role branch に作業がまとまったら、main への PR を作成できます。

ただし main への merge は Merge Captain が判断します。

AI は PR 作成時に以下を整理してください。

- 依存 PR
- Contract impact
- CI / test result
- 他担当への影響
- 推奨 label
- 最新 main への追従状況

Merge Captain は作成順ではなく、依存関係と影響範囲で merge 順を決めます。

## 6. Label の使い方

### Area

通常は 1 つ選択します。

- `area: data`
- `area: frontend`
- `area: validation`
- `area: pipeline`
- `area: gis`
- `area: shared`

複数担当にまたがる共有変更では `area: shared` を使います。

### Change type

必要なものだけ追加します。

- `depends-on`: 他 PR / branch に依存
- `contract-change`: Schema / shared API / shared contract を変更
- `breaking-change`: 後方互換性を壊す
- `critical-fix`: main や統合を止める重大修正
- `docs-only`: 文書のみ
- `ai-authored`: AI がコードまたは文書を実質的に作成

### Merge state

merge state は統合判断を表します。

- `merge: blocked`: 依存や未解決問題がある
- `merge: needs-update`: base が古い / 再テストが必要
- `merge: captain-review`: Merge Captain の最終確認待ち
- `merge: ready`: Merge Captain が target branch へ統合可能と判断済み

**AI は `merge: ready` を独断で設定しません。**

## 7. AI が PR 作成時に確認すること

PR 本文には最低限:

- Summary
- Why
- Scope
- Depends on
- Contract impact
- Tests
- Data assumptions
- Known limitations
- Suggested labels

を記載します。

AI が作成・実装に関与した場合は `ai-authored` を推奨します。

## 8. 困ったとき

メンバーは GitHub の操作を覚えていなくても構いません。

AI に例えば次のように依頼できます。

> B担当の作業を始めたい。HINANEXのルールに従って、今のGit状態を確認してから必要なコマンドを1つずつ案内して。

> このPRは別のPRに依存している。HINANEXのルールに従ってbase、Depends on、labelsを整理して。

> mainに統合したい。自分でmergeせず、Merge Captainが判断できる状態までPRを整えて。

AI は操作を推測せず、現在 branch / status / remote / dependency を確認しながら案内してください。

## 9. main の required check

main への PR では GitHub Actions の `test` が required check です。

AI は:
- red の原因を確認してから修正する
- CIを回避しない
- test削除・skipでgreenに見せない
- pending / red のPRをmerge可能と案内しない
- 最新mainへ追従後に再度greenを確認する

Branch protection の詳細は `.github/MAIN_PROTECTION.md` を参照してください。
