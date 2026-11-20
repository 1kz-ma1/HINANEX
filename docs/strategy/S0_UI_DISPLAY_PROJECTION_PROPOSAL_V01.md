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


### 3.1 D-03 実行時同一性・失効境界（未採用設計案）

**状態：D03_DESIGN_ACCEPTED_SCOPED / CONTRACT_ADOPTION_HOLD / IMPLEMENTATION_HOLD**

本節は第3節のfail-closed規則を実行時の責務として補足する**未採用設計案**である。既存13フィールドprojection、S0 `Session/reduce_session/safe_view`、RegionExport、F05を変更しない。新たな正式Session ID、bridge、transport API、製品Contractの採用ではない。

#### 3.1.1 適用範囲とcontroller identity

- 初期適用範囲は**単一画面・単一インメモリcontroller・合成fixture・B read-only**に限定する。別画面/タブへの伝搬、保存、復元、公式データ連携、一般公開は対象外。
- Dは生存中controllerへ紐付く信頼済み一時bindingを所有し、破棄・再生成時に旧bindingを失効させる。identityは13フィールドへ追加せず、URL・localStorage・ファイルへ保存しない。
- `generation`は同一S0 controller内の世代番号であり、controller間で一意とは限らない。**別controllerが同一generationを返した場合でも必ず拒否**する。
- Bが受け取ったpayload自身をcontroller同一性の証明に使わず、信頼された実行時bindingとDの現在generationを独立に照合する。binding方式・認証・搬送は未決。

#### 3.1.2 request_sequence・display_epoch

- Bは表示要求ごとの`request_sequence`と、binding変更・状態変更・画面破棄で更新する`display_epoch`を内部管理する。両者ともprojectionのフィールドではない。
- 応答受理は、現在binding一致、現在display_epoch一致、**最新**request_sequence一致、D現在generationとprojectionのgeneration一致、Schema・意味・時刻・期限検証の成功をすべて必要とする。DOM反映直前にもコンテキストを再確認する。
- R1の後にR2を発行した場合、R1の遅延成功を採用しない。R2が失敗してもR1にフォールバックしない。abortだけを安全上の根拠にせず、旧応答を到着時に拒否する。
- Dの状態変更がBの旧表示を無効化できない経路は認めない。無効化と状態変更の順序・通知喪失時の挙動は合同レビューで確定する。

#### 3.1.3 trusted issuance・render expiry

- Dは現在のstateと明示TZ付き時刻から`safe_view(state, now)`を唯一の意味ソースとしてprojectionを生成し、発行処理と状態参照の一貫性を保証する。
- `issued_at`はDが生成し、payloadとは独立のtrusted issuanceとの一致を検査可能にする。Bがpayloadの`issued_at`だけを信頼の根拠にすることは禁止。不一致・信頼文脈の欠落ではBLOCKEDとする。
- DRILLの成立条件は`observed_at <= issued_at <= render_at < expires_at`であり、`expires_at`は排他的終端。Dが発行時点、Bが描画時点と復帰時点を検証する。
- 時計逆行、不連続な変更、D/B時刻整合の不確実性が検出された場合は旧表示を無効化し、新規検証成功までBLOCKED。単調増加時計は経過時間の補助であり、信頼できる絶対時刻の代替ではない。
- NORMALの`expires_at=null`は維持する。NORMALをLIVE確認済みとはせず、controllerの寿命・状態変更による無効化で管理する。

#### 3.1.4 期限到達・画面破棄

- controller破棄・再生成、generation変更、地域変更・再選択、`STOP_DRILL`、`SOURCE_FAILED`、`RESET`、期限到達、bridge/通知喪失、時計異常、component unmount/remount、画面離脱・`pagehide`で旧projectionを失効させる。
- 初期案ではタブ非表示でDRILL表示を破棄し、復帰・BFCacheからの再開では新たなbinding/取得・検証に成功するまでBLOCKEDとする。
- 旧fixtureの内容・訓練バナー・ARIA状態を一体で破棄し、「確認できません」を新しいNORMAL状態として偽装しない。
- **残余リスク：** スリープ・停止・イベントループのブロック中はJavaScriptタイマーだけで失効時刻ちょうどのDOM消去を保証できない。非表示時破棄、復帰・再描画直前の再検証を必須とし、厳密な実時間消去を要求するなら別途設計審査する。

