# R0 — GSI 2タイル位置 × 2災害の取得・証拠管理（D内部仕様）

**記録日:** 2026-11-16
**追跡:** Issue #89 地域×災害2×2、Issue #305 Stream R、Issue #378 H0、Issue #380 C原本一致、Issue #388 後日まとめて実施する人間レビュー
**依存:** D H0 [Draft PR #379](https://github.com/1kz-ma1/HINANEX/pull/379)。C skhb02単一タイル検査 [Draft PR #385](https://github.com/1kz-ma1/HINANEX/pull/385) とは直接のコード依存なし
**Status:** D内部の先行合成実装。B/E/RegionExportへの共有契約採用は**未承認**。人間レビューは後日のバッチに積む。

## 1. なぜこの順番か

H0では利用者MacからGSI土砂 `skhb02/10/909/403.geojson` を取得し、D/Cで `240875` bytes・タイル全体 `800` features・SHA256 `6d940e0bee2af28e69e3b5e6957ab3a619464a75216be30febe851978d906253` の技術的同一性を報告済み。現時点で**確定したのはタイル単位の原本バイト一致だけ**。市川市全域の施設、法律上の指定、現況・安全・開設、再配布許可を示さない。

次は手作業で4回コマンドを打つ代わりに、**2つの明示した地理院z10タイル位置 A/B**について、洪水 `skhb01/disaster1` と崖崩れ・土石流・地滑り `skhb02/disaster2` の合計4セルの取得を小さなCLIで管理する。

**最重要の区別：この段階の A/B は「2つの明示タイル」であって「行政区域の異なる2地域」ではない。** タイルの異同はチェックできるが、地域Bの地理的距離・行政界、原本の公開範囲、指定件数は別途出典で検証していない。この機能の4セル取得を #89 の2地域×2災害の正式受入に数えない。

## 2. インターフェースと安全な既定動作

- 実装：`pipeline/src/hinanex/gsi_r0_pilot_batch.py`
- **引数なし・通常実行は存在しない**。必ず`--plan`で手動選択のJSONを渡す。
- 既定：`--execute`がなければ**プレビューのみ**。`HTTP GET=0`、raw出力=0。`status=R0_PREVIEW_ONLY`で4つの期待URLとハザード属性を出す。
- 明示`--execute`時のみ4つのGSI HTTPS GETを順番に行う。Dの `gsi_hazard_acquisition.acquire_one_tile` を共通使用し、HTTPS URLの検証・リダイレクト拒否・20MiB上限・タイムゾーンUTC・原文GeoJSONの厳格検査・rawとreceiptの排他保存を再利用。
- リポジトリ内部のraw保存は不可。外部に**既存の絶対パスであるディレクトリ**を指定する。4セルのうち1つでもrawかreceiptの既存ファイルがある場合は、ネットワーク開始前に**全体を中止**し、既存証拠を混在/上書きしない。
- 成功後は各保存済みrawと保存済みreceiptの値を再照合し、URL、hazard、tile、hash、byte数、UTC、未承認ステータスを検査。**receipt内の `PASS`/公開許可などの偽装を拒否**。
- 失敗セルは`NOT_ACQUIRED_OR_EVIDENCE_HOLD`で記録。HTTP 404やDNS失敗を施設0件とみなさず、その他のセルの取得は続ける。raw構造が空`features=[]`でも`EMPTY_TILE_COVERAGE_UNKNOWN`であり、行政区域内の施設数とはしない。
- 全4セルのraw取得が成功しても `R0_FOUR_TILE_CAPTURES_UNAPPROVED`。全セル`c_independent_acceptance=NOT_GRANTED`, `publication_approval=NOT_GRANTED`、総合 `cells_independently_c_accepted=0`、`pilot_b_geographically_distant_verified=false`。
- ユーザーが`--report-out`を指定した場合だけGit管理外に新しいレポートJSONを保存（既存ファイルへの上書きを禁止）。レポートには実住所・個別施設名/位置を含めず、タイル単位のURL/件数/ハッシュと受入状態のみを出力。

### 入力例（**合成試験専用。地域Bのソース調査済み例ではない**）

```json
{
  "schema": "hinanex.gsi.r0_tile_matrix.v0.1",
  "pilots": [
    {"slot": "A", "tile": {"z": 10, "x": 909, "y": 403}},
    {"slot": "B", "tile": {"z": 10, "x": 910, "y": 404}}
  ]
}
```

**この例のBをそのまま `--execute` してR0正式受入と称してはいけない。** `910/404` はテスト用の仮値であり、遠隔地域の2災害公式ソースが存在するとの証明ではない。まず正式な地域B候補を公式資料から選び、明示z10 URL・取得対象・スコープを記録した別planをGit外に作る。

`A`についても `skhb01`洪水の同タイルの公開実在・時点は独立確認が必要。既存 `skhb02`のC byte MATCHを洪水へ流用しない。

## 3. 動作例

```bash
cd "$HOME/HINANEX-r0-worktree/pipeline"

# 先にGit管理外で作成したplanを確認。デフォルトでは通信なし。
python3.12 -m src.hinanex.gsi_r0_pilot_batch \
  --plan "$HOME/HINANEX-r0-evidence/pilot-plan.json"

# 別途、Bの公式取得タイル候補を調査・入力した場合のみ明示実行
python3.12 -m src.hinanex.gsi_r0_pilot_batch \
  --plan "$HOME/HINANEX-r0-evidence/pilot-plan.json" \
  --execute \
  --evidence-dir "$HOME/HINANEX-r0-evidence/capture-001" \
  --report-out "$HOME/HINANEX-r0-evidence/r0-capture-001.json"
```

実行先 `capture-001` は空の既存ディレクトリを用意する。再試行は別ディレクトリで行う。raw/receipt/実データはGitにコミットしない。自動定期取得・CI外部通信は行わない。

## 4. ステータスと未解決ゲート

| 状態 | 意味 |
|---|---|
| `NOT_EXECUTED` | プレビューのみ。取得未実施 |
| `RAW_CAPTURED_C_UNVERIFIED` | ローカルraw保存・構造/receipt照合済み。C未承認 |
| `EMPTY_TILE_COVERAGE_UNKNOWN` | 正常な空のタイルrawを保存。行政区域の施設0件ではない |
| `NOT_ACQUIRED_OR_EVIDENCE_HOLD` | HTTP/DNS/TLS/保存/receipt検証に問題。未取得/未検証 |
| `R0_PARTIAL_CAPTURE_HOLD` | 4セルの一部しかD技術取得できていない |
| `R0_FOUR_TILE_CAPTURES_UNAPPROVED` | 4セルのDローカルraw取得のみ。**正式なR0の受入ではない** |

4セルのC独立HTTPS照合や個別原本の版・出典・人間指定/施設同一性レビューは別スライス。既存C PR #385は`skhb02/10/909/403`のみに固定されており、別タイル/洪水の受入機能として**流用してはいけない**。#388の人間レビューは後日バッチで実施し、実装や合成CIを待たせない。ただし公開用RegionExport/GIS/避難先推薦/安全・開設判断への昇格はその後もNO-GO。

## 5. テスト・統合規律

```bash
cd pipeline
python3.12 -m unittest discover -s tests -p "test_gsi_r0_pilot_batch.py" -v
python3.12 -m unittest discover -s tests -v
```

合成のみ19ケース：異なる2タイル・4ハザード別URL、デフォルト通信0、明示取得、空タイル/HTTP404と正常0件の区別、既存証拠の一括上書き拒否、ハッシュ/receipt偽装とC承認偽装、環境パス規制、配信未承認、テスト用任意座標の正式地域扱い防止。実原本4セル取得・独立C・地域B候補の現地確認・Safari/iOS/Android実機は **NOT RUN**。

- D`pipeline/**`のみ。RegionExport v0.9/Scenario/既存GIS/F05/B/E/Renderに変更なし。
- **Stacked PR：Depends on #379**（H0 D取得CLI）。先行PRがDraftの間、R0 PRもDraft/merge: blocked。#379を本番統合していない間、R0を独立した完成した地域対応として扱わない。
- main統合はMerge Captainの明示判断が必要。最新main・契約・CIの検証は統合前に再実施。

**現在の判定：R0複数セルの機械的取得準備を進める。人間レビューと公開・避難判断はまとめて保留。**
