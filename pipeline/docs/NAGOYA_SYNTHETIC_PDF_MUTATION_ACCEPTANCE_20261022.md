# 名古屋P1：実体のある合成PDFで改版ケースを検証（2026-10-22）

## 目的

既存のPDF5ソース監視（#295）と施設行比較（#296）を、実際に生成した**検索可能な合成PDFのバイト列**に通し、実際の改版時の誤判定を予防する。公式PDFの変更・座標・施設承認を行わない。

このファイルはDの手動試験手順。テスト用PDFは**保存しない**。すべてPyMuPDFでメモリ内に生成し、架空施設名「架空…施設」・架空住所「架空…町」・資料本文「HINANEX SYNTHETIC TEST ONLY - NOT OFFICIAL」だけを使う。公式の区名・PDF URLはソース識別キーにのみ利用し、HTTPS通信は**ゼロ**。本番/Render/RegionExport/GISを変更しない。

## 操作（Macの既存仮想環境）

```bash
cd ~/Developer/HINANEX
git fetch origin refs/pull/297/head

# 既存のStage 7 CSV、baseline、比較結果を一切変更しない
TARGET="pipeline/manual_accept_nagoya_synthetic_pdf.py"
TEMP="${TARGET}.tmp"
if git show FETCH_HEAD:pipeline/manual_accept_nagoya_synthetic_pdf.py > "$TEMP" \
  && test -s "$TEMP"; then
  mv "$TEMP" "$TARGET"
else
  rm -f "$TEMP"
  echo "取得失敗"; exit 1
fi

cd pipeline
source .venv/bin/activate
# 既にPyMuPDFを導入済みなら再インストール不要
python manual_accept_nagoya_synthetic_pdf.py
```

対象は8シナリオ、**実体のあるPDFバイト**をPyMuPDFのテキスト抽出器へ通して評価する。

| ケース | 期待する検証境界 |
|---|---|
| 無変更 | 9件抽出・変更候補0・再確認0（このテストの比較のみ） |
| 未登録施設の追加 | 既存9件の行は同一でも、その区のPDFが変わるため当該区の人間確認を残す。追加施設の認可や自動追加はしない |
| 既存施設の削除 | 元の名称・住所ペアが見つからず `UNRESOLVED`。削除確定とは断定しない |
| 施設名の変更 | 対応名が消えるため `UNRESOLVED`。自動改称確定・ID付替えをしない |
| 掲載住所の変更 | 元住所ペアが消えるため `UNRESOLVED`。移転・敷地位置を自動確定しない |
| 同じ施設行の備考変更 | 行文字列ハッシュが変わるため `ROW_TEXT_CHANGED...` 候補 |
| PDF下部の注記変更 | 行テキストは同一でもPDFバイト変更により当該区を再確認 |
| PDFメタデータだけの変更 | 行一致でも当該区のPDF再確認。公式本文変更確定ではない |

完了した場合は `"all_passed": true` と `"scenario_count": 8`。5区分に分けた9架空施設が対象。入力PDFはファイル保存せず、公式PDFに対する接続はしない。**手動合成PDF実行は、CI内のunit testsとは別の検証**として記録する。

## 状態の意味

- `row_changed_candidates=1`: 対応付けられた文字列行の**変更候補**。資料意味や指定の変更確定ではない。
- `unresolved=1`: 元の名・住所で行を1対1に再特定できない。新しい名前/住所、削除、テキスト崩れを確定しない。
- `human_review_required=3`: 3施設が対象区の公式PDF変更に巻き込まれて追加確認へ残る。3施設それぞれが改版されたという意味ではない。
- `approved_for_map=false`, `data_promotion_authorized=false`, `official_facility_positions_accepted=0` は常に不変。

## 限界と次段階

これは意図的にレイアウトの単純な合成PDFを用いた**回帰試験**であって、複雑な表・セル結合・多段注記を含む全自治体のPDFに対する検証ではない。公式PDF実データでの行抽出成功9/9は既存PR #296でオペレーターのCLI出力により確認済み。ただし抽出行が対応する元PDFセル・付随注記を完全に含むか、人間の独立目視レビューは未実施。

- **新規施設を発見できた**とは主張しない（今回の処理は既存9件を監視するだけ）。
- **改称・住所変更を同一施設として追跡できた**とは主張しない（未解決として保留）。
- ページ余白の変更、年度更新、凡例変更、スキャンPDFは引き続き原本を確認する。
- 安全上の承認をする権限はこのコードに存在しない。PR #283→#293→#295→#296→当PRの依存を保ち、DraftのままCIと実機確認を区別する。
