# F07 参考経路：独立ローカル合成試作（2026-11-17）

**状態：PROTOTYPE / PRIVATE / NOT APPROVED / F07 REAL ROUTE HOLD**。Issue #358 の実経路公開HOLDは変更しない。2027-02-09 MVPに向けた操作・状態管理だけを検証する。実施設への参考経路は未提供。

## 現行mainとの差分とファイル

- 既存の `gis/gis/js/flood_discovery.js` / `reference_site_compare.js` は既存データの参考閲覧であり、F07の経路計算や描画ではない。再利用できる実ルート描画APIはないため、独立の合成模式図を追加する（実GISは一切importしない）。
- `index.html` / `style.css`: 架空地点の固定選択、模式図、アクセシブルな状態/警告表示、幅320/390/1440px。
- `route-model.js`: CommonJS + browser両用の純粋なセッション状態機械。合成画面単位のみを扱う。
- `app.js`: モデルとDOM/SVGの接続。条件変更・失敗で旧線を即時クリア。
- `test-node.cjs`: 状態遷移、NO-GO、古い線の破棄、未知地点拒否、CSP、Renderコピー境界。
- `test-browser.cjs`: ローカルHTTP + headless Chromiumで実DOMを使った幅/操作/フォーカス/NO-GO回帰。

## 使用方法（外部ネットワーク不要）

リポジトリ直下から：

```sh
node gis/prototypes/f07-reference-route/test-node.cjs
node gis/prototypes/f07-reference-route/test-browser.cjs
python3 -m http.server 8765 --bind 127.0.0.1 --directory gis/prototypes/f07-reference-route
```

ブラウザで `http://127.0.0.1:8765/index.html` を開く。外部サーバーへ配信しない。ブラウザテストは `chromium` 実行ファイルが必要（別名の場合は `CHROMIUM_BIN` で指定）。S2からF07 Nodeテストは既存GIS CI入口 `gis/tests/map_controller.test.js` を通じ required `test` に参加する。Chromiumの実HTTP検査は別途実行するため、実行結果をPRに区別して記録する。

## 状態契約・受入

| 操作 | 期待状態 | 模式線 |
|---|---|---|
| 初期 / 地点未選択 | UNSELECTED | なし |
| 架空出発点と架空目的地を明示選択 | READY | なし |
| 正常生成 | SHOWN | 合成模式線のみ |
| 出発点/目的地/条件/失敗トグル変更 | READY または UNSELECTED | 即時破棄 |
| 生成失敗または未選択でgenerate呼出 | NO_GO | 即時破棄 |
| 解除 | READY または UNSELECTED | 即時破棄 |

図形の `x/y` は `svg viewBox` 内のレイアウト単位で、実世界の緯度経度/道路/距離/時間ではない。模式線パターンは交通手段・アクセシビリティ・災害リスクを反映しない。安全・通行可能・開設・施設適合を推測しない。

GPS、住所取得、実座標、地域データ、実ルートAPI、第三者送信、localStorage、Cookieは使用しない。CSPはネットワーク接続を禁止。URLから地点を読まない。`gis/gis/` をコピーする既存 `deploy/build_staging.py` の対象外であり、Render bundle混入防止はNodeで静的に回帰検証する（デプロイ実測とは別）。他担当ファイルは無変更、既存Draft #311の4ファイルとは重ならない。実機QAは Issue #372 に `DEFERRED` として登録し、未実施をPASS扱いしない。

## 将来のゲート

合成UIの受入は実経路GOではない。F02→F05の本人選択、終点の施設ID・入口等の公的根拠とC/人間承認、経路サービスの同意・規約・送信情報、実機QAと公開審査が必要。Issue #358がNO-GOの間、一般公開案内に接続しない。

## F07 S2 — 誤入力のfail-closed・読み上げ・必須CI (2026-11-17)

- **差分**: 架空の出発点・目的地・表示条件と表示中/未表示を文で確認できる `#selectionSummary` を追加。従来のSVGは変更せず、文字だけで現在の合成状態が読める。警告と `role=status` は維持。
- 未定義の条件IDが渡された場合、以前のように自動でパターン1へ置き換えない。モデルは `condition=null`・`NO_GO`・`route=null` とし、明示的な有効条件の再選択まで生成不可。内部モデルから直接 `generate()` しても経路は戻らない。
- 既存の地点/条件変更時の古い経路破棄、出発点の明示選択、合成失敗、CSP `connect-src 'none'`、No GPS/No API、Render除外は維持。実施設の受入/公開可否に関係しない。
- **必須CI**: `gis/tests/map_controller.test.js` 末尾で本ディレクトリの `test-node.cjs` を `require` し、既存E GIS Node回帰の実行経路へ組み込む。単独テストと共通の正本を使い、同内容のテストはコピーしない。Chromiumの実HTTP E2Eは引き続き個別QAであり、required CIがブラウザを起動したとは主張しない。
- 新規Node回帰: 未対応条件時NO-GO/経路即破棄、明示的な条件復旧、32連続操作のrevision・線破棄。ブラウザ回帰: 未対応条件のNO-GOとテキスト要約。
- **未実施/別ゲート**: Android/iOS実機と読み上げ、Render LIVE 404、公的施設/経路API・移動手段の審査。Issue #358はHOLD、Issue #372 DQA-006はDEFERRED。
