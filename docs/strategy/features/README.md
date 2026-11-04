# HINANEX 機能別仕様書と開発優先順位（設計索引）

- 初稿: 2026-10-30
- 状態: **PROPOSED / DESIGN-ONLY**。候補の登録は実装着手・本番公開・公的データの受入承認を意味しない。
- 方針: **災害情報・避難施設・事前準備・時系列シミュレーションは独立して完成させ、最後に必要な連携だけを設計する。** 現在の比較UIを完成形に固定しない。
- 学内目標: 2027-02-09の限定洪水MVP。学校でのHINANEX開発と学校外のAP学習を両立するためWIPを絞る。

## まず読む：優先順位マスター

**[FEATURE_PRIORITY_MASTER.md — F01〜F19のP0〜P3、着手ゲート、3名のWIP上限、アイデア控え](FEATURE_PRIORITY_MASTER.md)**

新機能を思いついても、最初はマスターの `ICEBOX` に1行追加するだけ。実装・仕様の拡張・担当依頼は、既存P0との交換コスト・安全/権利の確認後に決める。

## 仕様書一覧（F01〜F19、全19機能）

| ID | 仕様書 | 主な価値と扱い |
| --- | --- | --- |
| F01 | [災害情報・ハザード閲覧](01_HAZARD_INFORMATION.md) | 洪水単独マップ（P0）、地震/津波は後段 |
| F02 | [避難施設の探索・詳細](02_SHELTER_REFERENCE.md) | 公式掲載・不明を独立閲覧（P0）、旧比較UIに縛られない |
| F03 | [事前準備・簡易アクセス](03_PRE_EVENT_PREPARATION.md) | 学校の班員向け独立試作候補（P1） |
| F04 | [浸水の時系列再生](04_FLOOD_TIMELINE.md) | 浸水ナビAPIの公式仕様調査（P1）、実装判断は後 |
| F05 | [最終統合ジャーニー](05_INTEGRATED_JOURNEY.md) | 独立機能の最小接続（P0の後段） |
| F06 | [公式警報・避難情報](06_OFFICIAL_ALERTS.md) | 公的原本リンクから開始（P1/P3） |
| F07 | [参考経路・移動手段](07_REFERENCE_ROUTE.md) | ゲート要件を定義（P0）、位置承認後に実連携 |
| F08 | [オフライン閲覧](08_OFFLINE_MODE.md) | 保存済み出典の失効/通信断表示（P2） |
| F09 | [備蓄チェックリスト](09_PREPAREDNESS_CHECKLIST.md) | 平時の備えを確認（P2） |
| F10 | [家族・知人の連絡計画](10_FAMILY_CONTACT.md) | 個人データ無しの手順案内から（P2/P3） |
| F11 | [アクセシビリティ・言語](11_ACCESSIBILITY_I18N.md) | P0の基礎品質、多言語は後段 |
| F12 | [よくいる地域の切替](12_FAVORITE_PLACES.md) | 手動地域切替を便利に、精密位置は慎重に（P1/P2） |
| F13 | [出典・検証状態の可視化](13_DATA_STATUS_UI.md) | 未確認・通信失敗の区別（P0） |
| F14 | [広域データと対応範囲](14_REGIONAL_DATA_COVERAGE.md) | 情報のない地域を誤解させない広域化（P2） |
| F15 | [不足情報の招待制募集](15_CONTROLLED_CONTRIBUTION.md) | サーバー認可/審査が整うまで保留（P3） |
| F16 | [避難後の公的支援](16_POST_DISASTER_SUPPORT.md) | 給水・物資・制度の公式案内（P2/P3） |
| F17 | [平時の練習・訓練](17_TRAINING_DRILL.md) | 合成データで操作を練習（P2） |
| F18 | [避難施設の開設状況](18_SHELTER_OPERATIONS.md) | 公式現況・更新保証が必要（P3） |
| F19 | [運営審査・公開・撤回](19_OPERATIONS_REVIEW.md) | まず人間/文書の手動運用、動的UIはP3 |

## 共通ルールとテンプレート

- [DATA_STATES_AND_GATES.md](DATA_STATES_AND_GATES.md)：情報の出典、版、確認状態、表示許可と安全の境界。
- [FEATURE_TEMPLATE.md](FEATURE_TEMPLATE.md)：今後の機能仕様・1スライス作業票の雛形。
- **正本優先順位**：`AGENTS.md`（root/領域別）→既存D Contract/C検証規則→機能仕様→Issue/PR。文書間で矛盾したら実装前に人間確認する。

## 開発時に使う運用

1. マスターで `P0/P1/P2/P3` と作業状態・依存・WIP枠を確認し、アクティブなスライス1件を選ぶ。
2. 対応するF仕様を読み、現行main、既存コード/テスト、資料/ライセンスを確認する。**FUTURE設計を現行機能として扱わない**。
3. 自分の担当範囲だけの小PRで成功/UNKNOWN/通信失敗を検証する。C人間レビュー/公開承認はCIと別。
4. 実装で仕様差分が出たら、コードに合わせて既存契約を黙って上書きせず、仕様の改訂提案とマスターの履歴を同じPRで整理する。
5. 新しい発想はICEBOXで保管し、現在のP0作業に割り込ませない。担当を決めただけで実際の作業開始/本番統合とは扱わない。

## 外部の正本・関連バックログ

- [root AGENTS](../../../AGENTS.md) / [3軸ロードマップ](../HINANEX_THREE_AXIS_ROADMAP_2027-02-09.md) / [体験先行方針 Draft #344](https://github.com/1kz-ma1/HINANEX/pull/344)
- [D洪水Scenario Contract](../../../pipeline/docs/FLOOD_SCENARIO_CONTRACT.md) / [Cレビュー学習ループ](../../../validation/docs/REUSABLE_REVIEW_EVIDENCE_LEARNING_LOOP_20261027.md)
- [MVPの参考候補の計画 #301](https://github.com/1kz-ma1/HINANEX/issues/301) / [広域化 #343](https://github.com/1kz-ma1/HINANEX/issues/343) / [将来の情報募集 #342](https://github.com/1kz-ma1/HINANEX/issues/342)

**本ディレクトリは利用者体験と優先順位の提案資料。RegionExport Schema・災害時安全判断・人間審査・GIS公開ゲートは変更しない。**
