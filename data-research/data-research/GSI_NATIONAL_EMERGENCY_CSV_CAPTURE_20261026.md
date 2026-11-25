# GSI全国CSV 原本の明示的取得と未承認保存（2026-10-26）

このCLIは外部起動していない。全国CSV配信候補 https://hinanmap.gsi.go.jp/hinanjocp/defaultFtpData/csv/mergeFromCity_2.csv はGSIホスト上のURLだが、現時点の実行環境では公式サーバーへのDNS接続ができず、応答内容や正確な配信先かどうかは未確認。
公式列仕様: https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html 。利用条件: https://www.gsi.go.jp/bousaichiri/hinanbasho-menseki.html

既にAで作成したパーサーの全国版原本処理上限を16MBから32MBへ拡大。元のCSVが16MBを超える場合も上限内なら受け取れる設計（実ファイルのサイズはここでは未計測）。HTTP取得は固定HTTPSホスト、TLS検証、リダイレクト禁止、25秒期限、最大32MB、200のみ。

利用者がGSIの利用条件を実際に確認し、情報取得を明示的に認める場合だけ次のように実行する。
python data-research/tools/capture_gsi_emergency_csv_original.py --fetch --acknowledged-gsi-terms --out-dir /outside-repo/gsi-emergency-national-UNREVIEWED

既存フォルダ・Git内部への保存は拒否。原本CSV、A検査レポート、HTTPヘッダーの観測値とハッシュを含む未承認マニフェストを保存。
CSV取得失敗・URL違い・列数/ハザード指定フォーマット違いはUNKNOWN/BLOCKEDとして扱い、指定場所ゼロにはしない。
原本の真偽や自治体版の更新状態、Cによる独立照合、CSV共通ID→GeoJSONの同一性を**承認しない**。
本PRは #319 のAオフライン検査に積む追加差分。合成fixture以外の実通信はCIで実行しない。