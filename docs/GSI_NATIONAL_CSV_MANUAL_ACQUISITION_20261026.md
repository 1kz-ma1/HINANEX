# GSI指定緊急避難場所・全国CSVの手動1回取得（2026-10-26）

この実行入口は **人間の明示同意 + workflow_dispatch専用**。データ取得・一時保管・C人間による受入は別工程。CIでは実CSVを取得せず合成テストのみ。

必要なPR: A #319 → A #321（CSV取り込みと原本取得）。このワークフローだけをmainへ反映しても依存コードがない場合は失敗。

公式のCSV列定義: https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html
国土地理院のご利用上の注意: https://www.gsi.go.jp/bousaichiri/hinanbasho-menseki.html

CSV配信候補URLはGSIドメイン上の全国CSV https://hinanmap.gsi.go.jp/hinanjocp/defaultFtpData/csv/mergeFromCity_2.csv だが、現在の実行環境はDNS失敗のため直接の配信確認ができない。このWorkflowを手動実行してもHTTP不達、パス変更、CSV形式不一致ならBLOCKし、未掲載・ゼロ件とみなさない。

## 手動実行
依存PRをmain統合し、新しいワークフローをmainに反映してから GitHub → Actions → GSI national emergency CSV manual source capture (UNREVIEWED) → Run workflow。
表示される国土地理院利用注意事項を事前に読んだ人が、研究用の短期間の原本アーティファクト保存も認識した場合だけ `acknowledged_gsi_terms=true` にして手動実行。

取得が成功したときだけ、元CSV、原本バイトSHA256、取得時刻/HTTP観測値、Aの未承認CSV検査、注意事項を3日間のActionsアーティファクトに保存する。
それでも**公式内容の最新版・原本の真正性を独立に認証していない**。C #320の別原本照合を行い、その結果も候補一致に止める。C人間による承認、実際の指定状態、案内可能な入口、現在の開設、経路安全性は別途必要。

自動定期実行、Render/GISとの接続、入力された実情報の公開は一切行わない。