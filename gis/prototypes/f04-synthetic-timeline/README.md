# F04 合成洪水タイムライン — 独立・非公開Prototype

**Status: PRIVATE PROTOTYPE / SYNTHETIC ONLY / NO-GO for real flood advice or publication.**

## 目的と位置付け

2027-02-09 HINANEX MVPに向け、時間に沿った図形切替を実際に操作できる形で検証する。Draft PR #346 のF04は公式API調査を先行する**未採用の提案仕様**。本スライスはオーナーから明示された独立合成Prototypeであり、公式洪水時系列の実装・承認・取得実験ではない。F05/F07/F09やD/C、既存GISの表示、契約には接続しない。

## 最小仕様（S1）

| 条件 / 操作 | 表示と状態 |
| --- | --- |
| 初期・未選択 | UNSELECTED。色付きセルなし。再生・スライダー無効。|
| 架空ケースA/Bを明示選択 | PAUSED。初期模擬ステップ0と該当合成セルを表示。|
| 再生 | PLAYING。850msごとに**固定合成フレーム**を1つ進める。最後でPAUSED。|
| 一時停止 / スライダー | PAUSED。選択した相対番号の固定合成フレームのみ表示。|
| 先頭から | PAUSED。タイマー無効化後、合成ステップ0へ戻す。|
| 終端で再生 | ステップ0へ戻して再生する。|
| 別ケース選択 / 選択解除 | 前ケースの表示と旧タイマーを即時破棄。世代tokenの古いtickを無視。|
| 未選択でplay、未知ID、欠損・不正fixture、範囲外ステップ | NO-GO。フレームを全消去し、推測補完しない。選び直しを案内。|

## 合成データの意味と禁止事項

- 8列×5行の画面内模式グリッド。セルID `row-col` は配列インデックスであり緯度経度・地物・格子メッシュではない。
- 2つの完全架空ケース×各4ステップを静的同梱。セルの着色は水位・浸水深・危険度・速度・時刻・現実の安全を**一切意味しない**。ステップは実時間ではなく相対順序のみ。
- GPS・実座標・実際の河川/自治体・実災害データ・公式ハザード・外部API・localStorage・Cookie・通信リクエストなし。CSP `connect-src 'none'`。
- 利用者に施設の適合、安全、所要時間、避難要否、推奨を伝えない。固定した合成セル配列を単に切り替えるだけで、洪水進行を計算・予測しない。
- 画面上部、模式グリッド、凡例、フッターに合成・訓練用である旨を表示。

## ファイルと起動

すべて `gis/prototypes/f04-synthetic-timeline/` の内部で完結する（CIへの登録のみ `gis/tests/map_controller.test.js` の1行追加）。標準ライブラリとネイティブWeb API以外の依存なし。

```sh
node gis/prototypes/f04-synthetic-timeline/test-node.cjs
node gis/prototypes/f04-synthetic-timeline/test-browser.cjs
python3 -m http.server 8766 --bind 127.0.0.1 --directory gis/prototypes/f04-synthetic-timeline
```

手元のブラウザから `http://127.0.0.1:8766/index.html` を開く。テストには実Chromium (`CHROMIUM_BIN` で別パス指定可) が必要で、テストはHTTPで実HTML/JS/CSSを読み込む。ブラウザ検査をNodeモデル検査の成功で代替しない。

## 公開と統合のゲート

現行 `deploy/build_staging.py` は `gis/gis/**` のみをRenderの `/gis/gis/**` にコピーする。兄弟ディレクトリの `gis/prototypes/**` を**コピーしない**ことをNode静的ガードでも検査する。未承認公開・Render接続を追加しない。将来builderが変われば再検証が必要。

MVPや本番への連携判断には、公式APIの一次資料、条件/版、権利、C独立検証、人間の安全・公開承認、実機QA、最新main追従・required `test` が別途必要。Node/Chromium PASSは災害適合や公開GOではない。mainへのmergeは共同Merge Captainだけが判断する。

## S2 — 2模擬ステップ間の変化比較（Stacked on #430）

**S2はF04 S1の独立拡張。PR #430のmain統合・公開を意味しない。** 比較元と比較先は同一の架空シナリオから明示選択し、`2時点を比較`を押すまでは結果を出さない。S1の時点スライダーと再生/一時停止は独立して動作する。

| 操作・状態 | S2の表示 |
| --- | --- |
| 初期/シナリオ未選択 | 全比較グリッドが空、NO-GO、選択/比較ボタン無効 |
| ケースA/B明示選択 | 2つの模擬ステップ選択を有効化、比較結果はまだ空 |
| 2時点選択 | READY。明示比較ボタンが有効化、旧結果は即時破棄 |
| 2時点を比較 | SHOWN。比較元40セル、比較先40セル、差分40セル。文章と4分類の件数 |
| 比較元/先が同じ | 新規着色0/着色解除0、継続を正しく分類 |
| 比較順を反転 | 追加/解除を反転した模式セル差分を表示 |
| ケース変更 / S1全解除 / S2やり直し | 比較元/先の選択と旧3グリッドを同時にクリア |
| 欠損/重複/不正ケースや範囲外番号 | NO-GO。比較結果を破棄し、旧結果は再表示しない |

差分の4分類は「新規着色」「着色解除」「着色継続」「無着色継続」。**S2のセル数は模式図内の単純な着色数であり、浸水面積・浸水深・水位・危険度・到達時間・安全を意味しない**。すべての着色は固定合成fixtureの比較であり、現実の洪水進行や科学的な予測・補間は実行しない。

画面は3つの模式グリッドと文章説明、カウント、記号+/-/=/·を組み合わせる。モバイルは縦並び。キーボード用にnative `select` と `button`、明示ラベル/フォーカス/状態通知（S1の既存statusを維持）を使用。

S1 `synthetic-data.js` と `timeline-model.js`、`app.js` のロジックは変更しない。S2 `comparison-model.js` と `comparison-app.js` が独立して動き、S1のケース切替/解除イベントのみ参照する。CSP、実API/GPS/外部座標なし、非公開Render配布境界を維持する。F05/F07/F09、D/C/Contract/本番GIS変更なし。

### 実行
```sh
node gis/prototypes/f04-synthetic-timeline/test-node.cjs
node gis/prototypes/f04-synthetic-timeline/test-comparison-node.cjs
node gis/prototypes/f04-synthetic-timeline/test-browser.cjs
node gis/prototypes/f04-synthetic-timeline/test-comparison-browser.cjs
# playwright@1.56.1 をQA環境だけに導入（通常の本番依存には追加しない）
CHROMIUM_BIN=/path/to/chrome NODE_PATH=/path/to/qa/node_modules node gis/prototypes/f04-synthetic-timeline/test-comparison-keyboard.cjs
```

Node S2回帰はS1と同じ `gis/tests/map_controller.test.js` からrequired GitHub `test`へ登録。Chromeはlocal HTTPで本物のHTML/CSS/JSを読み込む。Playwrightのnative Tab/Arrow/Enter/Space試験とRender実コピー除外確認は検証専用ワークフローで実施する。**Android/iOS実機と人間による防災/公開承認は自動テストで代替できない。**

依存: **Depends on #430**。親が未統合の間はS2をDraft/blockedとし、親のmain統合後に最新mainへ追従させ必須CIを再実行する。一般公開禁止。必要な追加変更はE `gis/prototypes/f04-synthetic-timeline/**`とE CI入口だけ。
