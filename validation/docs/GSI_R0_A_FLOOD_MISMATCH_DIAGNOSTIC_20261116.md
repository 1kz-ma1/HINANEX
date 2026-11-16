# R0 C監査：A洪水タイルのHTTPSバイト不一致を独立に切り分ける

**2026-11-16 / C担当 / 依存:** [C Draft PR #393](https://github.com/1kz-ma1/HINANEX/pull/393) （C #385からのstacked）およびD原本取得 [#389](https://github.com/1kz-ma1/HINANEX/issues/389)。人間レビューは [#388](https://github.com/1kz-ma1/HINANEX/issues/388) に後日まとめて実施。公開・人間C承認は未実施。

## 1. Macから提出された実原本検証結果（AIがrawを直接見たものではない）

- Dの4セルraw取得 4/4、Cローカルraw/receipt/D report検算 4/4（`2026-11-16T04:52:27Z`）。
- C4セル HTTPS別リプレイ 3/4 byte MATCH。A洪水 `skhb01/10/909/403` のみ `C_SOURCE_CHANGED_OR_MISMATCH_HOLD`、残り3セルは`C_HTTPS_BYTE_MATCH_UNAPPROVED`。
- A洪水のD保存原本SHA256 `3d88eab61dea466e3647beb08a47e312cf9853de48d6936323e5023d0c27881c`、C別GET原本SHA256 `1a18246c95386b24bada1a063b1cf8e51f8f1fe7b7f546de6032adc3e589cc35`。
- D保存原本は`349472` bytes、GSI z10タイル全体`1195` features。**当該C再取得時のバイト長・feature数・HTTP ETag/Last-Modified・生rawは記録されていないため不明**。これは**単なるSHA不一致の観測**であり、公式の改版・災害危険・指定変更・配信不具合をまだ特定していない。
- zshの `command not found: #` はコメントをコマンドとして貼ったことによるもので、**D/Cレポート取得成功とは無関係**。

元証拠の正本：[Issue #392 C4セル実行報告](https://github.com/1kz-ma1/HINANEX/issues/392#issuecomment-6907704960)。

## 2. 今回追加した限定診断

`validation/validation/diagnose_gsi_r0_a_flood_delta.py`

- **対象をA洪水の正式URL `https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson` に固定**。B/土砂・地理タイル・施設情報を意図せず再検証/取得しない。
- 必ずDの保存済み4セルreport、A洪水原本・receiptをC既存コードで検算し、タイル範囲、`disaster1=1`、raw SHA/バイト数/全Featureを検査。未承認の状態も維持する。
- その後、**明示実行時に1回だけ公式HTTPS/TLS GET**（既存Cのredirect禁止・proxy無効・URL厳密指定・12MB上限）を行い、応答HTTP200・最終URL一致と元原本のハッシュ、bytes、feature数を比べる。
- JSONの**厳格なPython型付き構造比較**を追加。原文JSONが同じ構造でもシリアライズ/キー順/空白差でバイトが異なる可能性を区別できる。全Featureを同じ配列インデックス同士で比較し、相違インデックスの**件数と最初の番号だけ**記録。施設名・住所・座標・個々の詳細・JSON本文は出力しない。
- 前回CのSHA `1a182...`は**ユーザーが申告した過去ハッシュ**として照合するだけ。前回Cの生rawが存在しないため、今回の新GETが異なる場合でも**前回の差分理由を確定しない**。`cause_of_prior_mismatch=UNDETERMINED`固定。
- 新たなC HTTP GET原本はこのツールでは保存せず、Git外に**新規・排他**JSONレポートを1つだけ書く。D原本・receipt・R0元reportおよび既存Cレポートを上書きしない。
- 取得の現在一致時`C_A_FLOOD_CURRENT_BYTE_MATCH_UNAPPROVED`、不一致時`C_A_FLOOD_CURRENT_BYTE_MISMATCH_HOLD`。これは**過去のHOLDを取り消さず**、現在の追加観測を記録する。ネットワーク・入力・検証失敗は`C_A_FLOOD_DIAGNOSTIC_HOLD`。
- `c_independent_approved=false`、`facility_identity_approved=false`、`publication_approved=false`。一連のbyte比較は公式データの署名・自治体全域・指定の現在有効性・施設安全の承認ではない。

## 3. 利用者Macでの再現手順（C実行はこの時点ではNOT_RUN）

既存 `HINANEX-r0-c-worktree` はPR #393の先行コードをすでに含みます。PR #393内へ診断を追加したHEADに更新する際、worktreeに未コミットの変更がないことを先に確認してください。

```bash
git -C "$HOME/HINANEX-r0-c-worktree" status --short
git -C "$HOME/HINANEX-r0-c-worktree" fetch origin feature/c-r0-four-cell-https-replay-20261116
git -C "$HOME/HINANEX-r0-c-worktree" switch --detach FETCH_HEAD

cd "$HOME/HINANEX-r0-c-worktree"

python3.12 -m unittest discover -s validation/validation -p "test_diagnose_gsi_r0_a_flood_delta.py" -v

python3.12 validation/validation/diagnose_gsi_r0_a_flood_delta.py \
  --d-report "$HOME/HINANEX-r0-evidence/r0-capture-001.json" \
  --evidence-dir "$HOME/HINANEX-r0-evidence/capture-001" \
  --prior-c-sha256 "1a18246c95386b24bada1a063b1cf8e51f8f1fe7b7f546de6032adc3e589cc35" \
  --report-out "$HOME/HINANEX-r0-evidence/r0-a-flood-diagnostic-20261116-01.json"
```

**注意：** `--report-out` のファイルがすでに存在する場合は失敗するので、再試行時は新しいファイル名にする。ファイル名には識別可能な日時や番号を使用してください。作業用worktreeや保存済みRawのgit状態が不明な場合は、勝手な`reset --hard`、`clean`、上書きをせず相談してください。

出力JSON（原本/個人・施設情報を含まない）を共有すれば、少なくとも「現在のバイト一致・不一致」「JSON構造が一致するか」「件数差」「相違する最初のインデックス」「現在取得が過去Cハッシュと一致するか」を記録できる。**施設同一性や実際の指定情報はこの指標だけでは分からない。**

## 4. 技術受入・保留

- 本PRの追加診断はC領域の**限定実装**。既存4セル技術PASS 3/4とA洪水HOLD 1/4を維持する。
- 合成テスト `validation/validation/test_diagnose_gsi_r0_a_flood_delta.py` はネットワークmockだけ。C実本番タイルの新GET、原因解明、GSIのHTTPヘッダー比較、公式改版判定は **NOT_RUN**。
- 機器QA：NOT_REQUIRED（offline監査/単一GETのCLI）。RegionExport、GUI、B/E/Renderには変更なし。共有Contract impact: none。
- 人間レビューとデータ公開判断はIssue #388の後日バッチへ蓄積。**mainへの統合は依存先PRの最新main追従、required CI、Merge Captain判断まで保留**。
