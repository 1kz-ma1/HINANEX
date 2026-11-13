# HINANEX AI Development Rules

このファイルは、HINANEX リポジトリを変更する **すべての AI コーディングエージェントに対する正本（canonical rules）** です。

Claude Code、GitHub Copilot、Gemini、Cursor、ChatGPT、その他の AI ツールは、固有の指示ファイルより先に本ファイルの意図を尊重してください。
ツール固有の指示と本ファイルが矛盾する場合は、本ファイルを優先します。

---

## 1. Before You Change Anything

ファイルを変更する前に必ず次を行ってください。

1. 本 `AGENTS.md` を最後まで読む。
2. 対象ディレクトリに追加の `AGENTS.md` がある場合はそれも読む。
3. 対象機能の README、契約、既存テストを確認する。
4. 変更対象と依存先を特定する。
5. 既存仕様と依頼内容が矛盾していないか確認する。
6. 必要最小限の差分で実装計画を立てる。

仕様・データ・テスト・依頼内容が矛盾している場合、推測で解決しないでください。
作業を止め、矛盾点と必要な判断を人間へ報告してください。

---

## 2. Architecture Boundaries and Feature Ownership

HINANEX は **実現する利用者価値・3軸の成長・依存関係** を基準に実装を計画します。A〜E は過去の担当区分であり、現在は人・AI・チャットの作業権限や着手順序を固定するものではありません。単一の開発者が複数領域を一貫して扱って構いません。

| Legacy area | Directory | Technical responsibility |
|---|---|---|
| A | `data-research/` | 公開データ調査、Evidence、出典・更新日・形式・ライセンスの記録 |
| B | `frontend/` | UI、Dashboard、分析結果の表示 |
| C | `validation/` | Source → Output の独立検証、テスト、検証根拠 |
| D | `pipeline/` | 取得、Adapter、共通Schema、評価、Capability、Gap、Recommendation、Export |
| E | `gis/` | GIS、地図、GeoJSON、空間可視化 |

ディレクトリと契約の境界は **技術的な責務と検証の独立性** を示すもので、担当者の境界ではありません。

- ひとつの目的に必要な複数ディレクトリの変更は、影響範囲・Contract・必要なテスト・並行作業との競合を明記したうえで、機能単位のPRとして進めてよい。
- 無関係な「ついで修正」は混ぜない。共有Schemaの破壊的変更、安全性判断、検証を自己承認する変更は、別PRまたは明示的な検証ゲートで扱う。
- 実装と独立検証は同じ人が実行してもよいが、別経路の原本照合・明示的な人間判断を省略したり、架空の別レビュアー承認を記録したりしてはいけない。

---

## 3. Branch and Integration Policy

### 3.1 main is an integration branch

`main` は常に統合可能かつ動作確認済みの状態を保ちます。

- AI は `main` に直接 push しない。
- AI は `main` を直接変更しない。
- AI は `main` の PR を勝手に merge しない。
- `main` への最終 merge は **Merge Captain（統合担当者）** が行う。

Approve と Merge は別物です。
レビュー済みでも、依存関係・最新 main・CI・契約互換性を確認するまでは merge してはいけません。

### 3.2 Feature-first branches

新規作業は原則 **機能・改善課題ごとの短命ブランチ**（例: `feature/flood-comparison-flow`, `fix/source-version-gate`, `docs/three-axis-plan`）で進めます。必要な複数領域を横断できますが、PRには変更理由・影響ディレクトリ・Contractへの影響・検証範囲を記載します。

既存の `role/a-data` / `role/b-frontend` / `role/c-validation` / `role/d-pipeline` / `role/e-gis` と `feature/a-*` 等は、未完了作業を安全に継続するため **互換として維持** します。新規作業に利用を強制しません。role-scoped branchのScope Guardは従来どおり有効です。

前提PRがある場合は依存ブランチを用い、競合を避けて並行開発します。**統合したいタイミングで手を止め、mainへ入れて安全かを確認してから順番にmergeします。**

### 3.3 Dependent / stacked PRs

前提 PR が未マージでも後続作業は進めて構いません。

その場合は:

