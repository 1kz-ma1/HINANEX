# F01 洪水Scenarioのページ操作とフォーカス（Issue #426）

既存の地域詳細画面の洪水Scenario表示を対象とするB担当UI修正。Dの評価・共有契約・公式記号・施設安全性の判断を変更しない。

## 操作

- 20件ごとの「前の20件」「次の20件」の操作で、再描画された同じ向きのボタンへ `focus({preventScroll:true})` を復元する。連続したEnter操作でページを進められる。
- 先頭/最終ページで操作したボタンがdisabledになった場合は、件数・範囲・ページ番号の表示へフォーカスを移す。逆向きのボタンへ切り替えず、続けてEnterを押しても逆方向へ進まない。件数は通常のTab順には追加しない。
- キーボード操作後のボタン/件数にはフォーカス枠を表示する。ページの再読込・地域切替・合成デモ読込ではフォーカスを強制移動しない。
- 既存の20件上限とDが与えた順序を保持する。UNKNOWN、○などの元記号、照合状態、出典、利用階の原文、安全性/開設未確認の説明は不変。

## 実Chrome回帰

リポジトリrootを基準に、実際の `frontend/index.html` / CSS / ESMをloopback HTTPで読み込む。既存の合成RegionExportへ45件の架空Scenarioを付け、利用者操作の「合成デモ」から読み込む。通常の実データ読込失敗時に合成Fixtureへ暗黙fallbackしないことも確認する。

```powershell
cd frontend
$env:CHROME_BIN = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:F01_REQUIRE_CHROME = '1'
node --test tests/flood-scenario-http-browser.test.cjs
```

- 320/390/1440 CSS pxでnative Enterによる1→2→3ページと逆方向の操作、境界のdisabled/件数フォーカス、再Enterの非作動を確認する。
- 非ゼロscrollYと画面外の操作ボタンを事前にassertし、フォーカス復帰によるスクロールを検出する。ページのsmooth-scroll設定は変えず、テストの初期位置設定だけをinstantにする。
- 元記号/UNKNOWN/出典追跡を保持し、0件/不正ID/Scenarioなし/HTTP503では前の一覧・ページ操作を消す。再読込は1ページ目。実行時JS例外・ページの外部リクエスト・端末保存の追加なし。
- Chrome/CDPの起動・終了処理は既存F02 HTTP回帰を基にした新しいテスト専用helper。WindowsのDevToolsActivePort一時ロックは起動待ち30秒の範囲で再試行し、恒久的失敗はFAIL。既存F02テストは書き換えない。
- CIでChrome不在ならFAIL。ローカルでChromeがない場合はSKIPを明示し、PASSと主張しない。

修正前の既存UIでは、320pxの実Chromeで2ページ目へ進んだ後に「次の20件」へのフォーカス保持assertがFAILした。修正後のPASS/FAIL・対象SHA・全frontend/CI結果はPRへ記録する。

## 実機・公開境界

**Device QA: DEFERRED / Issue #372 DQA-008**。物理Android/iOS/Safari/VoiceOver/TalkBack、手動タッチ/読み上げ、独立HARはNOT_RUN。QA-1（2026-12-06 JST）候補、担当UNASSIGNED。自動Chromeの成功は実機受入ではない。

GPS・経路・保存・外部API・実施設データ・新しいSchemaは追加しない。F02/F05の非公開配信ガードを維持。公式資料/原本権利、施設位置/開設/安全性、経路、一般公開、Render LIVE受入は別ゲート。本修正は#371/#362のB1採用を承認しない。AIによるmain mergeは行わない。
