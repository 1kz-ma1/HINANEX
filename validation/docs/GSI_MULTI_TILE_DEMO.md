# 10/22 HINANEX — 位置情報に連動した複数タイルの受入手順

GSI指定緊急避難場所（洪水）skhb01 は GeoJSON z=10 のタイルです。**3自治体のD RegionExport**（Edogawa 152 / Niigata 566 / Nagoya 1602 など）と、**位置情報に応じて選ぶGSIの参考施設**は別レイヤーです。

## 実装済みの役割分担

- **A/D:** 各z10公式タイルのraw GeoJSONを正規化し、C raw監査PASS + 公式HTTPS再取得MATCHがないものはREFERENCE_ONLYを発行しない。
- **C:** rawバイト、全feature_index、URL、原文名・住所・座標・災害1=1、監査参照、HTTP再取得・SHA256を独立検査。各タイルごとに受入。
- **E:** ユーザーの明示地点からz10原点タイルと最大8周辺タイルを計算し、**静的配信された検証済み**参考JSONだけを参照。起点タイルなし・不正タイル・不正URL・不一致ならfail closed。未配信の隣接タイルを「避難場所なし」と扱わない。
- **B:** 従来の3自治体RegionExportを継続表示。UNKNOWNはUNKNOWNのままで、GSIにより安全候補へ変換しない。

## 実データを用いたWindows準備（既存worktreeを保護）

前回の`C:\HINANEX-Accept`等を保持し、**新規**worktreeを作成します。

~~~powershell
cd C:\HINANEX
git fetch origin
git worktree add --detach ..\HINANEX-Multi origin/integration/flood-scenario-preview
cd C:\HINANEX-Multi

# 例：地図の任意地点。最初は起点タイルだけ検証・保存（未公開）。
& .\validation\scripts\Prepare-GsiDemoTiles.ps1 -Latitude 35.70 -Longitude 139.90 -RegionCode 13123

# 起点タイル＋最大8周辺タイルをそれぞれ独立監査し、全工程が通ったものだけ
# 新しいworktreeの静的GISに配信する場合（ネットワークが必要）。
& .\validation\scripts\Prepare-GsiDemoTiles.ps1 -Latitude 35.70 -Longitude 139.90 -RegionCode 13123 -IncludeNeighbors -PublishPreview
~~~

**注意**：一度公開したタイルを同じ配信パスに再公開する場合は上書きを拒否します。試行は必ず新規の検証フォルダに記録されます。事前に作成済みの`edogawa_flood_site_catalog.json`はそのまま保持されます。

個別の保存済みタイルを再利用する場合は、`Run-GsiFloodLocalAcceptance.ps1 -ArchivePath <raw> -SourceUrl <official z10 URL> -ExpectedSha256 <saved digest> -RegionCode 13123 -PublishPreview`を使います。新しいrawに対して従来のハッシュを暗黙適用しません。

公開される静的ファイルの例：
`pipeline/data/output/gsi_verified_tiles/13123/10-909-403.json`

Eはあくまで同一originで配信されたファイルを参照します。**GPS座標そのものをHINANEXへPOSTしません**が、タイルIDをGETするためホスト側には概略地域が分かります。公式ダウンロードスクリプトはユーザー操作時にGSIへタイルURLを要求します。公開済みタイルがなければ正しく「未検証」と表示します。

## 受入とデモの限界

- 起点タイルへの地図クリック、境界付近のクリック、GPS拒否、連続クリックによる古いレスポンス上書き防止、地域切替、出典リンクとraw値を検証。
- 近隣タイルが未配信なら、検証済み範囲に限った直線距離順であり「地域全体の最寄り」ではありません。
- タイルは自治体境界に一致しません。資料の1195件は1タイル内の件数で、江戸川区内の施設数や網羅性ではありません。
- 指定緊急避難場所の掲載は**現在開設、安全、避難経路、最適な行き先**を保証しません。地元自治体の最新案内に従います。
- 本番の全国網羅を主張しません。公開範囲と未検証範囲を区別して見せます。
- 本工程では`main`に統合しない。Merge Captainのリリース判定と新潟ODS #48は独立した確認項目です。

参照：国土地理院「地理院タイル一覧」（skhb01/指定緊急避難場所・洪水）、https://maps.gsi.go.jp/development/index.html
