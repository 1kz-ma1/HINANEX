# H0 / GSI skhb02 のC独立HTTPS原本再取得・バイト照合（限定1タイル）

- 記録日：2026-11-16 JST
- Issue: #380（C独立検証）、#378（D H0取得）、#305（H0）、#89（地域×災害2×2）
- 変更範囲：`validation/**`のみ。Dの`gsi_hazard_preflight`・`gsi_hazard_acquisition`をimportしない。
- 状態：**C検査コードと合成テストの実装**。ユーザーMacでのC側再取得はまだ実施されていない。地域網羅・指定施設の同一性・災害安全性・一般公開はHOLD。
- 対象URL（今回の固定スライス）：https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson

## 1. D側の利用者Mac提出結果（C未検証）

2026-11-16に利用者がD取得CLIによるローカル原本のHTTP/構造レポートを提出した。これはユーザー申告のD取得証跡であり、Cがネットワークやファイル内容を独立に観測したことを意味しない。

| 属性 | 提出された値 |
|---|---|
| 実行 D HEAD | `14e758553460c0f7ff11e122d413fc1dc927fd55` |
| status | `H0_LOCAL_STRUCTURE_ONLY` / `LOCAL_ARCHIVE_RECEIVED` |
| URL（requested/final） | `https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson` |
| HTTP | `200` |
| 時刻 | `2026-11-16T01:42:30+00:00` |
| SHA-256 | `6d940e0bee2af28e69e3b5e6957ab3a619464a75216be30febe851978d906253` |
| byte数 | `240875` |
| 件数 | `800`（z10タイル全体） |
| Header Content-Type | `application/octet-stream` |
| ETag | `"2f1b21abf3d6c40133dea418a2a62fa6"` |
| Last-Modified | `Mon, 09 Nov 2026 06:10:25 GMT`（**指定日・発効日ではない**） |
| raw/receiptパス | Mac `~/HINANEX-h0-evidence/skhb02-10-909-403.geojson` と `skhb02-10-909-403.receipt.json` |

旧市川 #316 に記録された同タイルのSHA `cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84` と一致しない。**版差／資料更新／キャッシュ／取得差の原因はまだ未判定**であり、旧調査の800件や市川住所接頭辞29件・突合28/1件を現在原本への承認に流用しない。

## 2. 独立C検査の範囲

`validation/validation/verify_gsi_skhb02_https_replay.py`

- Dコードを使わず、保管されたD rawの全FeatureをC独自検査：GeoJSON、duplicate keys、`disaster2=1`、名称/住所/備考、Point座標と **tile`10/909/403`内の地理的包含**、レコード数とハッシュ。
- D receiptの自己申告URL/hazard/`source_sha256`/bytes/全Feature数/UTC/HTTP200/未承認状態をローカルrawで再検算。**Dの検証自体を信頼して承認しない**。
- Cが改めてGSI公式HTTPS URLへ直接GET（外部proxy不使用、リダイレクト拒否、TLS・HTTPS固定、12MB上限）し、HTTP 200・最終URL同一・原文のハザード属性とtileを検証。D rawと **bytesそのもの** を比較。
- 同一の場合：`C_HTTPS_BYTE_MATCH_UNAPPROVED`、独立HTTPS byte replay `MATCH`。**人間のC承認、自治体/施設同一性、最新開設・安全・運用・出荷許可ではない**。
- バイト相違：`C_SOURCE_CHANGED_OR_MISMATCH_HOLD`、CLI終了コード3。実際の版更新なのか取得/応答差なのか原因は未確定、差分を黙って受入しない。
- HTTP/DNS/TLS/URL/Raw/receiptの不整合：`C_H0_REPLAY_HOLD`と終了コード2。404やDNS失敗は自治体の対象施設0件を意味しない。
- ローカル出力は外部証拠フォルダー内、既存レポートの上書きは拒否。原本、位置・住所の各行、生成済み結果はGitへコミットしない。
- 出力にはタイル全体の件数だけを残す。行政区域・市川市施設の総数や正式な適合/経路判断は行わない。

Cの直接HTTPS取得はDとは**別リクエスト・別検証実装**だが、同一Macで実行する場合は**ネットワーク/操作者独立性や暗号署名付きの原本真正性**まで証明しない。C人間レビューと独立ソースの再現性確認は別の段階。

## 3. Macで実行するコマンド

D側のworktreeを残したまま、C用に別worktreeを作る。元の原本は再取得・上書きしない。

```bash
git -C "$HOME/HINANEX-h0-worktree" fetch origin feature/c-h0-skhb02-https-replay-20261116
git -C "$HOME/HINANEX-h0-worktree" worktree add --detach "$HOME/HINANEX-h0-c-worktree" FETCH_HEAD
cd "$HOME/HINANEX-h0-c-worktree"

python3.12 validation/validation/verify_gsi_skhb02_https_replay.py \
  --raw "$HOME/HINANEX-h0-evidence/skhb02-10-909-403.geojson" \
  --d-receipt "$HOME/HINANEX-h0-evidence/skhb02-10-909-403.receipt.json" \
  --report-out "$HOME/HINANEX-h0-evidence/skhb02-10-909-403.c-replay-20261116.json"
```

**提出**：標準出力のJSON（必要ならURL/ローカルパスを伏せる）。`status`, `same_bytes`, `d_archived_sha256_recomputed`, `c_replayed_sha256`, `d_archived_tile_feature_count`, `c_replayed_tile_feature_count`, `c_checked_at_utc`など。表示が`C_H0_REPLAY_HOLD`や`C_SOURCE_CHANGED_OR_MISMATCH_HOLD`ならそのまま提出し、再取得原本をD原本に上書きしないこと。

**本処理をGitHub Actions上で実rawを使って実行しない**（外部URL/未承認データ/機密保存の依存回避）。合成テスト入口：

```bash
cd "$HOME/HINANEX-h0-c-worktree"
python3.12 -m unittest discover -s validation/validation -p "test_verify_gsi_skhb02_https_replay.py" -v
```

## 4. 残る人間と公開のゲート

- 公式サイトの掲載範囲/ライセンス/更新日、データ改変/第三者利用の適法性（A/Owner）
- タイル内の実地物、施設名・住所・区域の同定、公的指定の現時点の有効性の人間確認
- `skhb01`洪水の既存C監査を`skhb02`土砂災害へ横流ししないことの独立検証
- 本C結果がMATCHしても `independent_c_approved=false`、`publication_approved=false` を維持
- 2地域×2災害の採用判断、D RegionExport契約・E GIS接続は別Issue/PRで共同レビュー
- 合成CI PASSとMacの実原本再取得・人間レビュー・本番運用の判定は別々に記録

**判定：C技術的HTTPS byte replayの検証は実行待ち。正式出典受入/一般公開はNO-GO。**
