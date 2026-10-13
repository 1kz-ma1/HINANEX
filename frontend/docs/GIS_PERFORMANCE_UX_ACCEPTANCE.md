# GIS パフォーマンス改善の UI/UX 受入仕様

## 位置付け

- 対象資料: HINANEX パフォーマンス改善計画・担当割当 v1.0.0
- B確認日: 2026-10-13
- baseline: `main` / `520ff41`
- Bの変更範囲: `frontend/**`
- Eの実装範囲: `gis/**`

この文書は、PERF-07〜09についてBが定義するUI要件、測定baseline、E実装後の受入条件です。GISエンジン、RegionExport、Scenario、Evidenceの意味は変更しません。実装対象が現在のRepositoryルールでE所有の`gis/**`にあるため、B feature branchからGIS実装を変更しません。

## 変更前の確認結果

### GitHub / 実装状態

- `main`は`520ff41`。`role/b-frontend`はmainの376 commit後方、`role/e-gis`はmainの540 commit後方。
- OpenのB/E関連PRはDraft PR #83のみ。PR #83は古い`role/b-frontend`向けで、今回の変更元にはしない。
- Eの描画最適化 #118、#123、#125はmainへ統合済み。Dマーカーの再利用、整数zoom band内のクラスタ再利用、viewport更新の120ms debounceとRegionExportのメモ化は利用できる。
- 施設一覧、Observer、マーカーCSSの実体は`gis/**`にあり、B Scope Guardでは変更できない。

### PERF-07 baseline

現行経路は次のとおり。

```text
facilityListSearch input
  -> facilityListQuery更新
  -> pageを0へ戻す
  -> renderFacilityList()
  -> 全recordをfilter
  -> 20件分のカードHTMLを再生成
  -> facilityListResults.innerHTMLを置換
```

- debounce: なし
- 同一query / 同一page / 同一表示IDに対するrender抑止: なし
- page切替: 同期render（維持すべき挙動）
- panel非表示時: `renderFacilityList()`冒頭で処理を中止

2026-10-13にNode.js v24.16.0で、既存の名古屋向けテストと同じ1,602件の座標なし合成recordを使用して純粋な`filterFacilityRecords()`だけを測定した。10個の漸進的な検索語を10周する100回/run、warm-up後7 runの中央値は次のとおり。

| 指標 | 変更前 |
|---|---:|
| records | 1,602 |
| 100 filter合計の中央値 | 1,251.850 ms |
| 1 filterあたりの中央値 | 12.5185 ms |
| 100 filter合計の最小 / 最大 | 1,231.008 / 1,322.079 ms |

これはCPU上の合成benchmarkであり、実データ、DOM生成、paint、端末性能を表す値ではない。実ブラウザのLong Task、Scripting、Rendering、paint、入力遅延は未計測。

### PERF-08 baseline

| 対象 | 監視内容 | 現在の抑止 |
|---|---|---|
| `map_first_ui.js` | `originStatus`の子要素・文字列・subtree | rAF集約なし |
| `evidence_sheet.js` | D件数3項目、dataset chip、GSI coverage/count、raster warning、viewport D status | Evidence panel非表示時は`refresh()`しない |

どちらもMutationObserver callbackのアプリケーション側rAF集約はない。ブラウザ自身による同一microtaskのMutationObserver batchingはあるが、同一frameに複数callbackが届いた場合の追加抑止はない。実ブラウザでの1操作あたりcallback回数は未計測。

### PERF-09 baseline

- D個別施設とクラスタは`L.marker` + `L.divIcon`。`preferCanvas: true`はこれらのHTML iconをCanvas化しない。
- `.shelter-icon`と`.d-facility-cluster`には`box-shadow`とtransformがある。
- 常時animation、transition、filterはない。
- #118 / #123により、membership不変時のmarker objectとfractional zoom band内のクラスタは再利用される。
- CSS装飾がLong Taskやframe dropの主因かは未計測。この段階では意味のある視覚区別を弱めるCSS変更を行わない。

## PERF-07 施設検索・一覧

E実装の初期値は200ms debounceとする。150〜250msの範囲を実機確認で調整してよいが、変更理由と計測値をE PRに残す。

### 必須動作

1. `input`ごとに入力値は即時保持するが、filterと一覧DOM更新は最後の入力から200ms後に行う。
2. IME変換中は確定前の再描画を繰り返さない。`compositionend`後に最新値を対象として予約する。
3. Enter、前へ、次へは待機中のqueryを確定し、ユーザー操作に対して即時更新する。
4. 地域変更、RegionExport差し替え、一覧mode終了時は待機timerを取消す。旧地域のtimerで新地域の一覧を書き換えない。
5. record集合が同じ、正規化queryが同じ、pageが同じ、表示対象の順序付きIDが同じ場合は、一覧カードDOMの置換を省略する。
6. dataset世代またはrecord objectが変わった場合は、同じIDでも必ず再評価する。公式raw値やreasonの更新を隠さない。
7. 過剰な永続cacheを作らない。RegionExportをlocalStorageへ複製せず、画面session内だけで比較する。

