# HINANEX オーナー判断台帳 v0.1

- 作成日: 2026-11-20 JST
- 文書状態: **PROPOSED / OWNER_REVIEW_REQUIRED**（本書は提案・索引であり、未決事項を承認しない）
- 対象: 2027-02-09卒業制作MVPまでの運用・機能・根拠・公開・QA・統合の横断判断
- 参照時点: 2026-11-20（下記GitHub Issue/PRの読み取り照合と過去のオーナー指示に基づく初期整理）
- 最上位規則: [AGENTS.md](../../AGENTS.md)
- この文書の役割: **既存Issue・契約・レビュー・QA台帳の代わりではなく、オーナーの判断と依存関係を検索できる索引**
- 正本関係: 個別の一次資料・原本・契約・CI・Issueの実測情報は元資料が正本。ここに転記しても人間確認や一般公開の証拠にはならない

## 0. 利用上の禁止・前提

1. `INTEGRATED_MAIN`、`DEVICE_QA_PASSED`、`HUMAN_SOURCE_ACCEPTED`、`RELEASE_APPROVED`、`PUBLISHED`を別のゲートとして扱う。
2. `CONFIRMED`（記載事実の人間確認）と、実施設の安全・現在の開設・洪水適合・経路の通行可否を同一視しない。
3. 施設の同一性・災害種別・座標・開設・階数を推測して承認しない。UNKNOWN / UNVERIFIEDを維持する。
4. 本台帳の `PENDING` / `HOLD_EVIDENCE` / `DEFERRED` を、AIやPRのテストPASSだけで `ADOPTED_SCOPED` に変更しない。
5. mainへ直接pushしない。PRの最終統合は共同Merge Captainの判断（AGENTS.md）。一般公開・原本の人間受入はその判断と独立。
6. 下記は**2026-11-20時点のスナップショット**。各Issueの最新状態と矛盾した場合、元Issue・公式一次資料・AGENTS.mdを優先し、差分を明示して台帳を更新する。
7. 人間レビュー担当者の提出を、オーナー自身による最終利用許諾承認へ自動昇格しない。

## 1. 台帳のステータス定義

| 状態 | 意味 |
| --- | --- |
| `ADOPTED_SCOPED` | 既存Issue/仕様・オーナー指示で採用が確認でき、適用範囲を限定して記録済み |
| `PENDING_OWNER` | オーナーの判断待ち。選択肢はあるが採否記録なし |
| `HOLD_EVIDENCE` | 一次資料・人間レビュー・独立QA等が不足。承認不可 |
| `DEFERRED` | 後日に判断する運用が採用済み。公開/承認を省略しない |
| `CAPTAIN_REVIEW` | main統合の責任者判断。製品公開・人間原本承認とは別 |
| `REJECTED` | 対象範囲を明示して不採用。変更する場合は新たな根拠が必要 |
| `SUPERSEDED` | 後継判断で置換。旧判断は履歴として保持 |

## 2. 決定済み・既存の方針（再承認要求ではない）

