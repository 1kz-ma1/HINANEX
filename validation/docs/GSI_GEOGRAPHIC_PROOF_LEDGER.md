# C — 地域横断のGSI洪水タイル証跡レポート（読み取り専用）

目的：Issue [#89](https://github.com/1kz-ma1/HINANEX/issues/89) の二次元検証に進む前に、**洪水について地域を変えても同一C受入基準で再検証できるか**を可視化する。これは **Phase 1 の証跡台帳**であり、全国展開・ブラウザ受入・災害種別一般化が済んだと意味しない。

## 入力と出力

`validation/validation/gsi_geographic_proof_ledger.py` は、以下のローカル生成物を読み取り専用で照合する。

- `pipeline/data/output/gsi_verified_tiles/<region>/10-x-y.json` — 既に公開済みのGSI洪水参考カタログ
- `pipeline/data/verified/gsi-acceptance-runs/<run>/` — Dレコード、C raw監査、**保存済み**C HTTPS MATCH報告、正式なDカタログ
- `pipeline/data/raw/gsi-demo-runs/**/10-x-y.geojson` — SHA256が一致する公式rawアーカイブ

公開JSONは**監査済みDカタログとバイト単位で一致**する必要がある。独立Cの `verify_local_catalog()` でrawとnormalized records・C監査・保存されたHTTPS照合・全座標のz10タイル整合まで再実行する。単に `status: C_ACCEPTED` と書いてあるだけのJSONは不合格。

### Windows実行（現在のworktreeを維持）

~~~powershell
cd C:\HINANEX-Multi
git fetch origin
git status --short
# 追跡対象に未保存変更がない場合のみ最新版へ
git switch --detach origin/integration/flood-scenario-preview

# 起点はユーザーが選んだ2か所。互いに異なるGSI z10タイル。
& 'C:\HINANEX\pipeline\.venv\Scripts\python.exe' .\validation\validation\gsi_geographic_proof_ledger.py `
  --region 13123 `
  --origin 35.70,139.90 `
  --origin 35.70,140.10

# 結果を証拠として保存したい場合は、新規ファイル名を指定（上書き拒否）
& 'C:\HINANEX\pipeline\.venv\Scripts\python.exe' .\validation\validation\gsi_geographic_proof_ledger.py `
  --region 13123 `
  --origin 35.70,139.90 `
  --origin 35.70,140.10 `
  --report-out .\pipeline\data\verified\gsi-local-proof-20261009.json
~~~

**注意**：公開済みとC証跡・公式rawが同じ `C:\HINANEX-Multi` 配下に必要。以前の別worktreeのJSONを参照しない。データが足りなくてもこのツールはダウンロードしないし、現存する監査証跡を削除・上書きしない。

## 判定の読み方

- `PASS_SAVED_C_EVIDENCE`：元raw、D正常化、C独立raw監査、保存済み公式HTTPS MATCH報告、公開済みカタログの一致を**現在のローカルファイルで再検証**できた。新規にHTTPS通信は行わない。
- `MISSING_PUBLICATION`：このworktreeに対象JSONがない。**公式データの不存在ではない**。
- `UNVERIFIED_C_EVIDENCE` / `UNVERIFIED_RAW_ARCHIVE`：データはあるが、証跡または原本が揃わず再検証できない。
- `BLOCKED_INCONSISTENT`：改ざん、契約不一致、誤タイル、保存されたC証跡の不一致など。参考データとして採用不可。
- `ORIGIN_UNVERIFIED`：起点タイルを再検証できない。周辺8タイルのデータだけで「近隣候補」を保証してはいけない。
- `PARTIAL_LOCAL_SOURCE_PROOF` / `FULL_LOCAL_SOURCE_PROOF`：最大9タイルのうち再検証できた割合のみを示す。自治体・日本全国の網羅率ではない。

`all_requested_source_tiles_locally_verified` は **2地点のローカルC証拠だけ**の判定。どんな結果でも `baseline_accepted` は **false**、GPS・ブラウザ・外部洪水ラスタ・3自治体のD出力・最終リハーサルは `NOT_TESTED` と出る。実機受入はIssue #89のチェックリストへ別途記録する。

`distinct_origin_tiles_sampled` は、繰り返し指定した位置が**異なるz10タイルに存在するか**だけを検査する。同じタイル内の2クリックを、地域変更の検証実績として数えない。

## 追加受入：地点Bで足りない3タイルだけ安全に拡張

2026-10-09 の実機C証跡台帳では2地点で異なるz10タイルが確認された。

- 起点 A \`10/909/403\`：**9/9 PASS**、タイル内掲載 **6,656件**
- 起点 B \`10/910/403\`：**6/9 PASS**、タイル内掲載 **4,205件**
- 未配信 \`10/911/402\`、\`10/911/403\`、\`10/911/404\`：**MISSING_PUBLICATION**。これは取得失敗/公式の施設不存在を意味しない。

既存の原本・証跡・公開済みJSONは変更しない。Cの独立再照合に合格した既存タイルだけをスキップし、足りないタイルを**新たに**公式URLから取得してC raw監査、公式HTTPSバイト再照合、Dカタログ受入、E Node回帰、静的配信まで一式実行する。

~~~powershell
cd C:\HINANEX-Multi
git fetch origin
git status --short
# 追跡対象の未保存変更がなければ:
git switch --detach origin/integration/flood-scenario-preview

& .\validation\scripts\Prepare-GsiDemoTiles.ps1 \`
    -Latitude 35.70 \`
    -Longitude 140.10 \`
    -RegionCode 13123 \`
    -IncludeNeighbors \`
    -OnlyUnpublished \`
    -PublishPreview
~~~

- \`-OnlyUnpublished\` は **\`-IncludeNeighbors\` および \`-PublishPreview\` が両方必要**。\`-NeighborsOnly\` との同時指定不可。
- 独立Cの \`gsi_geographic_proof_ledger.py\` を呼び、各公開済みタイルについて完全な保存済みC証跡と原本を再検証。単なるファイル存在ではスキップしない。**C不一致時は一件も取得せず停止**。
- \`MISSING_PUBLICATION\` のみ取得対象とする。実際に公式データが取得できなかった場合、C監査が未完了なら配信されない。既存の原本・配信JSONは上書きしない。
- 新規3タイルの取得でも、Cの公式HTTPS照合は**新規にネットワークアクセス**を行う。元の6タイルについては保存済みC MATCH証跡の再照合であり、鮮度保証を更新しない。
- タイルの実在・掲載件数は実際の取得結果で確定する。既存6/9の値から3タイル分の件数を推測してはいけない。

追加後は、上の読み取り専用レポートを同じ起点2件で再実行する。両起点がFULL_LOCAL_SOURCE_PROOFになれば、**洪水・隣接2起点のローカルC証跡比較**として記録できる。ただし、ブラウザ実機操作や別の地理的に離れた地域の受入を実施したことにはならず、\`baseline_accepted\` はfalseのまま。

## 地域×災害種別への移行条件

このスクリプトは現在 **skhb01 洪水専用**。次に選ぶ地域Bに対して証拠が0ならその状況を明示する。GSIの `skhb02` 土砂災害データを **skhb01** としてこの検査へ投入してはいけない。別ハザードでは別のAdapter・別のC独立試験・別のタイル在庫が必要。

1. Issue #89のPhase 1必達条件（ブラウザを含む）を満たす
2. 洪水の地域Bを選定し、**別**地域のraw/監査を作る（C原本検査＋保存済みHTTPS）
3. 洪水で地域差の再現を確認後、`skhb02` の固有値を先に調査する
4. 災害種別に依存しない共通構造を抽出し、洪水の既存証跡を破壊しない

確認済み出典・件数・施設の安全性・開設有無はこの台帳から新たに推論しない。
