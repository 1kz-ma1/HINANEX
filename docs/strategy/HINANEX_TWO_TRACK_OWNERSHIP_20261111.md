# HINANEX 2トラック開発運用・責任分担仕様（2026-11-11）

- **決定者:** オーナー（2026-11-11の会話で方針決定）
- **目的:** 2027-02-09の限定洪水MVPと、その後の地域・災害拡張を並行して進める
- **状態:** OWNER DECISION / DOCS PR PENDING MAIN INTEGRATION
- **チーム共有・引継ぎの入口:** [Issue #360](https://github.com/1kz-ma1/HINANEX/issues/360)
- **適用:** 今後の作業提案・割当・Issue起票・レビュー・進捗報告
- **非適用:** 既存PRの担当・ブランチの自動移管、既存実装の本番承認、データ安全/座標/経路の自動承認

> 本書は**人の成果責任**を定める運用仕様。A〜Eは既存の**技術領域とディレクトリ境界**であり、人に固定割当する名称ではない。mainの[AGENTS.md](../../AGENTS.md)を常に優先し、未統合の[#282](https://github.com/1kz-ma1/HINANEX/pull/282)を統合済みルールと解釈しない。

## 1. 最上位目標と2つの開発トラック

2027-02-09の対象は、まず**限られた1地域×洪水**の理解可能な体験。地域拡大や他災害への対応を並行研究できるが、未承認情報を使って洪水体験を無理に「完成」にしない。

| トラック | 主責任者 | 成果責任（何を完成させるか） | 担当例（固定の機能表ではない） |
|---|---|---|---|
| **Flood Experience / 洪水体験の完成（高さ）** | **kouta** | 洪水の情報確認→施設の根拠/未確認を見た条件抽出・比較→利用者自身の選択までの一連の画面・動作を、実ブラウザで説明可能な形に仕上げる | F01/F02/F05、必要なF03、操作性・アクセシビリティ、F07のGO/NO-GOに応じた代替案 |
| **Platform & Coverage / 基盤・対応拡張（横・縦）** | **オーナー** | Source→検証→正規化→RegionExport→Consumerの再現性と契約を強化し、新しい地域や災害種別で安全に再利用できるようにする | 公式原本・Evidence・C独立検証・D/Schema・RegionExport、地域×災害の追加検証、位置照合と承認ゲート |

### 1.1 Flood Experience の対象と非対象

- 目標は「利用者が洪水の情報を理解し、施設を根拠付きで確認し、自分で選択できる**完成した小さな体験**」。新規UIの数を成果指標にしない。
- 現状のF01の一部・F02合成Prototypeはmain統合済み。F02実RegionExport Consumer [#357](https://github.com/1kz-ma1/HINANEX/pull/357)、F03保存QA [#359](https://github.com/1kz-ma1/HINANEX/pull/359) は**Draft**。CI PASSや検収を正式公開・採用と区別する。
- 選択先が災害時に**安全／開設中／通行可能**であると断定しない。施設の同一性・適合・位置/入口が未承認ならUNKNOWN/UNVERIFIEDを保持する。
- 参考経路は [#358](https://github.com/1kz-ma1/HINANEX/issues/358) の成立条件審査後。未成立なら「参考経路は未提供」のNO-GO体験を完成させる。危険な推測でMVPを満たさない。
- 実データ受入とUIの操作品質は**別々のゲート**。合成fixtureで動作が成功しても本番安全性を保証しない。

### 1.2 Platform & Coverage の対象と非対象

- Source/Evidence・版/時点・ライセンス・原本hashから出力/画面への追跡、異常系のfail-closed、Schema後方互換を維持/改善する。
- 地域と災害種別の拡張は、**個別の公式原本・意味・C検証・人間承認**をゲートにする。対応数やデータ件数の増加を公式受入件数と混同しない。
- 公式記号や施設名の一致を適合・同一施設・入口位置へ推測変換しない。ABR/GSI派生候補は正式位置として採用しない。
- Flood Experience側の実装を不必要に止めず、データ未承認でも進められる合成/読み取り専用の小スライスは独立に進める。
- 第二地域・第二災害の探索結果をmain/公開に反映するかは、元データの検証結果を踏まえ個別判断する。

## 2. 担当の境界と共同判断

**担当をUI/バックエンドやA〜Eで切らない。変更理由でトラックを決める。**

1. 洪水体験を良くするための実装/UX改善 → **kouta主導**。基盤側の変更が必要ならオーナーへ依存を提示する。
2. 多地域・多災害に再利用するデータ/検証/契約の改善 → **オーナー主導**。表示契約/UIが変わるならkoutaと確認する。
3. Shared Contract/Schemaの変更、適合/安全の意味の採否、位置・経路の公開権限、個人情報、統合タイミング → **共同レビューの対象**。最終製品/merge/公開判断はオーナー。
4. **班員S**：既存の公開一次資料・API調査の独立支援担当を継続。今回の変更だけで開発範囲・権限を拡大しない。
5. **司令塔**：仕様・Issue/PR・CI/エビデンスの状態を横断管理し、依存を可視化して判断材料を提出する。AIが人間の承認を代行しない。

技術ファイルの変更はroot/配下のAGENTS.md、Scope Guard、必要な独立レビューに従う。異なるディレクトリを跨ぐ必要がある場合、必要な契約変更・独立PRを切り分け、既存ガードを回避しない。

## 3. 運用手順

- **1人1active WIPを原則**とする。次のスライスは各担当が提案し、オーナーが優先順位と担当・前提を確認。作業がなければ待機も可能。
- 作業Issueには **Goal / Scope / Owner / Dependencies / Contract impact / Acceptance / Tests / Evidence / Safety constraints / Not done** を最低限記入する。
- PRの結果報告は **Passed / Failed / Not run / Reason** と、**Implementation Complete / Integration Ready / Merge Ready / Published** の状態を分ける。
- 前提が未解決のPRはDraft/blocked、最新mainとCIの再検証を通した後にMerge Captainが統合を判断する。main直接push・自動mergeは禁止。
- 体験に必要なデータがない場合、koutaは必要項目と失敗時UXをIssueに記録し、オーナーがSource/Contract/provider側の不足を受ける。データの安全ゲートは維持する。
- 対応範囲を増やしても、既存洪水体験の回帰テストと説明可能性が損なわれないことを確認する。

## 4. 2026-11-11時点の引継ぎ候補（固定割当ではない）

| トラック | 次の検討候補 | 判定・留保 |
|---|---|---|
| kouta | F02実データConsumer [Issue #355](https://github.com/1kz-ma1/HINANEX/issues/355) / [PR #357](https://github.com/1kz-ma1/HINANEX/pull/357) の受入ゲート整理 → F01/F02の小さな体験結合へ | 既存作業中PRのコードを勝手に引き取らず、最新HEAD/担当/未実行テストを確認する |
| kouta | F03の検証完了 [Issue #356](https://github.com/1kz-ma1/HINANEX/issues/356) / [PR #359](https://github.com/1kz-ma1/HINANEX/pull/359) | 独立QA検収と、製品保存契約の採用・統合は別 |
| オーナー | 原本/検証/RegionExportの再現・承認ゲート [Issue #268](https://github.com/1kz-ma1/HINANEX/issues/268) / [#305](https://github.com/1kz-ma1/HINANEX/issues/305) | 追加地域/災害の開始スライスは別Issueで確定 |
| 両者 | F05の必要最小のデータ受け渡しと、F07 [#358](https://github.com/1kz-ma1/HINANEX/issues/358)の経路GO/NO-GO | 未承認の経路を一般向けに表示しない |

## 5. 既存文書・未統合PRとの関係

- 3軸の優先方向と2/9の達成基準： [HINANEX 3軸ロードマップ](HINANEX_THREE_AXIS_ROADMAP_2027-02-09.md)
- 安全・CI・branch・Contractの最上位ルール： [AGENTS.md](../../AGENTS.md)
- [#282](https://github.com/1kz-ma1/HINANEX/pull/282)：A〜E固定職掌からの移行案（Draft、AGENTS/CONTRIBUTING変更は未反映）。**本書はその先行mergeを前提とせず、現在の制限と両立する責任の決め方のみを定義する。**
- [#344](https://github.com/1kz-ma1/HINANEX/pull/344)：利用体験先行の戦略変更案（Draft）。本書を根拠に既存PRを無断統合しない。
- [#346](https://github.com/1kz-ma1/HINANEX/pull/346)：F01〜F19の個別仕様・優先順位表（Draft、オーナー採用待ち）。各担当の**目標責任**と機能の**優先順位**は別概念。

**Change control:** 今回の変更は人の責任分担を明文化するdocs-only作業。コード・共有Schema・公式データ・テスト・デプロイ・Safety approvalの変更は一切含まない。main統合はPRのレビュー/required `test`確認後にオーナーが判断する。
