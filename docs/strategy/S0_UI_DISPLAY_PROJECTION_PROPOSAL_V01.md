# S0 → UI 安全表示境界 Contract 提案 v0.1

**状態: DESIGN PROPOSAL / NOT ADOPTED / REVIEW ONLY（2026-11-16）**

- 提案の目的：内部S0（main統合 PR #376）から、UIが誤解せず利用できる**合成訓練の表示専用スナップショット候補**を定義する。
- 参照：S0 `pipeline/docs/DRILL_SESSION_S0_20261113.md`、C独立確認 `validation/docs/S0_REAL_REDUCER_C_REPLAY_V01.md`（PR #384 統合済み）、計画Issue #305、F05 Draft #371、F05予定Issue #362、QA #372、公開ゲート #366。
- 本書はB/D/Eへの採用・運用API追加・公式資料の利用許諾・一般公開・Render配信・実災害対応の承認ではない。レビュー対象の**草案**。
- 契約候補は `docs/strategy/S0_UI_DISPLAY_PROJECTION_DRAFT_V01.schema.json`。既存 `pipeline/contracts/region_export.schema.json` 等は変更しない。

## 1. 現在の分離と提案

**既存:** Dの `Session / reduce_session / safe_view` はPythonの内部合成状態。Cは合成イベントから実出力を独立検証する。B Draft F05は本人の地域選択 + loopback originでF02ローカル導線を出すだけで、S0 stateもUIモードも読み込まない。Eはハザード表示、F02は公式根拠付き掲載**記録**でありS0 fixtureではない。

**提案（未実装）:** D側が渡すなら、公開状態の `safe_view(state, now)` を唯一の意味ソースとし、明示時刻 `now` と現在の合成fixtureの `observed_at/expires_at` から**表示用projection**を一方向に作る。Bは読み取り専用で、契約の意味・期限・文言を**検証してから**表示する。UIから `Session` や `Event` を直接作成する契約／永続化は別レビューとする。Cが参照実装・テストを行ってもD→Bの製品APIを実装済みとは見なさない。

## 2. データモデル（候補、全キー必須、追加キー禁止）

| キー | 値 / 根拠 | 承認前の意味 |
|---|---|---|
| `schema_id` | 固定 `hinanex.s0.ui_display_projection.review.v0.1` | プロトタイプ用草案の識別子。production Contract番号ではない |
| `review_only` / `synthetic_only` | どちらも厳密に `true` | 正式採用ではなく、合成専用 |
| `mode` | `NORMAL / DRILL` (`safe_view`) | NORMAL は実災害の有無/速報確認の証拠ではない |
| `generation` | S0整数世代（0以上） | **同一インメモリセッション**での旧イベント拒否補助。グローバル一意IDではない |
| `selected_region` | 5桁地域コードまたは `null` | 本人の選択状態。地図・施設やF05の自動地域選択へは渡さない |
| `fixture_id` / `hazard` | DRILL時のみS0合成fixture由来、NORMALは `null` | 現在発生中の災害や正式指定ではない |
| `source_authorization` | DRILL `SYNTHETIC_TEST_ONLY`、NORMAL `null` | 公式資料の利用権限ではない |
| `notice` | S0の `NORMAL_NOTICE / DRILL_NOTICE` **完全一致** | DRILL時に恒常表示。HTMLではなく textContent |
| `live_data_verified` | 厳密に `false` | LIVE受信・警報・開設済み・安全等を証明しない |
| `issued_at` | 投影時の明示TZ付き時刻 | 画面が鮮度確認するための時点 |
| `observed_at` / `expires_at` | DRILL時のみS0 fixture由来、NORMALは `null` | `observed_at <= issued_at < expires_at`。期限終端は**排他的** |

**意図的に除外:** `preferred_region`（同意済みメモリ設定をUI配布しない）、氏名/住所/GPS/緯度経度、施設ID・災害適合・開設・安全・収容/ペット等、経路URL、外部通信先、認可情報の正式許諾ID、LIVEステータス。

## 3. fail-closed表示規則（候補）

