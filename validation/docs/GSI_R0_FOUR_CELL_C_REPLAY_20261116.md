# C / R0：2タイル × 2災害の独立原本監査（合成先行）

**作成日**：2026-11-16 JST
**Issue**：#89 R0・#389 D4セル取得・#380 C単一タイル・#388 人間レビュー保留台帳
**依存関係**：C [Draft #385](https://github.com/1kz-ma1/HINANEX/pull/385) にstackする。D [Draft #390](https://github.com/1kz-ma1/HINANEX/pull/390) が定義した入力 `hinanex.gsi.r0_tile_matrix.v0.1` に対応。#390はD #379に依存。
**受入状態**：内部技術検証ツール。**RegionExport v0.9 / B/E/GIS/Renderは変更なし**。正式出典、施設同一性、現在開設、安全性、一般公開はすべてNO-GO。ユーザー方針により人間レビューは#388へ蓄積して後日まとめて実施する。

## 1. 技術目的と対象の境界

D R0では **明示されたGSI z10の2タイル位置 A/B** に対して、洪水`skhb01/disaster1`と崖崩れ・土石流・地滑り`skhb02/disaster2`の合計4セルをローカル保存できる。

Cの今回の実装では同じ計画・出力を**Dの実装に依存せず**検証する。
- ハザードごとにURL、`disasterN`、raw SHA256、UTC取得時刻を厳密に分離。別タイルの原本/receiptや別ハザードの検証結果を流用しない。
- GSI公式タイルのURL正規形 `https://cyberjapandata.gsi.go.jp/xyz/skhb0N/10/x/y.geojson` 以外を受理せず、z10 x/yの正確な範囲を検査。
- 生GeoJSONの**全Feature**について、`FeatureCollection`、対象`disaster1|2=1`の整数型、原文名・任意住所/備考、PointのWeb Mercatorタイル内位置をC側で独立に検査。施設名・座標は監査レポートへ出力しない。
- Dの4セルreport、各raw、各receiptのURL・ハザード・byte長・SHA・UTC・出典/配信未承認フラグを再検算し、偽の公開承認を拒否。
- **既定では通信0**。 `--replay-https`を明示した場合のみ、CがGSI公式HTTPSから4セルを独立再取得し、TLS、HTTP200、最終URL、原本全行・バイト一致を検証。Proxy無し・redirect禁止・1セル12MB上限。
- 原本がない／DNS/HTTP障害／GeoJSON不正／バイト相違はHOLD。空の原本と未取得を別扱いにし、タイル全体0件を行政区域の0施設に変換しない。

**A/Bは異なるタイル位置であり、異なる2自治体でも地理的に離れた2地域でもない**。今回の4セル取得・4セル byte MATCHでも、Issue #89の正式な「2地域×2災害」受入を達成したとはみなさない。

## 2. ステータスと厳格な未承認ゲート

| コード | 内容 |
| --- | --- |
| `C_NOT_ACQUIRED_HOLD` | D側の取得証拠がない。実施設0件ではない |
| `C_EVIDENCE_OR_REPLAY_HOLD` | Raw/receipt不整合・GeoJSON/タイル外・HTTP/DNS/TLS等のエラー |
| `C_LOCAL_RAW_MATCH_UNAPPROVED` | Dのローカルraw/receiptとD4セルreportをCが照合。**C HTTPS再取得は未実行** |
| `C_HTTPS_BYTE_MATCH_UNAPPROVED` | CがHTTPSで別取得したrawと、D保存rawのバイト列が一致 |
| `C_EMPTY_TILE_BYTE_MATCH_COVERAGE_UNKNOWN` | 空タイルのrawがバイト一致。自治体に施設なしとは言わない |
| `C_SOURCE_CHANGED_OR_MISMATCH_HOLD` | D原本とC再取得原本のbyte差異。原因は特定していないのでHOLD |

レポート内の`cells_independently_approved=0`、`publication_approved=false`、`municipal_boundary_verified=false`、`facility_identity_approved=false`は本フェーズで**変更しない**。byteの一致はあくまで通信原本の一致で、GSIや自治体によるデータの署名・指定内容の確定・個別の安全性の証拠ではない。

## 3. R0のD保存規約への対応

C入力：
- D R0レポート：`r0-capture-001.json`
- D4セル保存ディレクトリ：`r0-A-flood-10-x-y.geojson`／`r0-A-flood-10-x-y.receipt.json`、同A landslide・B flood・B landslide
- 4セルの`slot`×`hazard`は完全一致、各slotのtileは同一、A/Bのtileは別、D取得成功件数・総合statusは実際のセル状態と整合する必要がある。
- `publication_approval=NOT_GRANTED`、`c_independent_acceptance=NOT_GRANTED`などが不一致なら自動拒否。
- pathは必ずリポジトリ外の絶対パス。raw/receiptのsymlinkは拒否。レポートは個別の元地点情報を含めない。
- R0のDテストで用いたB `910/404`は**合成テスト専用タイル例**。公式のRegion B候補や両hazardの可用性を証明していない。

## 4. CLI（R0実データ取得後に実行、今はNOT_RUN）

```bash
# PR #385のCブランチをベースにした別worktree。Macの既存D原本を変更しない。
git -C "$HOME/HINANEX-h0-c-worktree" fetch origin feature/c-r0-four-cell-https-replay-20261116
git -C "$HOME/HINANEX-h0-c-worktree" worktree add --detach \
  "$HOME/HINANEX-r0-c-worktree" FETCH_HEAD

cd "$HOME/HINANEX-r0-c-worktree"
python3.12 -m unittest discover -s validation/validation -p "test_verify_gsi_r0_four_cell_replay.py" -v

# 1) まず原本とreceiptをC独立照合。HTTP通信なし。
python3.12 validation/validation/verify_gsi_r0_four_cell_replay.py \
  --d-report "$HOME/HINANEX-r0-evidence/r0-capture-001.json" \
  --evidence-dir "$HOME/HINANEX-r0-evidence/capture-001" \
  --report-out "$HOME/HINANEX-r0-evidence/r0-c-local-001.json"

# 2) 利用者が公式HTTPSへ独立リプレイする場合のみ、明示オプトイン。
python3.12 validation/validation/verify_gsi_r0_four_cell_replay.py \
  --d-report "$HOME/HINANEX-r0-evidence/r0-capture-001.json" \
  --evidence-dir "$HOME/HINANEX-r0-evidence/capture-001" \
  --replay-https \
  --report-out "$HOME/HINANEX-r0-evidence/r0-c-https-001.json"
```

Dの4セル取得をまだ実行していない現在は、このCLIに与える実4セルraw/receiptは**存在を確認していない**。現物を用意せず検証実施済みとは報告しない。

## 5. テストと統合上の注意

- `validation/validation/test_verify_gsi_r0_four_cell_replay.py`：合成専用21ケース。通信はmockのみ。
- 合成テストと、ユーザーMacで実行した単一タイルC PR #385の技術PASS（SHA256 `6d940e0bee2af28e69e3b5e6957ab3a619464a75216be30febe851978d906253`、240875bytes、800tile-wide features）は**別の証拠**。この既存PASSを今回の4セルの技術PASSへ流用しない。
- D R0 PR #390はまだDraft。#379→#390の順の依存性、C側 #385→今回C PRの順番を守る。正式2地域の選定、人間の利用条件・地理情報・指定/入口/安全レビューは#388へ集める。
- C変更範囲は `validation/**` のみ。新しい地図・UI・経路・災害判断には接続しない。Device QA：NOT_REQUIRED（純粋なCLI＋mockテスト）。
- **Merge Captainの明示的判断がない限り、mainへ統合しない**。親PRの統合後、最新main追従・required CI再実施が必要。

**今回の受入：C多セルの合成実装・CIに限定。実raw4セル、実HTTPS4セル、正式地域2×2、人間承認は未実施のまま。**
