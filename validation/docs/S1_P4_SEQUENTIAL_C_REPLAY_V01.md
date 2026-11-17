# C独立 S1-P4 操作シーケンス固定リプレイ v0.1

**2026-11-17 / C-only / synthetic only / NOT PUBLIC / 実データ・施設安全の承認ではない**

## 目的・責務
D内部S1-P4の[PR #407](https://github.com/1kz-ma1/HINANEX/pull/407)は、S0の合成訓練 → 条件変更/差分比較 → 利用者の明示的レビュー選択 → 期限・地域・データ失敗・停止で破棄、を実装した。今回は**C独立**に、P4の実装を実際に連続実行し、C自身が固定した期待値と実出力を比較する。D自体のunit testやDデモ`preview_s1_synthetic_walkthrough.py`の結果コピーではない。

前提: D #376(S0), #391(P0), #394(P1), #397(P2), #406(P3), #407(P4) は main統合済み。Cに先行 #400（S0→P2単体と静的合成回帰）、#403/#404（未承認証拠のHOLD/作業票）がある。**本追加はCだけの独立検証であり、公式原本証拠を調べる作業へ戻らない。**

## 変更ファイル
- `validation/fixtures/s1_p4_sequential_c_replay_v01.json` : 全て架空の`synthetic:` ID・6件の固定record（うち1件は意図的に別fixture）、1つの架空DRILL・5つの独立連続シナリオ、**計40の操作/投影チェックポイント**。期待する`generation/revision`、画面操作理由、before/afterの全レコード分類、差分ID、UNKNOWN、レビュー対象の元分類・missing/failedは**Cの期待値として直接固定**。原本から取得した値ではない。
- `validation/validation/verify_s1_p4_sequential_replay.py` : 実Dの`WalkthroughIntent`、`apply_walkthrough_intent`、`project_walkthrough`を実行。P4の出力と、**D P1実比較から直接算出した各行の分類・理由・条件別根拠**をCが別経路で突き合わせる。従来Cの固定fixture/record組立関数は再利用。比較結果/人の意思/公式安全性をテスト内で再実装しない。
- `validation/validation/test_verify_s1_p4_sequential_replay.py` : **29件のCテスト**。固定結果のPASSだけでなく、期待値改ざん、不一致レビュー昇格、P3のUNKNOWN→MATCHED偽装、古い操作による現在状態破壊、条件変更後の古い選択残留、LIVE偽装、実施設ID流入をそれぞれ故意に注入し、Cが検出することを確認。
- `validation/docs/S1_P4_SEQUENTIAL_C_REPLAY_V01.md` : 本仕様。

## 40チェックポイント / 5独立シナリオ

| シナリオ | チェック数 | 実際に確認する内容 |
| --- | ---: | --- |
| 連続操作・選択解除・停止 | 11 | START→合成一致/UNKNOWN→明示選択→条件変更で旧選択解除→差分→UNKNOWN選択→解除→別fixture拒否→再選択→STOP後に空結果 |
| 遅延コールバック・地域変更 | 9 | 同じS0世代で旧revisionのREVIEW/SET_CONDITIONSを拒否。正しい現選択は保持。地域変更後は旧選択拒否、新しいSTARTからのみ再開 |
| 期限終端・非同期操作 | 7 | 有効期限直前は投影可能。期限ぴったりではreducer tickなしでも空。期限後の操作でS0世代/revisionを進め、失効fixture再開始を拒否 |
| SOURCE_FAILED・RESET | 7 | 取得失敗・再開始・RESETで古い条件/選択が復活せず、通常モードに実データの評価を偽装しない |
| 不明ID・明示的な非一致レビュー | 6 | 現比較にないIDはBLOCKED。非一致は本人が調べる対象としてだけ選択可能で、変更・解除で古い選択が残らない |

## 独立で必ず守る不変条件
- Cの期待値はDのプレビューをコピーしない。**全チェックポイント**でS0`mode`/投影`view_mode`、`generation`、`revision`、対象地域・有効`fixture_id`、現/前条件・選択ID、操作`status/reason`、投影結果・全分類・差分・UNKNOWN・選択レビューを比較する。未定義キーや不完全な期待値は`BLOCKED`。明示時刻はUTCオフセット付き。
- 毎回DのP1`compare_synthetic_conditions`を独立に呼び、P4/P3の結果行（record_id/前後分類/理由コード/checks/missing/failed）と突き合わせる。P4/P3が`UNKNOWN`を一致に変えたり、差分IDを都合良く増減したら`FAIL`。
- P2レビューは`REVIEW_SELECTED_SYNTHETIC_ONLY`・`review_only=true`。現在のP1行の`status`、理由、checksと一致しなければ`FAIL`。別fixture`NOT_EVALUATED`は選択不可。
- S0の`safe_view`の訓練表示・`SYNTHETIC_TEST_ONLY`、正常モードから旧fixture情報が消えることを別検査する。正常モードには条件・前条件・レビューを残さない。
- 条件変更時に古いreview IDが保持された場合、明示の`FILTER_CHANGE_RETAINED_REVIEW`で`FAIL`。遅延操作が、現在有効な状態を変えた場合も`STALE_ACTION_MUTATED_CURRENT_SESSION`で`FAIL`。
- 期限後の投影は`BLOCKED + result=None`。元の不変Pythonオブジェクトの存在をゼロにしたとは主張せず、**有効な最新の投影から過去の評価を出さない**ことを確認。期限後コマンドで世代/操作revisionを進める動作も固定期待値で照合する。
- 全transition/projection/P3/P2で`synthetic_only=true`、公式承認・LIVE・施設/経路安全・releaseの安全フラグは厳密にfalse。結果を**実施設の安全/開設/災害適合/経路の保証**へ昇格しない。レポート上の`regression=PASS`は**合成P4の再現テストのみ**。

## 使用・CI
リポジトリrootから:
~~~sh
python validation/validation/verify_s1_p4_sequential_replay.py --json
python -m unittest discover -s validation/validation -p 'test_verify_s1_p4_sequential_replay.py' -v
~~~
合成固定fixtureは全項目を明記し、ネットワーク、端末位置、実原本バイト、localStorage、HTTP API、永久保存、個人情報、住所・座標・実施設IDを使用しない。`--json`は機密のない合成の状態/結果のみを出力し、レポートをファイルへ書き込まない。偽の安全フラグ・出典/承認を実データへ転用する機能は存在しない。

CLIの`exit 0`はC合成期待値PASSのみ。未整合なら`exit 1`、入力/manifest不正なら`exit 2`（一部の不完全期待値は出力ステータス`BLOCKED`でexit1）として未受理にする。

CIは正確なPR HEADの必須`test`、C Scope Guard、既存D279/C318+B/E/deploy/schemaの回帰を確認する。**Device QA: NOT_REQUIRED**（C純粋Python）。実Chrome、iPhone/Android、D→B Transport、GPS・保存・実施設利用・GIS参考経路・法的権利・正式原本照合、一般公開は一切行わない（`NOT_RUN / NO-GO`）。

## 統合・再開判断
このPRは`validation/**`のみに限定。koutaのF05/B1 Draft #371、F05/B2・Chrome QA #399/#405、F03、Dの#407、本件の共有Contract保留Draft #386/#387には触れない。新しいD→B/ブラウザ契約やUI制御の採用を自動的に許可しない。実データの根拠確認と人間承認は#134/#48/#366で継続HOLD。

**MVPの今後:** このC回帰が通れば、合成モードの連続操作と遅延処理に対する統合前の安全回帰基盤として使える。ブラウザ接続する場合は、改めて公開/表示と人間のQAを別Issue/PRで判断する。