1. 入力は同一D表示コントローラからの**新規スナップショットのみ**。任意のURLクエリ、localStorage、ファイル保存、別画面や別タブからの復元をしない。今回はクロスページ連動を設計/実装しない。
2. Consumerはschema/key型/条件を厳密検証。未知キーや足りないキー、未知enum、認証済みと偽るLIVE、受入済み安全値、DRILLの訓練文言欠落は**拒否**。
3. 訓練表示なら有効なS0由来の地域・fixture・hazard・出典区分と時点の対応を要求。発行時点、描画時点の**双方で**期限内（`observed_at <= issued_at <= render_at < expires_at`）。発行時点が未来/時計不整合なら拒否。期限切れで自動的に訓練ラベルを取り下げ、旧fixtureを再表示しない。必要な再取得に失敗したら「確認できません」を表示し、正常/最新の実災害情報と称さない。
4. 同一のインメモリコントローラが渡した`active_generation`とprojectionの`generation`が厳密一致。地域変更・停止・失敗・リセット・コンポーネント再mountでは旧projectionを破棄。**世代番号だけでは新Session/タブを跨ぐ一意性を保証しない**ため、横断利用を禁止する。
5. NORMALはfixture/hazard/source/time windowがすべて`null`、かつ`NORMAL_NOTICE`完全一致。NORMALだからといって実災害・開設状況を確認済みと表示しない。
6. UIの訓練ラベルは既存F01洪水ハザードラスタやF02実施設の法的承認・所在を置換しない。F05のリンク条件（本人選択地域 + loopback）を緩めない。施設の自動結合・経路・推測の禁止を保持する。
7. 将来のB画面統合では固定バナー/ARIA/live読み上げ/狭幅/再描画/キーボード/期限境界と発火イベント後の非同期更新を独立E2Eで確認する。**Device QA: DEFERRED/BLOCKING** はUI変更時に #372で改めて判定し、本仕様のdocs-only検証はNOT_REQUIRED。

## 4. 採用前にB/D/Cで決める事項（未確定）

- **プロバイダの実装場所:** S0はPython内部。静的frontendのJavaScriptが`Session`を直接importすることはできない。Python→UIの搬送方式（local-only bridge、ビルド時合成preview、API）と**非配信/公開境界**を事前に共同決定する。
- **各画面のセッションID/破棄規則:** generationは同一state内のみ有効。ページ横断/端末保存を採用するなら別のsession instance識別子と失効時刻・取得元の完全なライフサイクル契約を設計し、Cで再検証する。
- **権利/出典/施設安全:** このprojectionはS0合成データ専用で公式ソースを混ぜない。#366、F02/F05の非公開及び公開監査ゲートとは独立。
- **kouta側F05との順序:** PR #371がDraft/公開不可の間、Bが新モードを正式に採用したものとはしない。F05の既存リンクを自動変更しない。共同設計レビュー後に**B専用の別PR**を作る。
- **E/D/Cの責務:** Dが正規表示用projectionを生成、Cが出力/原本/fixtureを独立検査、Bは検証済みスナップショットを描画。Eの既存地図へ波及させる場合はE別PR。

## 5. 検証/統合の段階

1. **この共有docs-only提案PR**: Markdown仕様 + candidate JSON Schemaのみ。Schema既存版、UI、D、Cの振る舞い変更なし。共有採用は未承認。
2. **C独立Draft PR**: mainに存在するS0実コードからの固定合成projectionを検証し、未知キー/失効/旧generation/出典偽装/LIVE偽装/バナー欠落を拒否。docs PRに依存する場合はstackし、required CIまで確認。
3. **共同レビュー:** オーナー(D/C)・kouta(B) が上の未確定点を解決してから、運搬方式/正式Contract/テスト範囲を採用するか決定する。現行本番互換は不変更、正式Schema version増分なし、移行手順なし。
4. **後続UI B PR:** 本人が明示操作する合成画面だけ。新たなUIの実Chrome/E2E/端末QA/Render排除/公開HOLDをゲート化。**本PRで実UI未実装**。

**公表可否：NO-GO。MVPデモでの使用可否：別判定。**
