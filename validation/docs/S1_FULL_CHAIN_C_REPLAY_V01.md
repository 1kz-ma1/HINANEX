# C独立検証 — S0 → S1-P0 → P1 → P2 固定合成フルチェーン v0.1

**2026-11-16 / C独立・合成のみ / NOT PUBLIC・NOT OFFICIAL ACCEPTANCE**

## 目的と責務
Issue #305の「訓練を開始 → 条件抽出 → 根拠を比較 → 本人の明示的レビュー選択 → 停止・失効時に破棄」を、mainの**実際のD実装**に接続してCが独立検証する。DのロジックをCで再実装しない。単なるメソッド単位テストでも、B画面上のE2Eでもない。

参照するmain統合済みD実装:
- S0 `pipeline/src/hinanex/drill_session.py` — PR #376。
- S1-P0 `pipeline/src/hinanex/s1_synthetic_narrowing.py` — PR #391。
- S1-P1 `pipeline/src/hinanex/s1_synthetic_comparison.py` — PR #394。
- S1-P2 `pipeline/src/hinanex/s1_synthetic_review_choice.py` — PR #397。

変更範囲は **`validation/** のみ**。D・B・E・共有Contract/Schema・公式原本・GSI・Render・通知・ユーザー設定は変更しない。既存S0の独立リプレイ（#384）、S0→UI Contract草案Draft #386/#387とは独立であり、後者は未承認のまま保留する。

## ファイルと検証方式
- `validation/fixtures/s1_full_chain_c_replay_v01.json`: **1つの固定合成シナリオ**、6つの架空 `synthetic:` レコード、21の連続ステップ（9イベント/12チェック）、TZ付き固定時刻、条件は架空の `pet_support` / `step_free` のみ。
- `validation/validation/verify_s1_full_chain_replay.py`: 実際の `reduce_session` / `safe_view` / `narrow_synthetic_references` / `compare_synthetic_conditions` / `choose_synthetic_for_review` をそれぞれ呼び出し、**Cの固定期待値**と照合する。P0/P1/P2は各段階を独立に呼び、前段の出力だけを後段の期待値にはしない。
- `validation/validation/test_verify_s1_full_chain_replay.py`: 23件のC独立回帰。期待値改ざん・LIVE偽装・P1件数偽装・P2によるUNKNOWNのMATCHED昇格・BLOCKED中のID復活を注入して、正常なCIで検知できることも確認する。

## 実際に追う操作の意味

1. 合成fixtureでDRILL開始。現在の合成文言・世代・期限をS0から観測。
2. 2つの合成条件をAND評価。1件`MATCHED_SYNTHETIC`、1件`NOT_MATCHED_SYNTHETIC`、4件`UNKNOWN`。6レコードの比較理由・件数と、独立した固定期待値を照合。
3. 1件の`UNKNOWN`を利用者の明示アクションで**レビュー対象としてのみ選択**。未確認条件と元の分類を保持する。`NOT_MATCHED_SYNTHETIC`も閲覧のために選べるが、適合/開設/安全へ変換しない。
4. 明示アクションがない場合の拒否、STOP_DRILL後の空結果、再開時の旧generation選択拒否、新世代の明示選択を確認。
5. SELECT_REGIONで既存結果破棄、古いSTART_DRILL非同期イベント拒否、30分の期限終端でreducer tickなしでも古い結果を拒否。
6. SOURCE_FAILED、期限切れfixtureでの再開拒否、RESET後も抽出・比較・選択を空にする。

`UNKNOWN`を`EXCLUDED`に変換しない。`NORMAL`はライブ情報受信済みを意味しない。避難所の安全・開設・公式災害指定・経路/現在地・要配慮者事情は、このテストが存在を証明しない。実施設名/住所/GPSは含めない。

## Fail-closed・独立安全条件

- S0の`DRILL_NOTICE`と`SYNTHETIC_TEST_ONLY`、固定fixtureの出典/地域/災害/期限、`NORMAL`の旧fixture非表示、`live_data_verified is False`をCが検査。
- P0/P1/P2の全Reportで`synthetic_only is True`、公式受入/LIVE/施設・経路安全/公開承認は**厳密にFalse**。
- P0/P1のID・status・reason_code・missing・failed、合計件数、P2の選択ID・元のUNKNOWNや非一致の分類・条件を突き合わせる。
- 上流にBLOCKEDが出た場合はP1の`rows=()`・`required_conditions=()`・件数0、P2の選択ID/条件が空であることを要求。旧状態が残ればFAIL。
- ケース定義そのものが不正/欠損ならBLOCKED（合格にしない）。固定期待値と実出力の相違や安全属性偽装はFAIL。正常な再生のみPASS。未実施の端末QAはNOT_RUN。

## 実行・出力と判定

リポジトリrootから:

~~~sh
python validation/validation/verify_s1_full_chain_replay.py --json
python -m unittest discover -s validation/validation -p 'test_verify_s1_full_chain_replay.py' -v
~~~

合成入力だけを使い、ネットワーク/保存/原本取得/デプロイ操作なし。`regression=PASS` は期待値と合成実出力の**再現性のみ**。`official_acceptance=false`、`facility_safety_verified=false`、`route_safety_verified=false`、`public_release_approved=false`、`device_qa=NOT_RUN`を報告し、CI上の検証範囲とデバイス受入を混同しない。

**Device QA区分:** C純粋Python検証は`NOT_REQUIRED`。出力の`device_qa=NOT_RUN`は実機自体が未実施であることを表す。今後のB/E UI接続時の端末QAと独立の受入はIssue #372で追加する。

## 依存・完了条件
- 前提#376/#391/#394/#397はmain統合済み。新PRはC領域だけを変更して、mainへScope Guardで確認する。
- Required `test` と新規C23テストを含む全回帰成功、main更新確認が必要。機能本番導入・共有Contract採用・実データ安全性・公開許可ではない。
- S0→UI Draft #386/#387、koutaのF05 Draft #371、公式施設受入/利用規約ゲート#366は現状維持する。

**本C検証がGOであっても、実際の災害時に安全な避難先が選択できると結論付けない。**