### 維持するUI意味

- 取得施設数、検索一致数、表示範囲、page数
- 0件表示とpage buttonの状態
- 施設選択、詳細、Evidence、HTTPS source link
- HTML escapeと危険なURLの除外
- 座標欠損recordの検索・閲覧
- `CANDIDATE` / `EXCLUDED` / `UNKNOWN`のD原値
- `UNKNOWN`は危険・利用不可・対象外へ変換しない
- 地域切替で検索語と旧一覧をclearする

### PERF-07 acceptance

- 10回の連続`input`に対し、入力終了後の一覧renderは原則1回。入力間隔が200msを超えた場合は各確定単位でrenderしてよい。
- 同じ正規化queryを再入力した場合、結果カードの`innerHTML`置換は0回。
- page切替は1操作につき1 renderで、遅延を加えない。
- 1,602件fixtureで検索件数、最終page、0件、座標欠損、XSSの既存テストがすべて維持される。

## PERF-08 パネル / MutationObserver

### 実装条件

- Observerは削除しない。既存のstatus同期を保つ。
- 各Observerごとに`requestAnimationFrame`予約を1つだけ保持し、同一frameの通知を1回の更新へまとめる。
- Evidence panelが閉じている間は高コストな`refresh()`を行わない。開く操作では必ず最新DOMから1回refreshするため、状態は失わない。
- GPS failure feedbackは拒否・利用不可・取得失敗・開始失敗の意味を変えずに同期する。
- panel開閉時の`map.invalidateSize({ pan: false, animate: false })`は削除しない。中心、zoom、地域、起点、D/GSI状態を変更しない。
- moduleの多重初期化でObserverやlistenerを重複登録しない。

### PERF-08 acceptance

- 同一frame内に3回以上の監視対象更新があっても、各表示面の更新関数は最大1回。
- Evidence panel非表示中はEvidence出力DOMの書換え0回。再表示直後は最新値を表示。
- 左右panelの開閉ごとに`invalidateSize`は1回。地図center / zoomは不変。
- PCと狭いviewportの双方で、開閉、Escape、外側click、keyboard focusを維持する。

## PERF-09 マーカー / クラスタの視覚要件

現時点のE描画方式は`L.marker` + `L.divIcon`である。Canvas移行の採否はEが計測して決める。B側だけで描画方式やcluster閾値を変更しない。

### DivIconを維持する場合

- profilingでpaint/composite負荷が確認された場合だけ、多数表示される通常markerのshadowを段階的に簡略化する。
- hover / focus / 選択中など短時間の状態を優先し、常時animationを追加しない。
- CSS変更前後を同じ地域、zoom、viewport、marker数で比較する。

### Canvasを採用する場合

- 通常施設と大量表示はCanvasへ任せ、選択中・keyboard focus・重要なUI状態のみHTML overlayを検討する。
- Canvas化後もkeyboardやscreen readerから施設詳細へ到達できる一覧導線を残す。

### 維持する視覚・意味

- D個別施設の`CANDIDATE` / `EXCLUDED` / `UNKNOWN`を区別する。ただし安全 / 危険 / 対象外の意味へ変換しない。
- D RegionExport、GSI掲載参考地点、選択起点、クラスタを別Source / 別状態として識別できる。
- cluster数はそのvisual group / 現在描画対象に含まれるD record数であり、自治体全体件数ではない。
- cluster中心は含まれる座標の表示用平均で、実在施設、安全地点、推奨地点ではない。
- zoom 13以上で個別D source座標へ戻り、座標を補間しない。

## E実装後の回帰matrix

次の全項目を江戸川区、新潟市、名古屋市で確認する。自動testだけで確認できた項目と、実ブラウザで確認した項目を分けて記録する。

| 操作 / 意味 | Desktop | Mobile相当 |
|---|---|---|
| zoom 12 -> 13 -> 15、連続拡大・縮小 | 要実ブラウザ | 要実ブラウザ |
| drag / viewport marker更新 | 要実ブラウザ | 要実ブラウザ |
| 個別施設click、一覧から選択、詳細 | 要実ブラウザ | 要実ブラウザ |
| Evidence開閉、左右panel開閉 | 要実ブラウザ | 要実ブラウザ |
| 検索、0件、page切替、座標欠損 | 自動 + 実ブラウザ | 自動 + 実ブラウザ |
| 地域切替時の旧一覧 / 旧詳細clear | 自動 + 実ブラウザ | 自動 + 実ブラウザ |
| 絞込、表示設定、洪水raster、opacity | 自動 + 実ブラウザ | 自動 + 実ブラウザ |
| tour、GPS、地点選択、周辺参照 | 自動 + 実ブラウザ | 自動 + 実ブラウザ |
| tile失敗とRegionExport失敗の文言 | 自動 + 実ブラウザ | 自動 + 実ブラウザ |
| GSIとDのSource区別 | 自動 + 実ブラウザ | 自動 + 実ブラウザ |

