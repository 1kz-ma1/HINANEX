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