| ID | 決定と適用範囲 | 状態 | 根拠・注意 |
| --- | --- | --- | --- |
| GOV-001 | 2027-02-09の限定MVPは、洪水の根拠・未確認表示 → 施設比較 → 本人選択というユーザー体験を重視する。実災害の安全推奨を製品目標としない | `ADOPTED_SCOPED`（方向性のみ） | [#305](https://github.com/1kz-ma1/HINANEX/issues/305)。[3軸ロードマップ](./HINANEX_THREE_AXIS_ROADMAP_2027-02-09.md)自体はPROPOSED。個別機能と公開範囲は未承認 |
| GOV-002 | 洪水体験はkouta、基盤・地域/災害拡張はオーナーの2トラック | `ADOPTED_SCOPED` | [#360](https://github.com/1kz-ma1/HINANEX/issues/360)（2026-11-11）。文書化PR [#361](https://github.com/1kz-ma1/HINANEX/pull/361)はDraftでmain未統合。A〜EのScope Guardは維持 |
| GOV-003 | 実装・自動テストを先行し、実機QAをまとめて実施。DeferredはDQA-IDと未実施内容を記録 | `ADOPTED_SCOPED` | [main運用仕様](./HINANEX_IMPLEMENTATION_FIRST_DEVICE_QA_20261113.md)、[#372](https://github.com/1kz-ma1/HINANEX/issues/372)（2026-11-13） |
| GOV-004 | GSI/F02/R0などの人間レビューは後日バッチへ集約。レビューを省略せず、技術開発と公開審査を分離 | `ADOPTED_SCOPED` | [#388](https://github.com/1kz-ma1/HINANEX/issues/388)（2026-11-16）。F02は鳥羽のレビューが2026-11-20に提出済みだがOwner採否待ち |
| GOV-005 | F09はP2を維持。保存しない非公開の独立Prototypeを例外的に実装対象とする | `ADOPTED_SCOPED` | [#423](https://github.com/1kz-ma1/HINANEX/issues/423)（2026-11-17）。配信除外・人間出典受入・一般公開は別ゲート |
| GOV-006 | F17は非公開の架空訓練Prototypeとしてコード統合。公開承認とは切り離す | `ADOPTED_SCOPED`（コード統合の事実） | [PR #437](https://github.com/1kz-ma1/HINANEX/pull/437)および[PR #438](https://github.com/1kz-ma1/HINANEX/pull/438)は2026-11-18時点mainへmerge済み。実機/配布承認は別 |

## 3. 未決・保留のオーナー判断

表の「次の判断」は採用案ではなく、決裁時に確認する問いである。期限はユーザーが明示していない限り捏造せず、「判断が必要になる条件（トリガー）」で管理する。

| ID | 優先 | 判断対象（必要な決裁） | 現在 | 主な根拠 | 次に必要な証拠・トリガー |
| --- | --- | --- | --- | --- | --- |
| OWN-F02-01 | P0 | **鳥羽のF02人間レビューを事実確認の証拠として受領する範囲**を確定する。一般公開許可とは独立 | `PENDING_OWNER` | [#366 提出コメント](https://github.com/1kz-ma1/HINANEX/issues/366#issuecomment-7027657052)、[#388](https://github.com/1kz-ma1/HINANEX/issues/388) | 提出済みのCONFIRMED/HOLD/NOT_RUNを確認し、受領範囲と残課題をIssueに明記 |
| OWN-F02-02 | P0 | **CSV固有の例外、第三者権利、PNGの複製/再配布可否**。必要に応じて自治体照会を判断 | `HOLD_EVIDENCE` | [#366](https://github.com/1kz-ma1/HINANEX/issues/366)、[PR #367](https://github.com/1kz-ma1/HINANEX/pull/367) | 権利主体・対象データ・対象用途ごとの公式根拠。根拠がない画像は再配布しない |
| OWN-F02-03 | P0 | F02の**出典、表更新日と取得日時の区別、加工、CCリンク、非公認/安全性非保証の文言と画面受入** | `HOLD_EVIDENCE` | [#366](https://github.com/1kz-ma1/HINANEX/issues/366)、[#355](https://github.com/1kz-ma1/HINANEX/issues/355) | 非公開画面資料、本人による視認・操作レビュー。現時点F02画面人間レビューNOT_RUN |
| OWN-DATA-01 | P0 | 江戸川区の異なる原本にある**施設同一性・敷地/入口・位置、洪水適合**の採否（行単位） | `HOLD_EVIDENCE` | [#134](https://github.com/1kz-ma1/HINANEX/issues/134)、[#141](https://github.com/1kz-ma1/HINANEX/issues/141)、[#268](https://github.com/1kz-ma1/HINANEX/issues/268) | 同時点の公式根拠・個別施設単位の人間C確認。名称/URL一致や距離で自動joinしない |
| OWN-DATA-02 | P0 | 新潟市ODS「災害種別_洪水」の記号を正規化・画面表示に使えるか | `HOLD_EVIDENCE` | [#48](https://github.com/1kz-ma1/HINANEX/issues/48) | 対象ODS列を定義する公式資料。確認までUNKNOWNを維持 |
| OWN-DATA-03 | P1 | GSI skhb02・2タイル×2災害4セルの**人間受入・表示/再配布の許容範囲** | `DEFERRED` + `HOLD_EVIDENCE` | [#388](https://github.com/1kz-ma1/HINANEX/issues/388)、[#378](https://github.com/1kz-ma1/HINANEX/issues/378)、[#389](https://github.com/1kz-ma1/HINANEX/issues/389) | 公式版・人間権利/意味レビュー・独立C証拠をセル別に。D技術4/4取得報告とC/人間受入は別 |
| OWN-DATA-04 | P1 | 3地域の原本更新・A/C受入後にRegionExportの再生成/採用を許可するか | `HOLD_EVIDENCE` | [#264](https://github.com/1kz-ma1/HINANEX/issues/264)、[#265](https://github.com/1kz-ma1/HINANEX/issues/265)、[#266](https://github.com/1kz-ma1/HINANEX/issues/266)、[#268](https://github.com/1kz-ma1/HINANEX/issues/268) | 版・原本SHA・原本間差異・独立C受入。古い件数を現在の固定仕様にしない |
| OWN-F05-01 | P0 | **F01→F02→F05の最小統合範囲**、合成モードと実CSVの接続境界、未確認時の代替体験 | `PENDING_OWNER` | [#362](https://github.com/1kz-ma1/HINANEX/issues/362)、[#305](https://github.com/1kz-ma1/HINANEX/issues/305)、[PR #371](https://github.com/1kz-ma1/HINANEX/pull/371) | F02権利/表示ゲート、合成体験の受入条件、Render配信ガード[#373](https://github.com/1kz-ma1/HINANEX/issues/373)。「本人選択」は安全推奨ではない |
| OWN-F07-01 | P0 | MVPの**参考経路を含めるか（GO/NO-GO）**。未達なら「参考経路は未提供」を許容するか | `PENDING_OWNER` + `HOLD_EVIDENCE` | [#358](https://github.com/1kz-ma1/HINANEX/issues/358) | 位置/入口、送信同意、ライセンス、実ブラウザ/実機と非安全保証の証拠。架空線Prototypeと現実経路は区別 |
| OWN-F03-01 | P1 | F03保存仕様の正式採用（地域1項目 vs 階情報込み、保存キー/Schema、180日ルール、自動復元 vs 明示読込） | `PENDING_OWNER` | [#356](https://github.com/1kz-ma1/HINANEX/issues/356)、[Draft PR #359](https://github.com/1kz-ma1/HINANEX/pull/359)、[Draft PR #311](https://github.com/1kz-ma1/HINANEX/pull/311) | プライバシー・同意・共用端末・削除・移行計画と実機受入。F05はF03を必須依存にしない |
| OWN-S0-01 | P1 | NORMAL/DRILLの合成状態モデルをB/E・F05へ接続する共有契約の採否 | `PENDING_OWNER` | [#375](https://github.com/1kz-ma1/HINANEX/issues/375) | 共同Contractレビュー。DRILLを現在の実災害と混同させない。独立Dテスト成功は製品採用ではない |
| OWN-F09-01 | P2 | F09非公開Prototypeと出典の受入、公開/展示への採用範囲 | `HOLD_EVIDENCE` | [#423](https://github.com/1kz-ma1/HINANEX/issues/423)、[PR #428](https://github.com/1kz-ma1/HINANEX/pull/428)、[PR #429](https://github.com/1kz-ma1/HINANEX/pull/429) | #428配信除外の先行統合/QA、出典利用条件と画面の人間確認。P2優先順位維持 |
| OWN-F04-01 | P2 | 架空洪水タイムラインS1/S2をMVP展示に採用するか、合成専用のまま保留するか | `PENDING_OWNER` | [PR #430](https://github.com/1kz-ma1/HINANEX/pull/430)、[PR #432](https://github.com/1kz-ma1/HINANEX/pull/432) | 本人の対象スコープ決定、非公開ガード、独立QA、S1→S2の依存と最新mainの確認。両PRは2026-11-20時点Draft |
| OWN-F13-01 | P1 | F13の根拠/未確認表示を現行F01へ統合・実機で受け入れる際の範囲 | `CAPTAIN_REVIEW` + `HOLD_EVIDENCE` | [PR #436](https://github.com/1kz-ma1/HINANEX/pull/436)、[#372](https://github.com/1kz-ma1/HINANEX/issues/372) | 現行main、F04との同一テストファイル差分、required test、実機QAを区別。CI合格だけでリリースしない |
| OWN-F17-01 | P1 | F17（架空訓練）の実機QA・発表採用・将来公開の範囲 | `HOLD_EVIDENCE` | [PR #437](https://github.com/1kz-ma1/HINANEX/pull/437)、[PR #438](https://github.com/1kz-ma1/HINANEX/pull/438)、[#372](https://github.com/1kz-ma1/HINANEX/issues/372) | #437/#438コードはmain統合済み。実機/人間受入と配布承認は別 |
| OWN-QA-01 | P0 | **次回実機QAの日時・担当・端末・対象フローの確定** | `PENDING_OWNER` | [#372](https://github.com/1kz-ma1/HINANEX/issues/372)、[実装先行QA運用仕様](./HINANEX_IMPLEMENTATION_FIRST_DEVICE_QA_20261113.md) | main文書は12/06等を暫定枠として記載。参加者・時間・端末は未確定。別途11/27実機準備案がある場合は正式予定と区別して調整 |
| OWN-REL-01 | P0 | 実データ・GIS・経路・F02/F03/F04/F09/F13/F17の**公開/発表用対象範囲**とGO/NO-GO | `HOLD_EVIDENCE` | [#89](https://github.com/1kz-ma1/HINANEX/issues/89)、[#268](https://github.com/1kz-ma1/HINANEX/issues/268)、[#366](https://github.com/1kz-ma1/HINANEX/issues/366)、[#388](https://github.com/1kz-ma1/HINANEX/issues/388) | 機能別出典、Schema、CI、実機、ライセンス、人間承認。main統合済みであっても公開しない |

## 4. 最初にオーナーが処理する順番（提案・未承認）

1. **OWN-F02-01:** 鳥羽レビューの受領範囲を確定し、[#366](https://github.com/1kz-ma1/HINANEX/issues/366)と[#388](https://github.com/1kz-ma1/HINANEX/issues/388)の未解決事項を保つ。
2. **OWN-F05-01 / OWN-F07-01:** 2027-02-09の体験を、実データや実経路が未承認でも成立する合成・根拠付き比較としてどこまで採用するか。
3. **OWN-QA-01:** 次回の人間実機QAを具体的な端末・担当・フローで固定する。
4. **OWN-F02-02/03 + OWN-DATA-01:** F02の本番公開判断に必要な証拠収集・画面レビューを委任する。
5. その後にF03保存、F04/F09/F13/F17、GSI/R0、地域拡張の採否を、関係する期限・依存が来たときに判断する。

この順番はオーナー採用前の提案であり、既存Issueの優先度を自動変更しない。

## 5. 1件を判断したら残す決裁記録（追記テンプレート）

```markdown
### DECISION-YYYYMMDD-NNN
- 台帳ID:
- 決定者（実際のGitHubアカウント）:
- 決定日時（JST / UTC）:
- 対象Issue / PR / 原本・版・SHA:
- 問い:
- 選択肢:
- 決定: ADOPTED_SCOPED / REJECTED / HOLD_EVIDENCE / DEFERRED
- 対象範囲（地域・災害・機能・配信環境・対象行）:
- 根拠（公式URL・レビュー・CI・実機）:
- 未確認事項 / 残存リスク:
- 実装・仕様変更の対象ファイルと必要なPR:
- 別途必要なゲート（人間出典、C、実機、公開、Merge Captain）:
- 見直し条件 / 次回確認時点:
- 通知先・引継ぎ先:
```

AIによるおすすめは「決定」ではない。本人の採用操作・明示記録がある場合のみ決定ステータスに反映する。

## 6. 更新運用と既存台帳の関係

- 新たなIssue/PRで「owner decision pending」「HOLD」「publication NO-GO」「human approval required」が出たら、重複IDを避けて本書へ1件追加。
- 既存IDの状況が変化した場合は同じ行を更新し、**決裁記録を追記で残す**。過去の結論を黙って上書きしない。
- C/Aレビューの詳細は[#388](https://github.com/1kz-ma1/HINANEX/issues/388)と個別Issue、実機QAは[#372](https://github.com/1kz-ma1/HINANEX/issues/372)を引き続き正本とする。
- 仕様変更があれば、対象の機能仕様・Contract・テストと、台帳の「決定内容・根拠・対象範囲・状態」を一緒に更新するか判断する。
- 変更の反映はdocs-only PRでレビューし、Merge Captainによるmain統合が行われるまで本書は**提案**のまま。
- 月日・件数・PASSを転記する場合は観測元のSHA/時刻/ソースを示す。確認していない範囲を「承認済み」にしない。

## 7. この文書で完了しないこと

F02人間レビューのオーナー受領、CSV個別の権利許諾、施設・経路安全性、災害別指定、端末実機QA、公開範囲・部署の正式承認、Draft PRのマージ、Render等の一般公開。本書は**判断の取りこぼし防止のための文書**である。


## 8. 2026-11-24 Owner決裁追補（現行判断の索引）

2026-11-24 JST、Owner本人のチャットでの明示採用を司令塔AIが関連Issue/PRへ代理記録。元の11-20スナップショットを履歴として保持し、以下の限定範囲については本追補を現行判断とする。本PR自体はDraft・未統合であり、公開や正式Contract採用の証拠ではない。

| 決裁ID | 台帳IDとの対応 | 採用範囲 | 残るHOLD・未決 | 個別決裁記録 |
| --- | --- | --- | --- | --- |
| DECISION-20261124-001 | OWN-F09-01 / CAPTAIN_REVIEW | #428非公開ガードのみ、Owner条件付き正式マージ許可 | 実効保護詳細・Render自動配信影響の確認、正式操作、#429別審査、F09公開/展示/出典受入 | [#428](https://github.com/1kz-ma1/HINANEX/pull/428#issuecomment-7120365938) |
| DECISION-20261124-002 | OWN-F05-01 / OWN-F07-01 | MJ-D01〜07限定方針、MJ-01固定架空表示Fixtureの非公開UI実装 | 提供方式、S1正式表示/操作契約、D/B接続、実施設結合、実経路、main統合、公開 | [#362](https://github.com/1kz-ma1/HINANEX/issues/362#issuecomment-7120366611) |
| DECISION-20261124-003 | OWN-S0-01 | D03-03案Bを合成訓練限定の設計第一候補、保証詳細設計のみ | D/B/C個別承認、Lease/時計/処理遅延/信頼確立/N-11、正式Contract、製品実装・公開 | [#386](https://github.com/1kz-ma1/HINANEX/pull/386#issuecomment-7120367201) |
| DECISION-20261124-004 | OWN-QA-01 | 11/27想定QA-0の隔離環境Preflight準備 | 日時・参加者・端末・実機操作・通信許可、実機受入、12/6候補QA-1 | [#372](https://github.com/1kz-ma1/HINANEX/issues/372#issuecomment-7120367909) |

### 決裁の適用境界
- 001: #428固定HEAD `c74c21b1152d429ef41dbc21a05cf7c3869fc05b`、main `f13ab2035c51cde0084d1463036f3148ff1b8ecc`、[exact-HEAD CI #45313165095](https://github.com/1kz-ma1/HINANEX/actions/runs/45313165095) SUCCESS。技術GOを維持するが、保護API 403・Render Workspace未選択のため実行HOLD。#371公開ガード是正と#429再準備は#428 main統合の独立確認後。#371の[再監査HOLD](https://github.com/1kz-ma1/HINANEX/pull/371#issuecomment-7119963653)を維持。
- 002: 本人選択でMVP完了、J02〜05単一画面、公式/合成の完全分離、既存B1/B2/S0/S1再利用、S1表示と操作契約分離、S1選択正本は設計候補、参考経路を必須外とする。MJ-01だけ別Draft PRで実装・検証可能。新規資材の非公開保証を統合前に独立Shared PRで確認。MJ-D08と実接続、MJ-02以降の実装は未承認。
- 003: 制御可能な変更の論理失効バリア、制御不能障害に対する条件付きShort Lease、復帰時全面再検証。停止中の物理画面消去や有限残存時間は保証不能。14キーSchema・既存#386/#387を維持し、正式採用は合同承認後の別決裁。
- 004: 11/27は想定日であり確定日ではない。固定候補・合成Fixture・全35項目操作票・loopback接続成立性・F13隔離キット・証拠収集の準備。実機試験はNOT_RUN、実行権限HOLD。

### 司令塔の運用
Ownerは技術統合判断を司令塔に委任した。司令塔のGO/HOLDと人間Captainの正式決裁・GitHub操作を区別し、現行AGENTS.md/MERGE_CAPTAINS.mdを維持する。原本・権利・安全・公開の人間承認を代行しない。今回の4件以外の未決項目は従来の状態を維持する。
