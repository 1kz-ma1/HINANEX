# R0 第二地域候補（新潟）と公式データ4セルの取得計画

**2026-11-16 / Status:** 候補位置の**公的一次資料による地理的アンカー**は確認済み。**GSI `skhb01`/ `skhb02` のB原本、A洪水原本の実HTTP成否は未確認**。この地域・タイル/施設の正式承認や一般公開はしていない。

依存：D [#379](https://github.com/1kz-ma1/HINANEX/pull/379) → D [#390](https://github.com/1kz-ma1/HINANEX/pull/390) → 本R0候補plan生成。C [#385](https://github.com/1kz-ma1/HINANEX/pull/385) → C [#393](https://github.com/1kz-ma1/HINANEX/pull/393) はD raw取得後の独立監査。人間レビューは [#388](https://github.com/1kz-ma1/HINANEX/issues/388) に後日まとめて実施。

## 1. 選定した比較スロット（施設や行政界ではない）

| slot | 地理的な参照 | 計画対象 z/x/y | 根拠の性質 |
|---|---|---|---|
| A | 市川市周辺を含む従来調査タイル | `10/909/403` | 2026-11-16、D取得/C別HTTPS再取得で `skhb02` raw byte一致を利用者報告（800件タイル全体、SHA256 `6d940e0bee2af28e69e3b5e6957ab3a619464a75216be30febe851978d906253`）。`skhb01`は未検証 |
| B | 新潟市中央区内の**地理的参照点**（新潟県庁駐車場ヘリポート） | `10/907/395` | 新潟県公式資料の **世界測地系・北緯37度54分14秒／東経139度01分24秒**を、国土地理院XYZ方式でz10タイル変換した数学的結果。緊急避難場所やGSI source掲載地点であるという意味はない |

### Bで使用した公式一次資料

- **発行元** 新潟県、県内飛行場外離着陸場一覧。2023年8月31日現在の欄に「新潟県庁臨時（駐車場内ヘリポート）」及び**世界測地系**の北緯37度54分14秒・東経139度01分24秒が記載。URL: https://www.pref.niigata.lg.jp/uploaded/attachment/389261.pdf
- **新潟市公式** 市勢概要・市域の位置情報。URL: https://www.city.niigata.lg.jp/shisei/gaiyo/profile/siseigaiyou.html
- **国土地理院公式** [地理院タイルの仕様](https://maps.gsi.go.jp/development/siyou.html)。世界測地系/WGS系メルカトル投影、ズームによる分割、`z/x/y` を定義。緯度経度から座標を**参照点1個だけ**数学変換したもので、施設座標を補完する処理ではない。
- **国土地理院公式** [指定緊急避難場所の配信仕様](https://maps.gsi.go.jp/help/use.html) は `skhb01`洪水・`skhb02`崖崩れ/土石流/地滑りの**z10** GeoJSON URLを定義。仕様上のURLがあることと、今回4件の個別URLがHTTP200/featureを返すことは異なる。
- 市町村別データ公開一覧：https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html 。ページは一部JavaScript生成であるため、今回の非ブラウザ取得では新潟市の当日公開日・更新日/カバレッジを確証できていない。

**確認できていない事項:** Bタイルの `skhb01`/ `skhb02` のHTTP200、原本Feature数、タイルが新潟市全域を代表していること、公式指定の最新性、合法的な再配布、個々の避難先の存在/安全性。Web閲覧経路では両GSIデータURLの直接取得が使えず、実行環境のcurlはGSIホストのDNS解決に失敗した。**404やデータ0件とみなさない**。

## 2. 取得対象4セル（正式受入ではない）

| slot | hazard | 個別の公式URL | 2026-11-16時点の可否 |
|---|---|---|---|
| A | flood `skhb01/disaster1` | https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson | NOT_ACQUIRED |
| A | landslide `skhb02/disaster2` | https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson | **D/C byte一致・利用者報告（単独検証）**。新R0実行には別保存領域で再取得が必要 |
| B | flood `skhb01/disaster1` | https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/907/395.geojson | NOT_ACQUIRED |
| B | landslide `skhb02/disaster2` | https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/907/395.geojson | NOT_ACQUIRED |

A/B各タイルの中心点/実施設座標/境界は**出力しない**。各タイルが複数市町村を横断しうるため、タイル全体の件数を自治体ごとの避難先件数に読み替えてはならない。市川と新潟の行政界が別であることをもって「正式2地域受入4セル」とはしない。

## 3. 今回追加した実装

`pipeline/src/hinanex/gsi_r0_anchor_plan.py`

- **明示入力限定**：既存Aタイル `a_x/a_y`、B参照点の東経/北緯（DMS `度:分:秒`）、参照元HTTPS一次資料URL。
- 座標は入力された**参照点**からGSI XYZタイルへ計算。GPS・住所ジオコーディング・避難施設位置推定なし。Web Mercator範囲外、不正なDMS、重複タイル、出典URLの構文異常をfail-closed。
- 出力は既存D R0`hinanex.gsi.r0_tile_matrix.v0.1`と一致する**厳密な2-slot JSON**。原本座標・出典リンクを共有取得契約に混入させない。
- ターミナルの別の証拠要約は、参照文書のURL・元のDMSを残すが`reference_url_content_verified_by_tool=false`、両災害ソース存在`NOT_TESTED`、人間レビュー/公開`NOT_GRANTED`を固定。提供URLのHTTPS形式は**信頼された一次資料として認証したという意味ではない**。
- `--plan-out`はGit管理外の新規JSONパスだけ。既存ファイルを上書きしない。CLI単体でGSIデータへの通信なし。

## 4. Macでの明示実行（自動定期実行はしない）

```bash
# D #390 上に積んだ候補計画ブランチだけで取得工程まで動く
git -C "$HOME/HINANEX-h0-worktree" fetch origin feature/d-r0-niigata-anchor-plan-20261116
git -C "$HOME/HINANEX-h0-worktree" worktree add --detach \
  "$HOME/HINANEX-r0-worktree" FETCH_HEAD

mkdir -p "$HOME/HINANEX-r0-evidence/capture-001"
cd "$HOME/HINANEX-r0-worktree/pipeline"

# まず一次資料で与えた参照座標からplan生成（外部通信なし）
python3.12 -m src.hinanex.gsi_r0_anchor_plan \
  --a-x 909 --a-y 403 \
  --b-lon-dms "139:01:24" \
  --b-lat-dms "37:54:14" \
  --b-reference-url "https://www.pref.niigata.lg.jp/uploaded/attachment/389261.pdf" \
  --plan-out "$HOME/HINANEX-r0-evidence/pilot-plan.json"

# 4つの要求URLを確認（通信なし）
python3.12 -m src.hinanex.gsi_r0_pilot_batch \
  --plan "$HOME/HINANEX-r0-evidence/pilot-plan.json"

# 4URLを実際にGETし、Git管理外のraw/receiptを個別保存（明示時のみ）
python3.12 -m src.hinanex.gsi_r0_pilot_batch \
  --plan "$HOME/HINANEX-r0-evidence/pilot-plan.json" \
  --execute \
  --evidence-dir "$HOME/HINANEX-r0-evidence/capture-001" \
  --report-out "$HOME/HINANEX-r0-evidence/r0-capture-001.json"
```

**提出:** `R0_...` のJSONメタデータのみ。原本・receiptそのものやローカル住所/個別施設名はGitHubへコミットしない。結果が `R0_PARTIAL_CAPTURE_HOLD` でも「取得不可」「ゼロ件」と断定せず原因コードで記録。4セルrawを取得できた場合のみ、別C [PR #393](https://github.com/1kz-ma1/HINANEX/pull/393)のローカル監査→任意HTTPS独立リプレイを別工程で実施する。

## 5. テストと保留ゲート

```bash
cd pipeline
python3.12 -m unittest discover -s tests -p "test_gsi_r0_anchor_plan.py" -v
python3.12 -m unittest discover -s tests -v
```

新規15件の合成テストで、一次資料のDMSからのz10計算・既存R0契約適合・偽出典 URL・重複タイル・範囲外/Boolean値・無断通信なし・出力パス/上書き拒否を確認。**実データ4セルを使った検証はMacでの明示実行までNOT_RUN**。

- D `pipeline/**`のみ、共有Contract・D既存RegionExport・B/C/E/GIS/Renderに影響なし。
- Depends on D #390（さらに#379）。このブランチは `feature/d-r0-gsi-four-cell-batch-20261116`からのstacked変更。親がDraftの間は本PRもDraft・merge: blocked。
- 人間レビューは後日まとめて #388 に登録したまま。資料の二次配布・行政界・避難施設同一性・安全・現時点の開設状況はすべて未承認。

**Gate: 技術的な候補計画生成のみ実装。R0の公式4セル取得・C独立原本・正式2地域の採用判断・公開は未実施/NO-GO。**
