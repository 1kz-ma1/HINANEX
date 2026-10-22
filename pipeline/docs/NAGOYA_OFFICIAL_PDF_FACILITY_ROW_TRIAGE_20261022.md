# 名古屋P1・9施設：公式PDF表の行単位差分候補（2026-10-22）

この独立Dツールは、公式PDF5件のバイト変更があった場合に、P1の9施設のうち、PDF表から抽出した施設ごとの行テキストにも変化があったかを判定する。**災害適合性、現地位置、開設情報、地図掲載を自動承認しない。**

## 分離した安全境界

- 固定公式PDF5件だけを人間の明示コマンドでHTTPS取得。PRIVATE CSV、候補座標、GSI実験レコード、認証情報は扱わない。PDFの原本や抽出本文は配布/保存しない。
- 初回の施設行baselineでは、既存の `official_pdf_snapshot_LOCAL.json` と再取得した5PDFのSHA256・バイト数を**全件一致**させる。違えば中止し、古いbaselineを改変しない。
- PyMuPDFの文字位置を用い、PDF同一行内に**名称+掲載住所**が一意に対応するものだけの行文字列SHA256を記録。曖昧・抽出不能は `UNRESOLVED`（人の確認が必要）として保持。
- 施設ごとの比較結果は、`ROW_TEXT_CHANGED_HUMAN_REVIEW_REQUIRED`（当該行の変化候補）、`ROW_TEXT_UNCHANGED_SOURCE_CHANGED_REVIEW_REQUIRED`（当該行は一致したがPDF全体が変化し、別箇所や凡例の意味が変わった可能性）、`ROW_EXTRACTION_UNRESOLVED_REVIEW_REQUIRED`（抽出不能）、`SAME_BYTES_DIFFERENT_EXTRACTION_HUMAN_REVIEW_REQUIRED`（抽出器が不安定）などに区別。
- `SOURCE_BYTES_UNCHANGED_NOT_OFFICIAL_APPROVAL` はこの比較のPDFバイトも抽出行も一致した意味のみ。指定施設の安全、運用、所在地、実際の入口や階数条件は依然**未検証**。
- 出力は既存ローカル作業ディレクトリ内だけ。上書き禁止、Git/Renderへ自動アップロードなし。RegionExportやGISの契約は変更しない。
- PDF全体の文字や注記・指定記号を完全に解釈するものではない。対象はP1の9施設のみで、追加施設の発見や避難の安全判定はしない。

## Mac実機の実行例（Draft PRの最新版を手元へ取り込んでから）

依存は本番 requirements.txt とは別の `requirements_nagoya_pdf_triage.txt` に記載。実機のPython環境にのみ任意インストールする。

```bash
cd ~/Developer/HINANEX
git fetch origin refs/pull/296/head
# 一時ファイルの書き出しに成功してから新しいファイル名へ配置する
git show FETCH_HEAD:pipeline/triage_nagoya_pdf_facility_changes.py > pipeline/triage_nagoya_pdf_facility_changes.py.tmp
test -s pipeline/triage_nagoya_pdf_facility_changes.py.tmp && mv pipeline/triage_nagoya_pdf_facility_changes.py.tmp pipeline/triage_nagoya_pdf_facility_changes.py
git show FETCH_HEAD:pipeline/requirements_nagoya_pdf_triage.txt > pipeline/requirements_nagoya_pdf_triage.txt.tmp
test -s pipeline/requirements_nagoya_pdf_triage.txt.tmp && mv pipeline/requirements_nagoya_pdf_triage.txt.tmp pipeline/requirements_nagoya_pdf_triage.txt
cd pipeline
source .venv/bin/activate
python -m pip install -r requirements_nagoya_pdf_triage.txt
python triage_nagoya_pdf_facility_changes.py --mode baseline --pilot-dir data/geocoding_pilot/nagoya50
python triage_nagoya_pdf_facility_changes.py --mode compare --pilot-dir data/geocoding_pilot/nagoya50
```

生成物は `official_pdf_facility_snapshot_LOCAL.json` と `official_pdf_facility_comparison_LOCAL.json`。既に存在する場合は上書きせず、後続比較は `--output-name official_pdf_facility_comparison_round2_LOCAL.json` とする。

## 受入上の未完事項

合成PDFバイトと独立抽出器によるCIテストは実装済みだが、**実PDF文字抽出で9施設すべてMATCHEDになるかは未検証**。合致数が少ない場合、誤判定で穴埋めせず本文のレイアウトを確認して処理を再設計する。Windowsでのオペレーター実行、資料本文の意味の再評価、班員HTMLへの自動投入は未実施。Draft依存 #283→#293→#295→後続PR。