取得失敗を「洪水なし」「避難所なし」と表示してはならない。描画数を減らしてもD原data、施設件数、座標欠損、Scenario statusを変更しない。

## 性能記録フォーマット

E実装前後を同じcommit以外の条件で比較しない。取得できない値は`未計測`と書き、0と記録しない。

| 日付 | commit | 地域 | device / viewport | 操作 | before | after | Long Task | DOM更新 | 体感 | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-13 | `520ff41` | 合成1,602件 | Node v24.16.0 | 純粋filter 100回 | 1,251.850ms median | 未実装 | 未計測 | 未計測 | 未計測 | 改善対象 |

## E担当へのhandoff

優先順は次のとおり。

1. PERF-07: `gis/gis/js/map.js`の検索eventに200ms debounce、IME対応、stale timer取消、同一表示signature抑止を実装する。
2. PERF-08: `gis/gis/js/evidence_sheet.js`と`map_first_ui.js`のObserver callbackをrAFで集約する。非表示skipと`invalidateSize`を維持する。
3. PERF-09: DevToolsでpaint/compositeが主因と確認できた場合のみ、現行DivIcon CSSを調整する。Canvas採否、cluster閾値、更新eventはEが決定する。
4. E PRには変更前後のLong Task、Scripting、Rendering、一覧DOM書換え回数、Observer更新回数を、取得できた範囲だけ記載する。

BはE PRでこの文書の受入条件を確認し、3地域のDesktop / Mobile実ブラウザ結果をPASS / FAIL / NOT RUNで追記する。

## PERF-01〜06の現状監査

これは完了認定ではなく、`520ff41`のコードから確認できる状態である。Eが計画書の正式な完了条件と実機計測を照合する。

| ID | 2026-10-13時点 | 確認内容 / 残作業 |
|---|---|---|
| PERF-01 marker描画方式 | 部分対応 | #118 / #123でmarkerとclusterを再利用。D施設は引き続きHTML DivIconで、Canvas移行は未決定。実機frame / paint計測が必要。 |
| PERF-02 zoomend / moveend | 部分対応 | clusterはinteger zoom bandで安定化、viewport更新は120ms debounce。`zoomend`と`moveend`は別handlerのため、重複処理の実測と統合要否判断が必要。 |
| PERF-03 tile処理 | 実装あり・実機未確認 | `keepBuffer: 3`、洪水rasterの途中zoom更新抑止、gesture設定を実装済み。外部network / decode / mobile体感は未計測。 |
| PERF-04 RegionExport cache | 部分対応 | viewport用3地域dataはmemory cacheとin-flight共有あり。選択地域の通常loadは`no-store`のため、再選択時の取得方針をEが判断する。 |
| PERF-05 全件走査・集計 | 残あり | viewportごとに各summaryの`mappableRecords.filter`を実行。施設検索の全件走査はPERF-07とも関連。実データ件数でprofileする。 |
| PERF-06 GSI参照data取得 | 残あり | 選択地点周辺の検証済みtile JSONを`no-store`で取得。再選択cache、同一tile共有、失敗retry方針を安全意味を変えずに評価する。 |

## このB変更での検証結果

### Passed

- B Frontend: `npm test` — 50 / 50
- B Frontend: `npm run lint`
- B Frontend: `npm run build`
- Scope Guard unit tests — 6 / 6
- E GIS: `facility_list.test.js`
- E GIS: `map_controller.test.js`
- E GIS: `d_region_adapter.test.js`
- E GIS: `region_exports.integration.test.js`
- E GIS: `inspect_local_region_exports.test.js`
- E GIS: `flood_discovery.test.js`
- Local fixture acceptance: 江戸川2件（座標欠損1）、新潟1件（UNKNOWN 1）、名古屋2件（座標欠損2 / UNKNOWN 2）を元の意味のまま受理

### Failed

- `python gis/tests/smoke_checks.py`: current mainの`map.js` commentにある`not geocoding`という文字列を、旧smoke checkが実装上のgeocodingと誤検知する。今回のB変更は`gis/**`を変更しないため、Eの別修正対象とする。このtestはrequired GitHub workflowには含まれていない。

### Not run

- Chrome DevTools Long Task / Scripting / Rendering / paint / MutationObserver callback計測
- stagingのDesktop / Mobile実ブラウザ操作
- 実端末のmouse / touch / pinch / GPS permission
- 外部GSI flood rasterのnetwork状態

### Reason

ローカルcheckoutに実運用の3地域RegionExport artifactがなく、今回のbranchはB所有の文書・受入条件だけを変更する。fixtureによる自動回帰は実施したが、実ブラウザ体感や外部network値を推測で補わない。
