# 江戸川区：学校移転・統合に関する公式原本の追加収集（2026-10-13）

**A evidence-only / 未承認・洪水Scenario変更なし**

Issue #141（平井南・下鎌田・瑞江・三葛西の施設移転・住所/座標差分）の調査用に、現行の7件の水害・位置原本及びGSI全国CSVから**完全に独立した**学校沿革原本セットを追加取得した。

## 再現可能な取得と原本ハッシュ

- 実行：GitHub Actions https://github.com/1kz-ma1/HINANEX/actions/runs/38337817800 （campus-history A取得・C検証ともSUCCESS）
- 取得日時：2026-10-13T02:38:27.571282+00:00
- GitHub private UNAPPROVED artifact: #11784419684、7日保管・期限2026-10-20。ZIP SHA256 **6b324ec18da0cc475d1ca9b3b58ba38af68154a5955d58e56171c37aa8a320fc**。
- 元ファイルを一括ZIPから展開し、manifest内のSHA256と各**実バイトを独立再照合して7/7一致**。Gitには原本・出力をコミットしない。
- A取得コード: data-research/tools/archive_edogawa_campus_history.py; A負系tests: data-research/tests/test_archive_edogawa_campus_history.py。
- HTTPS取得は www.city.edogawa.tokyo.jp の明示リストのみ。HTTP status、最終URL、source key、Original byte length、SHA256、UTC、Content-Type、Last-Modified、ETag を保存。Last-ModifiedはHTTPヘッダーであり、**公式発行日や施設の適用日を代替しない**。

| Key | 出典・形式 | SHA256 |
| --- | --- | --- |
| hirai_minami_rebuild | 平井南小学校 改築の概要 HTML・2026年7月7日ページ更新 | ffc85ecabea7e44984789512c595b5fc90453761942db7becc79a8dd1c6a81f9 |
| edogawa_school_rebuild_index | 学校改築の状況と予定 HTML | 55db737184f988a4c6b159793733953a0da263e223c3b07bdae93274e49c0a8e |
| shimokamata_rebuild | 下鎌田小学校 改築の概要 HTML・2026年3月11日ページ更新 | 3a11b6296bc32289669f2efd4f73e03f51bc90fb7896b47e1103921108ed3b7a |
| shimokamata_integration | 下鎌田地域小学校の統合・改築について HTML・2025年12月5日ページ更新 | 2f175d89c9ae08bfd2670ea8e0aaef06d93d0567f4e3ec0d65dfa351c9833089 |
| school_district_map_guidance | 通学区域図と校舎適用時期の注記 HTML・2025年4月7日ページ更新 | a0e0d2e0103ef1ae6e6e73cbd9e15c1d9d643b68d978a552b41c3c20dd9a05e9 |
| historical_shimokamata_site_plan_2021 | 江戸川区 下鎌田2校統合校・改築基本構想 PDF（2021年3月策定版） | 8aa8534b189440f0c13b9cdb30236e40b985a26fc6ef14f278144cd614f294af |
| historical_hirai_board_minutes_2024 | 江戸川区教育委員会 第20回会議録 PDF（2024年10月28日） | 4f07a382c9a5c3fe769297f201d1a5cfdfdd3344f702b9f50568175fb3ad5c63 |

**Source URLs** は原本Manifestを正とする。旧Cの施設位置CSV SHA256 64b1...、水害施設HTML SHA256 9600...、GSI全国CSV SHA256 e75b...とは異なる独立バージョンとして扱う。

## 時点別の原文観察（行政上の適用・敷地同一性は未承認）

- 下鎌田小学校：2021年3月基本計画の敷地図（PDF物理ページ5、印刷ページ1）に旧下鎌田小学校＝**東瑞江3丁目11番1号**、旧下鎌田西小学校＝**瑞江4丁目19番10号**と別校舎で掲載。2023年4月統合、2025年5月に旧下鎌田西の土地上の新校舎竣工、2025年9月から新校舎運営という区の2026年3月更新ページを確認。2025年4月更新の通学区域図案内は「2025年9月までは東瑞江3丁目11番1号」と明記。**2025年12月更新の水害施設リストが旧住所を示す一方、2026取得のGSIは新住所を示す**。公式の災害指定先が旧・新どちらの実敷地かはここから確定しない。D CSVの座標は静的データとしてそのまま。
- 平井南小学校：2026年7月更新の改築概要は旧小松川第三中学校を仮校舎とし、2029年9月の新校舎利用開始を予定。2025年以前の会議録や古い学校関連資料の工期は改訂され得るため、**2024議事録＝2026現行の学校運営時点とは断定しない**。2026年時点の水害待避施設指定場所が元本校舎・仮校舎のどちらかは別途検証。
- 瑞江小学校：今回の沿革原本7件だけでは、約107mのGSIとD代表点差の根拠が説明できない。
- 三葛西小学校：水害一覧の不規則住所「北葛西4丁目番2番19号」を修正せず保存。今回の沿革原本7件だけでは自治体正式訂正は見つからない。

2021/2024のPDFについて、構造（PDF magic・終端）・出典・生バイトハッシュは自動検証した。PDF内容の**独立した人間Cレビュー署名はない**。この調査ノートの目視確認事項は正式なCレビュー承認ではない。PDFの転載可否/ライセンスは未審査、必要な範囲の出典表示・利用許諾を別途確認。

## 運用上の制約

本原本取得により「どの資料に何が書いてあるか」を強化したが、出典の日付＝洪水待避指定の有効日ではない。旧学校敷地→新学校敷地の自動join禁止。名前・住所・代表点が一致してもC人間が指定された敷地・施設・時期を確認し、D/Cが水害待避 vs 洪水単独の制度・条件を独立検証するまで、**承認0件・CANDIDATE/EXCLUDED追加0件**を維持する。

C原本監査・4施設レビュー: validation/reviews/2026-10-13-edogawa-campus-era-original-audit.md 。Issue #141/#134 に経緯・引継ぎを記録。3地域統合、本番/stagingへの反映は未実施。
