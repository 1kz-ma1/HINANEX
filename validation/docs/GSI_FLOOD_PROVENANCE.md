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


## C→D→E 実データ・ローカル一括受入チェック

最新の統合プレビューには読み取り専用CLI：validation/validation/verify_gsi_catalog_acceptance.py があります。以下の順で実行してください。

1. 保存済みGSI rawからD整理レコードとC独立raw監査PASSのJSONを作成（元データは消さない）。
2. ネットワークが使える環境で前半記載の verify_gsi_flood_provenance.py を実行し、公式HTTPS再取得と原本バイトの MATCH レポートを生成。ネットワーク失敗や公式更新時は停止。
3. D run_verified_flood_site_reference.py へ --provenance を渡し、REFERENCE_ONLY カタログを生成。
4. 以下の読み取り専用チェックを実行。

PowerShell（最新previewの別worktreeに置いた正常な出力を検査）:

~~~powershell
cd C:\HINANEX-Accept
$py = 'C:\HINANEX\pipeline\.venv\Scripts\python.exe'
$source = 'https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson'
$raw = 'C:\HINANEX-Preview\pipeline\data\raw\gsi_flood_tile.geojson'
$records = '.\pipeline\data\verified\edogawa_gsi_flood_records.json'
$c = '.\pipeline\data\verified\edogawa_gsi_flood_c_acceptance.json'
$proof = '.\pipeline\data\verified\gsi_https_provenance_20261009.json'
$catalog = '.\pipeline\data\output\edogawa_flood_site_catalog.json'
& $py .\validation\validation\verify_gsi_catalog_acceptance.py --region 13123 --raw $raw --records $records --c-acceptance $c --provenance $proof --catalog $catalog --source-url $source
~~~

既存 C:\HINANEX-Preview の未コミット変更と原本を保持し、別worktreeを初めて作る場合:

~~~powershell
cd C:\HINANEX
git fetch origin
git worktree add --detach ..\HINANEX-Accept origin/integration/flood-scenario-preview
~~~

別worktree側で Dの prepare_gsi_flood_tile.py と Cの verify_gsi_flood_source.py を使い、元の保存済みrawから新規 $records と $c を作成してください。実際に公式HTTPSと一致したレポートだけを $proof とし、Dの公開CLIを --provenance $proof で実行して $catalog を生成します。既存証跡を消したり上書きしてはいけません。

正常終了時は LOCAL_CATALOG_CONTRACT_PASS とタイル全体の件数・SHA256を表示します。これは現場データの安全・開設・所属自治体やブラウザの操作確認ではありません。別途HTTP配信で3地域、施設原文、手動地点、GPS拒否、地域切替、ブラウザコンソールを確認します。最新の自治体避難案内を優先してください。


## まとめて実行する安全なPowerShellランナー

今後の実データ検証は、最新の統合プレビューを取得した**別worktree**から以下の1コマンドでも実行できます。元の C:\HINANEX-Preview に保存されたGSI原本や未コミットのschema修正は変更しません。

~~~powershell
cd C:\HINANEX
git fetch origin
git worktree add --detach ..\HINANEX-Accept origin/integration/flood-scenario-preview
& 'C:\HINANEX-Accept\validation\scripts\Run-GsiFloodLocalAcceptance.ps1' -ArchivePath 'C:\HINANEX-Preview\pipeline\data\raw\gsi_flood_tile.geojson'
~~~

スクリプトは新規の一意な検証フォルダにだけ、D正規化行、C raw照合、C実HTTPS照合、D参照カタログ、C→D→E整合性確認を出力し、EのNode回帰テスト5本を実行します。既定の原本SHA256は、ユーザーが2026-10-09に報告した2748FEA7E1145FD2A3BDFAD05B3FEA4B86127FAFD017F253FE327472F89A3A41です。別の原本を再監査する場合は -ExpectedSha256 で明示指定してください。値が違う場合やネットワークで再取得した公式バイトが変化している場合は停止します。

全工程が通ったあと、**新しいプレビューworktreeのみ**へ表示用JSONを配置する場合は最後のコマンドに -PublishPreview を追加します。公開先に既存ファイルがあれば上書きせずエラーにします。mainへのGitマージや実運用配信は行いません。

この一括PASSでも、B frontendテストと実ブラウザのGPS許可/拒否・地域切替・施設元情報・コンソールの受入作業は残ります。施設の自治体所属、避難適合性、安全経路、開設状況を認定しません。
