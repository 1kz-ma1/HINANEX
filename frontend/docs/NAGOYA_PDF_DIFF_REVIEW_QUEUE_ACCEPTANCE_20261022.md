# 名古屋施設別PDF差分 → 班員レビュー・確認優先キュー（Draft #298）

## 入力するファイル（区別）

1. **基準の施設レビューJSON**: `team_review_p1_sources_LOCAL.json` 等、#293の出力形式 `schema_id=hinanex.team-review.v1`。9件のP1施設、各施設に名古屋市の該当区の公式PDF URLを含む。
2. **別ファイルの施設別PDF差分JSON**: `official_pdf_facility_comparison_round2_LOCAL.json` 等、#296の `report_kind=NAGOYA_P1_PDF_ROW_DIFF_CANDIDATES_NOT_OFFICIAL_APPROVAL`。今回のMacで `row_changed_candidate_count=0` / `human_review_required_count=0` だった実出力を利用可能。**注意：単なるバイト監視 `official_pdf_comparison_LOCAL.json` や合成実験の `NAGOYA_SYNTHETIC_PDF_MUTATION_TEST_NOT_SOURCE_APPROVAL` は別形式なので読込不可。**
3. **班員の提出したレビューJSON**: 上記1から班員が記録し、`hinanex-team-review-*.json` として保存したもの（既存の「まとめて取り込む」機能で統合）。

差分JSONはブラウザー内で参考表示するだけ。**班員レビューJSONに新フィールドを追加せず、書き出す際にも差分を混ぜない**。毎回HTMLを開いたら基準JSONと必要な差分JSONを明示選択する。

## UI操作と判定

- 先に `team_review_p1_sources_LOCAL.json` を読み込む。次に「施設別PDF差分JSONを読み込む」で `official_pdf_facility_comparison_round2_LOCAL.json` を選択する。
- **すべての9施設**の名称・住所・公式PDFリンクを照合してから参考表示する。source_fingerprintは差分JSONにないため暗号学的な結合ではない（この制限を画面にも表示）。誤った地域や元データ、件数/安全フラグ/変更分類の改ざんは拒否。
- 読み込めたら上部に「再確認X件／行の変更候補Y件／抽出未解決Z件／取得時刻」が出る。
- 「PDF差分による絞り込み」の「今回のPDFで再確認が必要」「施設行の文字列変更候補」「抽出未解決・抽出結果の不整合」「PDF自体が更新された施設」「今回のPDFで行の変更候補なし」で整理する。
- 以前のレビューが「根拠あり」でも、PDF変更で確認対象になった場合はデフォルトの「根拠・確認が未完了の施設だけ表示」から隠さない。
- 今回の実PDFでは9件とも抽出一致・行の変更候補0のため、差分表示は「新たな変更候補なし」。しかし**既存の施設レビューは全部が正式未承認**であり、文書差分の無変更だけで人間の施設位置確認や安全評価は完了しない。
- 差分の入ったレポートの読込はレビュー状態・チェック・根拠URL・メモを**変更しない**。班員提出JSONと安全flagsも変えない。
- ベースの新JSONを読み込むと、以前の差分表示は破棄する。旧差分を別の基準へ黙って引き継がない。
- 文字列変更があっても「実在の施設が改称・移転・削除した」と断定しない。追加施設はこの9件のスコープ外で、元PDFが変化した区を人間が確認する。
- 差分の根拠となる原文PDFは班員が別途開いて照合する。ブラウザーからリモート送信はしない。

## 手元Macで最新HTMLを受入する

既存の `team-review-v2.html` とPRIVATEファイルを残し、v3の名前で取り出す。

```bash
cd ~/Developer/HINANEX
git fetch origin refs/pull/298/head
OUTPUT="pipeline/data/geocoding_pilot/nagoya50/team-review-v3.html"
TEMP="${OUTPUT}.tmp"
if test -e "$OUTPUT"; then
  echo "既にHTMLがあるため上書きしません: $OUTPUT"
elif git show FETCH_HEAD:frontend/team-review.html > "$TEMP" && test -s "$TEMP"; then
  mv "$TEMP" "$OUTPUT"
  open -a Safari "$OUTPUT"
else
  rm -f "$TEMP"
  echo "PR #298のHTML取得に失敗"
fi
```