#### 3.1.5 D/B/C責務とlocal-only bridge候補

| 領域 | 責務（未採用候補） |
|---|---|
| D Provider | S0/controller所有、generation、trusted issuance、`safe_view()`由来のprojection生成、旧binding失効、状態変更時の無効化整合 |
| B Consumer | binding・最新要求の照合、Schema/意味/render expiry確認、非同期旧応答拒否、DOM/バナー/ARIA破棄、再mount/復帰検証 |
| C Validation | S0実状態と発行時刻・projection独立照合、controller衝突/非同期逆転/時計異常/画面寿命の負例、後続Browser E2E・非配信確認 |

Python S0と静的Bの間には**非公開local-only bridge**を初期候補とするが、loopbackであることだけを認証とみなさない。Origin/Host、binding保護、キャッシュ・永続化排除、非配信境界の検証が必要。具体的なtransportやエンドポイントは本節で採用しない。

#### 3.1.6 D03-01〜05の判断追跡

| ID | 正式Contract採用前の必須判断 | 実装時に決められる詳細 |
|---|---|---|
| D03-01 | 信頼済みbindingの真正性、controller同一性、搬送の非公開境界 | binding表現・bridge実装詳細 |
| D03-02 | Dの時刻権威、D/B時計の安全条件、時刻不明時BLOCKED | 時計検出方法・閾値とその試験 |
| D03-03 | 状態変更と旧表示失効の順序、通知喪失時fail-closed保証 | 通知の実装方法・要求番号の実現 |
| D03-04 | unmount/remount、非表示復帰、BFCache、離脱時の破棄条件 | 画面状態管理・イベント処理の配置 |
| D03-05 | D/B/C合同採用、13フィールド維持、独立試験、公開HOLD | PR分割・QA実施時期 |

実装段階に委ねるのは手段であり、安全条件の省略ではない。

#### 3.1.7 CT-01〜13・追加負例N-01〜12の追跡

| CT | 既存検証または後続試験の対象 | 主な追加負例 |
|---|---|---|
| CT-01 | NORMAL初期、LIVE誤認禁止 | B表示検証 |
| CT-02 | DRILL開始・注意文完全一致 | 訓練バナー/ARIA |
| CT-03 | 地域変更・再選択の旧fixture破棄 | N-05 |
| CT-04 | STOP/取得失敗/RESETの破棄 | N-11 |
| CT-05 | 期限終端排他・tickなし失効 | N-07、N-09 |
| CT-06 | 旧世代・非同期逆転拒否 | N-03、N-04 |
| CT-07 | 同世代の別controller拒否 | N-01、N-02 |
| CT-08 | LIVE偽装・未知フィールド拒否 | B側の独立拒否試験 |
| CT-09 | 発行時刻改ざん・時計異常 | N-06、N-08 |
| CT-10 | 再mount・画面離脱・復帰 | N-09、N-10 |
| CT-11 | F05独立導線・S0非接続維持 | F05回帰 |
| CT-12 | 狭幅・キーボード・ARIA | Browser E2E、端末QA分類 |
| CT-13 | 非公開bundle・Render配信境界 | N-12、別途非配信試験 |

追加負例の期待条件：N-01別controller同generation拒否、N-02再生成後旧応答拒否、N-03 R2成功後R1破棄、N-04 R2失敗後R1再利用禁止、N-05描画直前世代変更拒否、N-06issued_at改ざん拒否、N-07期限切れ後着拒否、N-08時計逆行後の旧fixture復活禁止、N-09非表示中期限到達・復帰時BLOCKED、N-10再mount後旧callback拒否、N-11状態変更通知喪失でfail-closed、N-12不正Originのbridge接続拒否。

PR #387の既存25合成ケース・15テストはそのまま維持する。これらを未実施のbridge/B Browser E2E、追加負例、公式資料受入や公開承認のPASSとみなさない。必要な追加C検証は別の採用・実装段階で行う。

**未決・HOLD：** D03-01〜05の共同判断、信頼できるbinding・時刻・破棄方式、C独立受入、#372のUI実機QA区分。共有Contract正式採用、bridge製品実装、PR #387変更、main merge、Render公開は承認しない。

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
