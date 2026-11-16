# C独立統合リプレイ v0.1 — S0実装の実入出力（合成のみ）

**状態:** C側Draft検証仕様（2026-11-16）。S0 Providerは [PR #376](https://github.com/1kz-ma1/HINANEX/pull/376)（2026-11-16にmainへSquash統合済み）。Issue #305 / #375 / #360 / #372に対応。C v0.1 PR #381はmain統合済み。

## 最小責務と契約境界
本テストは **実装済みのS0 Python状態モデルをimportして固定合成イベントを実行する**。期待JSONと実際の状態・表示出力を照合し、C独立の安全ゲートも適用する。Dの`reduce_session`・状態遷移アルゴリズムは複製しない。

接続点はD内部のテスト専用API。S0を正式共有Contractへ昇格させない。変更は`validation/**`限定。共有RegionExport/Schema、B/E、D本体、H0、F01/F02/F05、CI、Renderへの変更なし。

C v0.1 `MVP_SYNTHETIC_CONSISTENCY_V01.md`は架空envelopeの静的入出力検査。本仕様は**実際のS0 reducer/safe_viewを使う第二層の結合検証**。S0の実モデルの`region_code`/`generation`/`expires_at`をC v0.1の別物の`region`/`session_token`/`valid_until`へ誤変換しない。C原本監査・歴史的災害デモとも別物。

## 接続元と形式
- Provider: `pipeline/src/hinanex/drill_session.py`（#376）。`Session`/`SyntheticFixture`/`Event`/`Action`/`Mode`/`reduce_session`/`safe_view`/`StaleSessionError`を実際に呼び出す。
- Consumer: `validation/validation/verify_s0_session_replay.py`。
- Fixture: `validation/fixtures/s0_c_replay_v01.json`。固定時刻・合成識別子のみ。region `13123`/`15100`はS0の入力形式をテストする文字列で、自治体の実データ受入ではない。
- Unit tests: `validation/validation/test_verify_s0_session_replay.py`。
- 各caseは新規`Session()`から開始。stepは`EVENT`または`VIEW`、明示`now`、必要に応じ`fixture`/`expected_generation`。`expect.transition`と`expect.view`は出力と独立した期待値。

## C独立安全ゲート
1. viewの`live_data_verified`は常に厳密に`False`。「通常モード＝現在の災害情報取得済み」にはしない。
2. NORMAL表示では`fixture_id`/`hazard`/`source_authorization`は`None`。古い模擬データを表示しない。
3. DRILL表示では内部stateのfixtureとregion/hazard/id/sourceが一致し、`observed_at <= now < expires_at`を満たす。認可区分は合成専用の`SYNTHETIC_TEST_ONLY`。
4. DRILLの訓練注意文が欠落したらFAIL。未レビューのpublic fieldが増えたらFAIL（仕様・公開安全ゲートの再レビューが必要）。
5. staleな`expected_generation`による`StaleSessionError`は**期待された拒否**として観測し、直前の状態が維持されることを確認する。
6. 施設の安全・開設・経路の断定はS0の公開出力に存在しない。Cも合成で作らない。公式原本受入の代用にしない。

## 受入・結果ステータス
- 固定14ケース: NORMAL開始、DRILL開始停止、地域変更、元データ失敗、旧応答拒否、時限切れ表示、未来fixture拒否、地域不一致、同意付き希望地域、リセット、ハザード/地域切替、fixture不足、検証不能、未実行。
- `PASS`: 実S0出力が独立検査と期待値に整合。期待通りの拒否も回帰PASS。
- `FAIL`: 不一致や不当なLIVE断定・公開値を検出。回帰が不一致ならexit=1。
- `BLOCKED`: fixture/時刻/期待値の不足で判定不能。
- `NOT_RUN`: 明示的に未実行。実機QAは別途`NOT_RUN`。
- レポートの`official_acceptance`は常に`false`、`device_qa`は常に`NOT_RUN`。全ケースの期待結果との一致だけが`regression=PASS`である。

## 実行
**#376を含むチェックアウト**のrootで実行:

~~~sh
python validation/validation/verify_s0_session_replay.py --json
python -m unittest discover -s validation/validation -p 'test_verify_s0_session_replay.py' -v
~~~

依存S0が欠ける環境ではテスト成功と扱わない。既存required `test` CIがCのtest_*.pyを自動検出するため、CI設定変更は不要。実機QA分類は**NOT_REQUIRED**（純粋Python・合成のみ）。UIとの接続時は#372に別途QA登録。

## 依存・統合判定
- **Depends on #376 — 解決済み**。S0 providerはmainに統合済み。C側ブランチは最新mainに追従・PRのbaseをmainへ変更した。D担当のブランチ/ファイルには変更しない。
- ProviderのAPI/HEADが変化した場合は再確認する。main追従後のrequired CI `test`が成功した場合に限りDraft解除およびMerge Captain最終審査へ進める。
- 合成PASSは公式出典・施設安全・現在の開設・経路通行・F02/F03配信の承認ではない。
- B/E共有API、状態永続化、実災害入力、発表デモの実機は別途共同契約レビュー・公開安全判定の対象。
