# S1-P3｜合成条件の変更・差分比較ワークベンチ v0.1

**2026-11-17 / D内部実装 / SYNTHETIC_TEST_ONLY / NOT PUBLIC API**

## 目的
証拠整理で実装を止めないために、**公式原本・施設の独立承認なしに実装できる利用者価値**を増やす。既存S0（合成訓練の開始/停止）とS1-P0（抽出）、P1（理由付き比較）、P2（明示的レビュー選択）を**変更せず再利用**し、架空の条件を変えた前後で抽出結果がどう変わったかを、本人がローカルに試せるD内部ワークベンチを用意する。

UI・F05の担当koutaの作業やF03保存Contractを横取りしないため、現在はPython CLIと純粋関数のみ。S0→UIのDraft #386/#387のTransport採用を前提にしない。公開API、RegionExport v0.9、Dの実施設用Scenario、B/E、raw/official data、Render配信、端末位置・保存機能は**非対象**。

## 機能と意味
- 呼び出し側が**現在の**S0 Session、明示時刻、架空SyntheticReferenceレコード、初期条件（before）と変更後条件（after）を渡す。
- before/afterはどちらも1つ以上、既存S1-P0が受け付ける`pet_support`と`step_free`に限定。これは架空施設の架空属性であり、実施設のペット受入やアクセシビリティを表すものではない。受入可能な条件の拡張は別仕様。
- `compare_what_if()`は毎回S1-P1を**両条件で再評価**し、各架空IDのbefore/afterの`MATCHED_SYNTHETIC / NOT_MATCHED_SYNTHETIC / UNKNOWN`、理由、条件別の`EXPLICIT_SYNTHETIC_TRUE/FALSE / UNVERIFIED / NOT_EVALUATED`、missing/failedを保持する。
- `newly_matching_synthetic_ids`は**条件変更後に架空の一致になったID**、`no_longer_matching_synthetic_ids`は一致でなくなったID。並びは入力順で、距離・安全・推奨順位ではない。`unknown_after_synthetic_ids`は常に別集合として保持。UNKNOWNをEXCLUDEDへ、完全一致を「安全」「開設中」へ昇格しない。
- `review_choice`が明示された場合のみ、**変更後の条件でS1-P2を再実行**する。UNKNOWNまたは不一致の合成レコードも「調べる対象」として選べるが、元の分類を保持する。未指定時に自動選択・デフォルト選択はしない。
- 失効、模擬停止、地域・災害範囲の不一致、旧generation、通常状態のいずれも`BLOCKED`として**全行・差分ID・以前の選択を空**にする。過去レポートを引数に取るAPIや有効期限を超えるキャッシュは持たない。
- 出力`WhatIfResult`は`synthetic_only=true`と公式受入/LIVE/施設安全/経路安全/公開承認の厳密な`false`を持つ。JSONはローカル実験用で、B向けContractや外部通信形式ではない。

## CLI使用例（固定架空データのみ）
`pipeline/` から:
~~~sh
python preview_s1_synthetic_what_if.py
python preview_s1_synthetic_what_if.py --before pet_support --after pet_support,step_free
python preview_s1_synthetic_what_if.py --before pet_support --after step_free --select synthetic:e
python preview_s1_synthetic_what_if.py --minutes 30 --select synthetic:a
python preview_s1_synthetic_what_if.py --stop
~~~
CLIは時点2026-11-13T00:00Zに作成した`synthetic:whatif-preview`を30分有効として扱い、合成地域コード13123・合成洪水ラベル・架空の5レコード`synthetic:a..e`を用いる。`--minutes 30`は時間境界でブロック、`--stop`はS0 STOP_DRILLイベントを実行してブロックする。時刻は実時間ではなく固定シミュレーション。CLIは対話のオプション入力による実験であり、ブラウザ/Android/iOS画面操作ではない。

**期待結果例:** 変更前`pet_support`から変更後`step_free`では、`synthetic:c` / `synthetic:d`が合成一致に移り、`synthetic:b`が一致から外れ、`synthetic:e`はUNKNOWN。どの変化も災害時の適合や安全性を示さない。

## テストと承認
- `pipeline/tests/test_s1_synthetic_what_if.py`は21件、`pipeline/tests/test_s1_synthetic_what_if_cli.py`は7件。変更前/後の差分、UNKNOWN/不一致の保持、明示的なレビュー選択、時間切れ/停止/地域変更/旧世代の破棄、重複・不正条件の拒否、ローカルJSON出力を検証する。
- 実行（`pipeline/`から）:
~~~sh
python -m unittest discover -s tests -p 'test_s1_synthetic_what_if*.py' -v
python -m unittest discover -s tests -v
~~~
- CIは正確なPR HEADでrequired `test`、D Scope Guard、C/B/E・デプロイの後方互換を確認する。実ブラウザ/スマホは**NOT_RUN**で、このD純粋Python機能単体のDevice QAは`NOT_REQUIRED`。本番の実施設データ、公式災害意味・原本・ライセンスの人間受入、経路・開設は全てHOLD。自動デプロイ・PRの勝手なmain直push禁止。

## 後続の実装候補
UIへの接続・事前設定保存は現在の領域別担当と共有Contractの採否を確認してから別PRに分ける。P3がmainに入ってもF05 #371、B2 #399、S0→UI提案 #386/#387の状態を自動変更しない。
