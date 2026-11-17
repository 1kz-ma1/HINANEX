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
