# C独立 S1-P4 連続再開・遅延操作の耐久回帰 v0.1

**2026-11-17 / C-only / SYNTHETIC_TEST_ONLY / ローカル固定シナリオ / NOT an official acceptance or B UI contract**

## 目的
[PR #407](https://github.com/1kz-ma1/HINANEX/pull/407)のD内部S1-P4操作モデルと、[PR #409](https://github.com/1kz-ma1/HINANEX/pull/409)のC独立固定リプレイ（**5シナリオ・40チェックポイント**）はmain統合済み。本追加では単発の順序検証を補完し、**多数の連続した訓練の開始・変更・レビュー・終了・再開**を実際のD reducerで再生し、以前の世代・操作revision・fixture・選択が次の試行へ混ざらないことを検証する。

根拠と区別:
- Cの期待分類は6つの架空レコードの明示的`pet_support`/`step_free`（真偽/None）から定める。`UNKNOWN`と`NOT_MATCHED_SYNTHETIC`は異なる意味で、資料の実在・避難安全性ではない。元のDデモ出力を正解として転記しない。
- 既存Cの`_projection_audit`を呼んで、**DのP1を直接再計算して**P3/P4の条件・理由・missing/failed・P2レビューの元分類と突き合わせる。C独立40チェックポイントを削除・置換しない。
- 既存S0・D P0/P1/P2/P3/P4、B/F05、E/GIS、shared Contract、RegionExport v0.9、公式データ・Evidence/権利資料は一切変更しない。

## 追加成果物
- `validation/validation/verify_s1_p4_endurance.py`：C-only決定論的な耐久検証。既存Dの`WalkthroughIntent / apply_walkthrough_intent / project_walkthrough`を使用し、**48周回（デフォルト）**、最大64周回の安全な上限付きリプレイを行う。Pythonの`random`や外部通信・外部時刻は使わない。
- `validation/validation/test_verify_s1_p4_endurance.py`：**17件**のC単体テスト。正規周回、64周上限、5種の失効/停止、バージョン境界、C自身の期待値、不正なLIVE・UNKNOWN→一致の偽装・旧操作の現在選択改ざん・filter変更後の旧選択残留を故意に注入して検出する。
- `validation/docs/S1_P4_ENDURANCE_C_REPLAY_V01.md`：この仕様とゲート区分。

## 48周回の構成と状態遷移

各周回はA/Bの**2つの異なる`synthetic:` fixture**と、フィクションの6件（5件が当該fixture、1件は意図的な別fixture）を使う。新しいfixtureは前と異なるレコードID・属性・observed_at/expiryを持つ。以前のrecord IDが再開後に含まれても、意図せず継承されてもいけない。

1. A START（`pet_support`）→明示レビュー→`step_free`へ変更して以前の選択解除。
2. 変更前の`revision`で届いた遅延レビューは拒否。変更後のUNKNOWN対象を明示レビューする。さらに古い条件変更も拒否し、正しい現在選択を維持。
3. `pet_support + step_free`の2条件へ変更し再び選択を解除。本人によるCLEAR、別fixtureのID選択の拒否、条件不一致の架空IDを「レビュー対象としてのみ」選択。
4. **5周に1回は有効期限ちょうど**に到達し、timer/reducer tickなしで結果を隠す。その直後の旧操作はS0`generation`と操作`revision`を進めて拒否。それ以外はSTOP、SOURCE_FAILED、SELECT_REGION、RESETを循環して訓練を解除。
5. Aの遅延コールバックを拒否してから、別のB fixtureを新START。新しい現条件`step_free`で`UNKNOWN`を明示レビューし、`pet_support`へ条件を変更して本人選択を解除。最新のBレコードについてのみ明示レビューを許し、STOP後は選択・比較・前条件・fixtureを全破棄。
6. 全周回で、次の周回開始前に`NORMAL`かつ条件/レビューが空であることを検査する。

固定モードでは**1周18個の実D操作、16回の投影**（期限切れ周は17回）、計48周なら**864操作・778投影、期限終端10周、旧操作拒否202件**。実Dの振る舞いを再生するので、直前状態を保持したまま連続実行する。`state`は1件だけ、各周の過去出力やレコードを集積しない。これは**ロジック上の境界/漏洩回帰**であり、プロセスRSS・ヒープ使用量・実端末の性能・持続時間のベンチマークではない。

## Fail closed 条件
- 各操作で`generation`と`revision`の期待増分を検証。古い操作は**同一オブジェクトのまま**拒否（失効時の明示クリアは例外で正しい+1を要求）。成功した条件変更は以前のレビューIDが必ず空。
- 各投影でC既存のP1独立照合とC固定の全レコード分類を検査。別fixture/未確認`UNKNOWN`、条件の明示`False`、複合条件の不足を同一視しない。レビューがあれば、元のP1分類・`missing/failed`を保存する。
- 状態をNORMALに戻す操作では`conditions`/`previous_conditions`/`selected_record_id`とfixtureを破棄し、投影は`BLOCKED + result=None`。すべての結果で`synthetic_only=true`、公式受入/現況LIVE/施設安全/経路安全/公開は`false`。
- 出力は`schema_id`、PASS/FAIL、件数と最初の失敗理由コード・周回番号のみ。架空レコードの本文・Raw・座標・名前・人間のレビュー記録を蓄積・公開しない。CLIはstdoutのみでログファイル作成・外部通信・正式資料参照をしない。
- 周回数は整数1〜64のみ許可。`bool`や範囲外は`exit 2`、回帰FAILなら`exit 1`、PASSなら`exit 0`。**exit 0は架空データの耐久回帰成功のみ**。

## 実行
リポジトリrootから:
~~~sh
python validation/validation/verify_s1_p4_endurance.py --cycles 48 --json
python -m unittest discover -s validation/validation -p 'test_verify_s1_p4_endurance.py' -v
~~~

CIでrequired `test`、C Scope Guard、既存C/D/B/E/deploy/schema回帰を正確なPR HEADで確認する。単体テストの時間はPython CI上で測るが、実際の機器性能評価・コンカレンシー/スレッド・HTTP競合・ブラウザ画面の操作速度を確認したとは報告しない。

**Device QA**: NOT_REQUIRED（C Pythonのみ）。実機UI、ブラウザ、D→B Interface、新しい共有Schema、実災害データ・実施設・権利・開設と参考経路、一般公開はすべて**NOT_RUN / NO-GO**。人間の独立レビューを必要とする#134/#48/#366のHOLDは変更しない。

## 今後の接続
この耐久テストが緑でも、koutaのF05/B1 Draft #371、F05/B2、F03保存、S0→UIの未採用共有Contract Draft #386/#387の状態は変更しない。D側の操作UI採用や実機E2Eへ進む場合は、共有契約レビューと人間の受入/デモ条件を別PRで定義する。