- 後続ブランチを前提ブランチから切る、または依存関係に合うfeature/既存role branchをbaseにする。
- PR 本文に `Depends on: #<PR番号>` を明記する。
- 前提が未解決の PR は原則 Draft または blocked 扱いにする。
- 前提 PR が main に入った後、後続 PR を最新 main に追従させて再テストする。

依存関係を無視して作成順に merge してはいけません。

### 3.4 Merge priority

Merge Captain は原則として次の優先度で判断します。

1. main を直す critical fix
2. 共通 Contract / Schema / CI / Infrastructure
3. 他 PR にデータや API を提供する provider
4. provider に依存する consumer
5. 独立した feature
6. docs / cleanup

「この PR を先に入れると何本の後続 PR が進められるか」を重視します。

### 3.5 Before final merge to main

main へ merge する直前に必ず:

1. 最新 main を取り込む。
2. conflict を解消する。
3. CI / tests を再実行する。
4. Contract 互換性を確認する。
5. 依頼範囲外の意図しない変更がないことと、変更した全領域のテストを確認する。
6. Merge Captain が merge 順を確定する。

AI は古い base のまま「以前テストが通った」という理由で merge を勧めてはいけません。

### 3.6 PR labels

Label の正本は `.github/labels.json` です。
GitHub 操作に不慣れなメンバーを案内するときは `.github/AI_GITHUB_GUIDE.md` も参照してください。

AI は PR ごとに適切な label を提案してください。

Area:

- `area: data`
- `area: frontend`
- `area: validation`
- `area: pipeline`
- `area: gis`
- `area: shared`

Change metadata:

- `depends-on`
- `contract-change`
- `breaking-change`
- `critical-fix`
- `docs-only`
- `ai-authored`

Merge state:

- `merge: blocked`
- `merge: needs-update`
- `merge: captain-review`
- `merge: ready`

`merge: ready` は Merge Captain の判断を表します。
AI は人間から明示的に依頼されていない限り、独断で `merge: ready` を設定・提案してはいけません。

前提 PR が未解決なら `depends-on` と `merge: blocked` を推奨します。
最新 base の取り込み・再テストが必要なら `merge: needs-update` を推奨します。
main 統合の最終確認待ちなら `merge: captain-review` を推奨します。


### 3.7 PR Creation Gate / Integration Readiness

AI は「実装が終わった」ことと「PRを統合候補として提出できる」ことを区別してください。

PR 作成前に最低限、以下を確認します。

1. `git status`
2. 現在 branch
3. PR の target/base branch
4. target/base branch と最新 `main` の差分
5. CI / tests の状態
6. 前提 PR / stacked PR の有無
7. Shared Contract / Schema / CI / Infrastructure の変更有無

#### Base freshness

作業ブランチ（既存role branchを含む）は常に main と同一である必要はありません。
ただし、main 側の変更が今回の検証・契約・統合に影響する場合は、古い base のまま統合候補にしてはいけません。

特に main 側で次が変更されている場合は影響を確認してください。

- `.github/workflows/**`
- shared Contract / Schema
- repository structure
- shared scripts
- `AGENTS.md` / `CONTRIBUTING.md`
- test infrastructure

影響する変更を取り込んでいない場合は `merge: needs-update` として扱い、target/base を更新してから tests / CI を再実行します。

#### CI gate

required check または今回の変更に必要な CI が `red` / `pending` の場合:

- merge を勧めない。
- 「Integration ready」「Merge ready」「実装完了ですべて確認済み」と表現しない。
- 原因が base 側の既知問題でも無視しない。
- 更新で解消できる場合は base を更新して再実行する。
- すぐ解消できない場合は Draft または `merge: blocked` / `merge: needs-update` として人間へ報告する。

#### Test result reporting

一部のテストだけが成功した場合に「tests passed」と総括してはいけません。
PR では最低限、以下を分けて記載してください。

- Passed
- Failed
- Not run
- Reason

#### Completion terminology

AI は以下を同じ「完了」と表現してはいけません。

- **Implementation complete**: コードや文書の実装が完了した。
- **PR created**: PR を作成した。
- **Integration ready**: base の鮮度・依存関係・必要 tests / CI を確認し、target branch へ統合可能な候補になった。
- **Merge ready**: Merge Captain が最終確認し、統合可能と判断した。

AI は Implementation complete / PR created の段階で Merge ready と扱ってはいけません。


