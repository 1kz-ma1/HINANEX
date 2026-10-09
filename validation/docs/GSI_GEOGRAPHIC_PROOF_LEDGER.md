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

## 地域×災害種別への移行条件

このスクリプトは現在 **skhb01 洪水専用**。次に選ぶ地域Bに対して証拠が0ならその状況を明示する。GSIの `skhb02` 土砂災害データを **skhb01** としてこの検査へ投入してはいけない。別ハザードでは別のAdapter・別のC独立試験・別のタイル在庫が必要。

1. Issue #89のPhase 1必達条件（ブラウザを含む）を満たす
2. 洪水の地域Bを選定し、**別**地域のraw/監査を作る（C原本検査＋保存済みHTTPS）
3. 洪水で地域差の再現を確認後、`skhb02` の固有値を先に調査する
4. 災害種別に依存しない共通構造を抽出し、洪水の既存証跡を破壊しない

確認済み出典・件数・施設の安全性・開設有無はこの台帳から新たに推論しない。
