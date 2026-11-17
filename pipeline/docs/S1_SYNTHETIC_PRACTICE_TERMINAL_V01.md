# S1 合成訓練｜対話式ターミナル操作体験 v0.1

**2026-11-17 / D内部ローカル実験 / SYNTHETIC_TEST_ONLY / NOT B UI / NOT a shared Contract**

## 目的と方針
合成S0→S1-P4（[#407](https://github.com/1kz-ma1/HINANEX/pull/407)）とCの連続/耐久回帰（[#409](https://github.com/1kz-ma1/HINANEX/pull/409)、[#412](https://github.com/1kz-ma1/HINANEX/pull/412)）がmain統合済み。追加のテストだけでは利用者の直接操作体験が増えないため、**既存D reducerを実際に呼ぶ、ローカル対話型コンソール**を提供する。

koutaのF05 Draft #371・F05/B2 Focus Draft #411、GIS F07 Draft #408、S0→UI共有Contract #386/#387と競合しないため、ブラウザ/モバイルUIやHTTP D→B接続は一切作らない。**コンソールは操作の試作であってMVPの正式UIではない**。

## 操作内容
`pipeline/preview_s1_synthetic_practice.py` を`pipeline/`から実行:

~~~sh
python preview_s1_synthetic_practice.py
# 固定の実行例。対話入力不要
python preview_s1_synthetic_practice.py --demo
~~~

利用可能なコマンド:

| コマンド | 効果 |
| --- | --- |
| `help` | 操作一覧と合成訓練警告を表示 |
| `start` | 本人の明示操作として合成S0訓練開始。既存P4 reducerを使用 |
| `show` | 現時点の5架空レコードの全分類、前回の条件変更による追加・解除と明示レビューを表示 |
| `pet` / `step` / `both` | 架空条件をペット／段差／両方に変更。以前の選択は解除される |
| `select a`〜`select e` | **架空レコード**1件だけを本人がレビュー対象として選択。UNKNOWNや不一致も元の分類のまま |
| `clear` | 明示選択を解除。条件は維持 |
| `stop` | S0訓練終了。条件・選択・行表示をすべて空にする |
| `advance N` | 仮想時刻を1〜60分進める（合計65分まで、巻き戻し不可）。30分の期限終端で結果は非表示 |
| `quit` | 終了。状態を一切保存しない |

開始時刻は固定の`2026-11-13T00:00Z`、初期操作時刻は+5分。旧P3プレビュー`sample_state()`の`synthetic:a..e`（架空ペット・段差属性）を再利用し、原本/施設名/住所/座標/個人情報は受け取らない。`pet`/`step`/`both`は**仮のレコード属性**を調べる操作であり、実際の避難施設のペット受入・バリアフリー情報ではない。

## 状態遷移と安全性
- 内部`SyntheticPractice`は`WalkthroughState`、入力レコードと仮想時刻のみを保持。`handle()`は許可されたコマンドだけを`WalkthroughIntent`に変換し、**Dの`apply_walkthrough_intent()`へ渡す**。`show_summary()`は毎回`project_walkthrough()`で最新状態を再評価する。判定ロジック・レコード選択・失効をコンソール側で独自実装しない。
- `start`は二重訓練開始を拒否。`stop`後に再開始は可能だが、すでに期限切れの合成fixtureを使い回して再開できない。`advance`は明示的な仮想時計で、端末時刻や実際の災害情報を読まない。期限が来たら`BLOCKED + result=None`なので古い行/レビューを表示しない。次の操作はP4の世代/revision失効処理を通る。
- `select`は英字`a..e`のみを厳密に許可。空欄・異なるID/実施設ID・任意文字列はP4に送らず無効操作。自動選択やランキングをしない。UNKNOWNと不一致と一致は明示的に区別し、**一致でも「安全」と表示しない**。
- 端末には常に「【合成訓練専用】現実の災害・避難施設の安全性や開設状況を示しません。」を掲示。100操作で自動終了。外部通信・保存・ユーザー履歴・通知なし。処理完了後はローカルメモリが消える。コンソールに公式承認フラグを渡すAPIもない。
- コマンドの真の意味はすべて元のS0/S1-P4から得る。未知条件、非合成データ、実施設の安全性判断は不可。

## 受入・回帰テスト
`pipeline/tests/test_s1_synthetic_practice.py`（**24件**）で、未開始、START、5レコード、ペット・段差条件、差分、UNKNOWNレビュー、選択解除、終了→再開、二重START防止、期限終端前後の投影停止、期限後START拒否、不正ID/複数文字選択拒否、時間入力上限、入力正規化、EOF/quit、100操作上限、`--demo`再現性、ファイル非書込みを確認する。

実行:
~~~sh
cd pipeline
python -m unittest discover -s tests -p 'test_s1_synthetic_practice.py' -v
python -m unittest discover -s tests -v
python verify_d_mvp.py
~~~

CIは正確なPR HEADでrequired `test`、D Scope Guard、既存C/D/B/Eとdeploy/schemaの後方互換を検証する。失敗をskipせず修正する。**Device QA: NOT_REQUIRED**（今回のD PythonローカルCLIに限る）。実ブラウザ・モバイル・F05表示や共有Contract受入・公式ソース/ライセンス/施設同一性の人間レビュー・実災害時の安全判断・一般公開は**NOT_RUN / NO-GO**。今後UIへ載せる場合はB担当と正式なContract境界・QAの別PRを必要とする。