### 3.8 Automated Scope Guard

role-scoped branch では、担当外ファイルの変更を CI で拒否します。

対象例:

- `feature/a-*`, `fix/a-*`, `role/a-data` → `data-research/**` のみ
- `feature/b-*`, `fix/b-*`, `role/b-frontend` → `frontend/**` のみ
- `feature/c-*`, `fix/c-*`, `role/c-validation` → `validation/**` のみ
- `feature/d-*`, `fix/d-*`, `role/d-pipeline` → `pipeline/**` のみ
- `feature/e-*`, `fix/e-*`, `role/e-gis` → `gis/**` のみ

例えば B の PR で `.github/workflows/**` や `pipeline/**` を変更すると Scope Guard は失敗します。

旧role-scopedブランチの制約は維持します。一方、**新しい機能単位の通常ブランチ**では、設計上必要な複数ディレクトリを同じPRに含められます。関係する全領域のテストを実施し、機能境界・独立検証・レビュー可能性を維持してください。

共有Contractの破壊的変更やCI/Infrastructureなど独立したリスクがある変更は、別PRと段階的移行を原則とします。必要なら `area: shared` を使用します。

Scope Guard を green にする目的で既存roleブランチの名前を偽装したり、guard自体を変更したりしてはいけません。

---

## 4. Disaster-data Safety Rules

HINANEX は防災データを扱います。
AI の推測による補完は、コード上の便利さより危険性が高いとみなします。

### Never invent disaster facts

以下を推測・補間・創作してはいけません。

- 緯度・経度
- 対応災害種別
- 避難所収容人数
- アクセシビリティ情報
- ハザード区分
- 更新日
- 公開日
- ライセンス
- 自治体の公開状況
- 公式データが示していない安全性・危険性

値が確認できない場合は、既存 Schema に従って `null` / UNKNOWN 等で保持してください。

### Absence of evidence is not evidence of absence

`NOT_FOUND` は:

> HINANEX の現在の取得経路ではデータを確認できなかった。

という意味です。

次の意味へ自動変換してはいけません。

> 自治体が公開していない。

アクセス制限、非機械可読、調査不足、URL変更等の可能性を区別してください。

### Preserve official meaning

- 公式のリスク区分・災害区分を独自ランクへ勝手に置き換えない。
- 不明なアイコン・列・コードを意味推測でマッピングしない。
- 説明できない変換を追加しない。
- Evidence と出典を追跡可能な形で保持する。

---

## 5. Evaluation Semantics Are Contractual

以下の意味は変更禁止です。

### Metric score

- `score = 0`: 評価を実施し、利用不能・要件未達と判断した。
- `score = null`: 未評価、情報不足、または判断不能。

0 と null を同一視してはいけません。

### Discovery

Discovery Status:

- `AVAILABLE`
- `PARTIAL`
- `NOT_MACHINE_READABLE`
- `ACCESS_RESTRICTED`
- `NOT_FOUND`
- `UNKNOWN`
- `NOT_APPLICABLE`

### Capability

Capability Status:

- `FULL`
- `DEGRADED`
- `BLOCKED`
- `UNKNOWN`
- `NOT_APPLICABLE`

Criticality は DataRequirement のグローバル属性ではありません。
**CapabilityDependency 上の文脈依存属性**として扱います。

### Gap

- `CONFIRMED_IMPROVEMENT`: 不足を確認済みの改善候補。
- `INVESTIGATION`: 存在・取得・評価が確定しておらず追加調査が必要。

調査不足を確認済み欠陥へ変換してはいけません。

---

## 6. Contract and Schema Compatibility

複数コンポーネントが利用する共有 Contract は API と同等に扱います。

AI は以下を勝手に変更してはいけません。

- RegionExport のトップレベル構造
- `requirement_code` の意味
- `capability_code` の意味
- null / 0 の意味
- status enum の意味
- Evidence の追跡関係

互換性に影響する変更では、PR に以下を明記してください。

- 何が変わるか
- 誰が影響を受けるか
- 後方互換性
- migration 手順
- schema version を上げる必要があるか

内部実装だけの変更で schema version を無意味に上げないでください。

### Breaking changes: Add → Migrate → Remove