試すこと：名古屋P1基準JSONを先に読み込む → 上の差分JSONを追加読込 → 9件／差分追加確認0を表示 → 差分フィルタで「今回のPDFで再確認が必要」は0件／「行の変更候補なし」は9件 → 班員のメモ・根拠URLの入力とJSON書き出しを従来通り実行。合成資料の未承認のデータを入れた異常JSONは拒否されること。Windows Edgeの同等動作はまだ確認していない。

## CIと依存

- Bの自動回帰は `frontend/tests/team-review.test.js`。既存データと座標を一切使わず、架空9施設に付いた公式PDF URL・差分を作って検証。
- 正本となるPDF差分レポートはDの #296（#297が合成PDF変更検知のテスト）。BのDraft #298は独立したHTML（Bの#292依存）だけを変更し、`pipeline/**` やRegionExport/共有契約は変更しない。
- Scope/merge: #283→#293→#295→#296→#297（Dの積上げ）、B側 #292→#298。**最新main追従・Windows/Mac実機確認・人のMerge Captain判断前にmainへマージしない。**

## 2026-11-25 再審査・親同期

- 厳密UTC暦・固定5 PDF URL→区対応・URL集計・遅延読込時の旧状態保持を追加した。旧親baseでのCI成功は新baseの成功と区別する。
- 親#292の未保存本人確認と公開導線なしを継承。実機・D依存・配布許可・Deploy非公開候補bundle検証は未了。

## 2026-11-27 #495 配布境界の整理

公開READMEの班員限定PDF差分説明は以下に省略せず移管しました。親#292の公開README/build-checkをmain同一に戻す方針と、既存非公開テストへの検査移管を継承します。#495のDeploy別PR・実候補コピー・配布決裁は引き続き必要です。

### 名古屋P1の施設別PDF変更候補を閲覧する（Draft #298）

- 班員用 `team-review.html` は、既存の `hinanex.team-review.v1` とは別に、Dの `NAGOYA_P1_PDF_ROW_DIFF_CANDIDATES_NOT_OFFICIAL_APPROVAL` 比較JSONを**任意に**追加読込できる。入力順は施設レビューJSON→施設別PDF差分JSON。バイト監視だけのJSONや合成変更試験レポートは受け付けない。
- 対象は名古屋Stage7 P1の9施設だけ。全レコードの施設名・公式掲載住所・資料URL（`www.city.nagoya.jp`のPDF）が一致し、差分分類・集計・安全フラグが厳格に整合する場合のみ参照表示。未知の項目・座標・未承認フラグ変更は拒否。
- 画面に「行文字列変更候補」「抽出未解決」「PDF全体の更新（行は同じ）」「今回のPDFで行の変更候補なし」を表示し、絞込できる。既にレビュー完了扱いでも、PDF更新で再確認対象になった施設は隠さない。
- 比較は**参考情報だけ**。作業済みの `review.status`・根拠URL・チェック・メモを変更せず、結果JSONへPDF差分情報を混在させない。HTMLを開き直した場合は別途再読込が必要。
- DレポートにStage7の `source_fingerprint` がないため、**名寄せ・PDF URLの対応だけを確認**し、別時点のStage7出力との厳密な結合は主張しない。公式原文の意味・現地位置・指定災害・開設・安全性についての承認はない。
- Mac SafariとWindows Edgeの更新版操作はまだ独立確認されていない。手順：`frontend/docs/NAGOYA_PDF_DIFF_REVIEW_QUEUE_ACCEPTANCE_20261022.md`。B Draft #292→#298、D Draft #283→#293→#295→#296→#297。main/Render未反映。

- 親#292のローカル限定・公開導線禁止・配布除外ゲートを継承。本追加受入文書も配布除外の対象とする。
