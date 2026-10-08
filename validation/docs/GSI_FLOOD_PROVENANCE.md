# C — GSI洪水データのHTTPS再取得・証跡

このチェックは、Cの既存`verify_gsi_flood_source.py`の**後**に実行します。まずCがローカル原本とD整理データを独立に照合し、そのPASS JSONを今回のツールに渡します。

## Windows PowerShell / integration preview

```powershell
cd C:\HINANEX-Preview
$py = 'C:\HINANEX\pipeline\.venv\Scripts\python.exe'
$source = 'https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson'
$raw = '.\pipeline\data\raw\gsi_flood_tile.geojson'
$c = '.\pipeline\data\verified\edogawa_gsi_flood_c_acceptance.json'
$report = '.\pipeline\data\verified\gsi_https_provenance_20261009.json'

& $py .\validation\validation\verify_gsi_flood_provenance.py `
  --raw $raw --source-url $source --c-acceptance $c --report-out $report
```

- **MATCHのみが成功**。別日配信等でバイトが変化した場合はエラーとなり、既存の受入JSONで新データを承認しません。
- `--report-out` に既存ファイルがあれば上書きしません。日付や実行時刻を変えた新規パスを指定してください。
- JSONにはアクセス時刻（UTC）、URL、HTTPステータス、受信ヘッダの一部、SHA256、C監査参照、件数を記録します。原本全体はレポートには含みません。
- Cがネット接続できない場合は**未検証のまま**です。ネットワーク失敗・HTTPエラーをPASS扱いしません。
- レポートとraw/normalized/C受入JSONは原則Git管理外に置き、監査エビデンスとして保持します。CIは合成データのテストのみ。
- HTTPS再取得の一致は、**その時点の公式配信バイト**との一致であり、以前のダウンロード日時の証明ではありません。また、GSIの1タイル内の施設が江戸川区内だけとは限らず、掲載網羅性・安全・開設・経路推奨も認定しません。自治体の最新案内を優先してください。

次の工程ではDの`run_verified_flood_site_reference.py`で`REFERENCE_ONLY`カタログを出力し、ブラウザから実データを読み込んで確認します。このレポートだけで`main`へリリースしてはいけません。