破壊的変更を一度に行わず、原則:

1. 新フィールド / 新構造を追加
2. Consumer を移行
3. 移行完了を確認
4. 旧構造を削除

の順に進めます。

---

## 7. Pipeline and Evidence Rules

- 自治体固有処理は Adapter 内へ閉じ込める。
- Raw source は意味を改変しない。
- Normalization 時に出典との追跡可能性を失わない。
- 推測による geocoding や属性補完を自動導入しない。
- 取得先を非公式ソースへ勝手に置換しない。
- 公開元の HTML / CSV / Excel の意味が不明なら、人間へ確認する。
- User feedback が safety logic を自動変更する仕組みを作らない。

---

## 8. Scope Discipline

AI は依頼されていない大規模リファクタリングをしないでください。

避けるもの:

- 関係ない rename
- 全ファイル整形
- Framework の置換
- 既存 API の全面再設計
- 「より綺麗だから」という理由だけの大量変更
- 依頼に無関係なディレクトリのついで修正

必要な変更が大きくなる場合、実装前に理由・影響範囲・代替案を示してください。

---

## 9. Testing and Verification

変更した領域に対応するテストを実行してください。

D / pipeline の基本確認:

```powershell
cd pipeline
python -m unittest discover -s tests -v
python verify_d_mvp.py
```

Contract / Schema 変更時:

```powershell
cd pipeline
python generate_contract_schema.py
git diff -- contracts/region_export.schema.json
```

必要に応じて `python run_all_workflows.py` で実データ workflow を確認します。
外部サイトへアクセスするテストと、CI で実行する deterministic test は区別してください。

テストを実行できなかった場合、成功したと表現してはいけません。
未実行理由と未確認範囲を PR に記載してください。

---

## 10. Forbidden AI Actions

AI は明示的な人間の承認なしに次を行ってはいけません。

- `main` への直接 push
- PR の main への merge
- force push
- 共有履歴の rewrite
- 大量ファイル削除
- secrets / credentials / `.env` の commit
- Raw / generated runtime artifacts の無断 commit
- branch protection の解除
- CI を通すためだけの test 削除
- failing test の skip 化による問題隠蔽
- Disaster data の推測補完
- Schema compatibility を壊す silent change

---

## 11. Stop Conditions

以下の場合は自己判断で進めず、人間へ確認してください。

- 防災上の意味解釈が曖昧。
- 公式ソース同士が矛盾している。
- source column の意味が確定できない。
- Contract を破壊する可能性がある。
- schema version の扱いが不明。
- 既存テストと仕様書が矛盾する。
- 複数コンポーネントにまたがる共有Contract・防災上の意味解釈・独立検証の扱いについて必要な判断が未承認。
- main への merge 順序が複数 PR の依存関係により不明。
- データ欠損を「欠陥」と判定してよい根拠がない。

---

## 12. PR Requirements for AI-authored Changes

AI が変更を実装した PR では最低限、以下を記載してください。

- Summary: 何を変更したか
- Why: なぜ必要か
- Scope: 変更機能と影響ディレクトリ
- Depends on: 前提 PR（存在する場合）
- Contract impact: none / additive / breaking
- Tests: 実行したコマンドと結果
- Data assumptions: 推測した事実がないこと、または確認が必要な点
- Known limitations: 未解決事項

「実装完了」だけの報告は禁止です。

---

## 13. Final Principle

HINANEX では AI の開発速度よりも、

- 事実性
- 追跡可能性
- Contract の安定性
- 原本と評価結果の独立検証
- main の再現可能性

を優先します。

**分からない値を埋めるより null にする。**
**依存関係を無視して merge するより待つ。**
**大きく書き換えるより小さく安全に変更する。**

## 14. main Branch Protection and Required Checks

`main` は GitHub 側の branch protection でも保護します。

Required check:
- `test`

AI は main 統合前に以下を満たす必要があります。

- Pull Request 経由である。
- 最新 main を取り込んでいる。
- required check `test` が成功している。
- force push や protection 回避を提案しない。
- failing test を削除・skipして green に見せない。

Branch protection の設定手順と確認方法は `.github/MAIN_PROTECTION.md` を参照してください。

required check が red / pending の PR は `merge: ready` と扱ってはいけません。
