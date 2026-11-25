# S1-P4｜合成模擬操作の状態遷移・古い操作拒否 v0.1

**2026-11-17 / D内部のみ / 合成DRILL専用 / D→Bの共有Contractではない**

## 目的
S1-P3の条件変更シミュレーションを、画面操作に必要となる**連続した入力・結果・状態失効**の単位で扱う。ブラウザ画面そのものやD→B APIの新設ではなく、既存のS0 / S1-P0/P1/P2/P3を再利用したD内部の純粋状態遷移である。koutaのF05/B1 Draft #371、B2 #399、F03保存、E GIS、S0→UI共有Contract Draft #386/#387には変更しない。

人手が不足する間はこの領域の合成実装を優先し、公式原本・施設同一性・自治体ハザード意味・利用権利の人間承認を擬装・自動承認しない。

## 内部モデル
`pipeline/src/hinanex/s1_synthetic_walkthrough.py`:
- `WalkthroughState`：S0の`Session`と、現条件・直前の条件・本人が明示的にレビュー対象に選んだ架空ID・`revision`（0から始まる整数）だけを保持する。比較レポート、現況災害、GPS、ユーザー属性、永続データは保持しない。`NORMAL`時は条件/選択が空。
- `WalkthroughIntent`：`kind`、`expected_generation`（S0の世代）、`expected_revision`（今回の画面操作単位）、`explicit_user_action`、操作種別に応じた条件/ID/地域/合成fixture。各種別と不許可フィールドを検査し、無断の自動条件変更や選択を許さない。
- `apply_walkthrough_intent`：START、SET_CONDITIONS、REVIEW、CLEAR_REVIEW、STOP、SELECT_REGION、SOURCE_FAILED、RESETを単一のS0/内部操作として扱う。条件更新は**常に以前の選択を解除**、reducerの世代と内部revisionを更新。旧revisionは同じS0世代でも`STALE_WALKTHROUGH_ACTION`で拒否。
- `project_walkthrough`：投影時の`safe_view`で時点・有効範囲を毎回再検査し、`compare_what_if`（P3）を再実行。明示的な前回選択があればP2でその時点の結果を再検査し、UNKNOWNを安全な一致へ昇格しない。
- 終了・地域切替・取得失敗・RESETで条件と選択を全破棄する。**失効時は投影をBLOCKED + result=null**とし、次のコマンド適用時にはS0 generation/revisionを増加させて旧コールバックを拒否する。古いPythonのimmutable state自体を書き換えるのではなく、最新状態の利用を強制する方式。これを外部UIの永続状態契約と解釈しない。

## 操作意味の固定
1. STARTは本人の明示入力、現在のS0 generation/revision、`synthetic:` fixture、地域完全一致、有効期間と最低1条件を要求。安全・開設・推奨の情報は作らない。
2. SET_CONDITIONSは`pet_support` / `step_free`の架空bool条件のみ。変更後の一覧と差分はP3で再評価する。**変更後は本人が以前選んだ対象を再利用しない**。
3. REVIEWは現在の比較に存在する架空IDを本人が明示選択。UNKNOWN・NOT_MATCHEDも「内容を確認する対象」としてのみ選択可能。別fixture・失効・存在しないIDの選択はBLOCKED。レビュー結果に対する不正な古い応答もrevisionでBLOCKED。
4. CLEAR_REVIEWは選択を解除し、比較の条件は維持する。
5. STOP / SELECT_REGION / SOURCE_FAILED / RESETはS0 reducerを必ず呼び、セッションと選択を無効化する。新しいDRILLは新STARTを必要とする。旧世代のSTART等が後から届いても復活しない。
6. 訓練の有効期限`expires_at`は排他的。時刻境界に到達した投影には古い結果が一切出ない。これをライブ災害の更新周期と混同しない。

## 実装範囲・安全フラグ
出力は`WalkthroughTransition`（適用/拒否＋新immutable state）と`WalkthroughProjection`（最新の合成計算、またはBLOCKED）で、API/正式JSON Schema/ブラウザへ公開していない。どちらも`synthetic_only=true`、公式受入/LIVE/施設安全/経路安全/一般公開のフラグは`false`。S0/S1各既存モジュールの意味・RegionExport v0.9・実ソースを変更しない。

## 固定シナリオCLI
`pipeline/`から:

~~~sh
python preview_s1_synthetic_walkthrough.py --scenario normal
python preview_s1_synthetic_walkthrough.py --scenario stale
python preview_s1_synthetic_walkthrough.py --scenario expired
python preview_s1_synthetic_walkthrough.py --scenario stopped
~~~

CLIはP3の**固定架空fixture/5件**だけを利用し、仮想時刻でSTART→条件変更→明示レビューを実際に操作する。`stale`は変更前の旧revisionによる遅延レビュー拒否を含む。`expired`は期限終端前後の投影と旧操作拒否を含む。`stopped`は停止後に比較と選択が空であることを確かめる。stdoutは結果/操作理由のみで、実住所/個人情報/通信/ファイル書き込みはない。CLIはGUIではなく固定操作シナリオの観察用。

## テスト・非対象
- `pipeline/tests/test_s1_synthetic_walkthrough.py`：28件。START〜停止/再開、条件変更で旧選択解除、同じS0世代の遅延コールバック拒否、UNKNOWN・不一致保持、異なるfixture拒否、期限端/地域変更/失敗/RESET、型・重複・実施設拒否、状態不変性を検証。
- `pipeline/tests/test_s1_synthetic_walkthrough_preview.py`：7件。固定CLIの正常/旧revision/期限切れ/停止・不承認フラグ・決定論を検証。
- `python -m unittest discover -s tests -v` と required CI `test` が正確なPR HEADで成功した場合にD内部機能の合成受入とする。

**NOT_RUN / NO-GO:** 実Chrome/Safari/端末の操作、HTTP D→B連携、正式F05への採用、個人情報保存、実施設の選定・開設・参考経路、原本/ライセンス/公式意味の人間受入、Render一般公開。本体は純粋Pythonなのでこのスライス単独のDevice QAは`NOT_REQUIRED`。UIに接続する時は別PRの共有Contract安全レビューと#372実機QAが必要。
