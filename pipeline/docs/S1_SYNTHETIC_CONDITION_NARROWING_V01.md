# S1-P0 — 合成条件抽出コア（D内部・未承認・非公開）

**2026-11-16 / 状態:** Synthetic-only implementation proposal. 公式の避難候補抽出・災害安全性判定・B/Eへの共有Contract採用は**未実装・未承認**。

## 背景と切り分け

- Issue #305 Stream S1は、事前設定・災害・公的証拠から適用できる条件のみを使い、本人が根拠を比較できる参考掲載集合を目標にしている。
- S0のNORMAL/DRILLモデル（main統合 #376）、CのS0実出力検証（main統合 #384）は前提。S0→UI Transport/ContractはDraft #386/#387で**レビュー保留中**。
- 現行の`flood_scenario.py`は新潟公式ODS「○/×」の個別意味や江戸川の公式同一性が未承認なため`UNKNOWN`を正しく維持している。このコードと`RegionExport v0.9`は**変更しない**。
- koutaのF05 Draft #371、F02、F03、E GIS、公式GSI H0 Draft #379とは独立。UIや未承認原本への接続を先取りしない。

## このスライスで実装した内容

`src/hinanex/s1_synthetic_narrowing.py`: S0の実`Session`から`safe_view(state, now)`を呼び、明示した固定合成条件を同一のインメモリS0状態に限定して突き合わせる**純粋関数**。

- `SyntheticReference`: `synthetic:`で始まる架空ID、S0 fixture ID、地域5桁、明示hazard、TZ付き観測/失効時刻、`SYNTHETIC_TEST_ONLY`、`(condition_name, bool | None)`の不変tuple。**実施設名/座標/住所/公式列/出典URLは禁止**。
- `NarrowRequest`: S0 `expected_generation`、選択地域・hazard、本人が明示した抽出条件。不明/重複キーは拒否、条件0件はBLOCKED。現在の固定テストキーは`pet_support`と`step_free`。**合成上の架空のチェック属性であって実際の動物受入/バリアフリーの調査結果ではない**。
- `narrow_synthetic_references`: 有効なS0 DRILLの`selected_region/hazard/fixture_id`と同一generationを要求する。NORMAL、期限切れ、地域/災害の不一致、旧generationは**BLOCKED**として結果を空にする。
- 有効な架空レコードのみ、必要条件を**全て明示True**なら`MATCHED_SYNTHETIC`。必要条件のうちいずれかが欠落/`None`なら`UNKNOWN`（他の条件がFalseでも`UNKNOWN`優先）。必要条件が全て既知で一つ以上明示Falseなら`NOT_MATCHED_SYNTHETIC`。
- fixture/region/hazardが異なるレコードや、観測前/失効レコードは`UNKNOWN`。**UNKNOWNを不適合/安全/除外へ変換しない**。
- 元入力順を維持。距離順、安全順、ランキング、施設推薦、現在の開設、安全確認、経路推薦は一切出力しない。
- 全Reportで`synthetic_only=true`、`official_acceptance=false`、`live_data_verified=false`、`facility_safety_verified=false`、`route_safety_verified=false`、`release_approved=false`を固定する。

## 失効・プライバシーと境界

- `safe_view`が期日境界でNORMALになった時は、その前の結果を返さない。`expected_generation`は**同一メモリSession**にのみ有効。別ブラウザ/タブ/再起動や保存からの復帰はサポートしない。
- GPS/住所・本人条件の保存/外部送信、外部API・ネットワーク呼び出し無し。固定S0セッションと合成record/要求を**呼び出し側が引数で提供**。
- 現実のC未承認データ、未確認の`source_authorization`をS1で「証拠あり」に変えない。正式な公式施設一覧・災害適合性判定への適用は**別のA/C/D共同受入**を必要とする。
- Dの`flood_scenario.py`や`RegionExport`の`CANDIDATE/EXCLUDED/UNKNOWN`と**異なる内部実験ステータス**を持つ。相互変換と共有スキーマへの追加は禁止。
- B/F05などに渡すTransport/Contractは未決。Draft #386/#387の採用を要求せず、逆にこの実装で採用済みと見なさない。

## テスト・実行

`pipeline/tests/test_s1_synthetic_narrowing.py`で18件の合成回帰：
- 2条件のAND一致/不一致/不明（不明優先）・条件の欠損
- 異地域/異災害/別fixture、失効/未来record、期限境界
- S0 NORMAL・世代の古い応答・地域切替・条件0件
- 公式ID/公式Source偽装、重複ID、値型・タイムゾーン不正
- 公式・公開・施設/ルート安全の偽陽性拒否、入力順/非破壊性

実行：

~~~sh
cd pipeline
python -m unittest discover -s tests -p "test_s1_synthetic_narrowing.py" -v
python -m unittest discover -s tests -v
~~~

`verify_d_mvp.py`と実Raw再生成は**既存の実データ成果物が必要で、この合成関数の受入とは独立**。未実施の検証は成功と報告しない。Pure Pythonの固定合成のみにつき`Device QA: NOT_REQUIRED`。画面接続時には別PRで#372に記録。

## 後続ゲート

1. 本PRは`pipeline/**`だけ。最新main・required `test`・既存全D/C/B/E回帰を通すこと。
2. 次段階で公式ソースを参照する場合、A証拠、C原本照合、D公式記号の意味、個別施設同一性・時点、利用許諾に対する**人間の独立受入**が必要。`UNKNOWN`が残る限り勝手に候補扱いしない。
3. UIから条件を選ぶ際には、事前設定保存/同意・画面ライフサイクル・S0連携Contractを別途審査する。現時点のF05 Draft #371には影響なし。

**本PRのPASSは「架空の条件抽出が決定論的に再現できた」のみ。MVP展示・災害時利用・一般配信の承認ではない。**
