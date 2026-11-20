# HINANEX F17 — 独立した模擬避難判断トレーニング v0.1（未承認）

**状態:** IMPLEMENTATION PROTOTYPE / LOCAL HTTP ONLY / PUBLICATION NO-GO。2026-11-27実機QAに向けた操作練習であり、正式採用・一般公開・災害適合性判定は承認されていない。

## 採用する初期仕様

- **Step 1 — 情報確認:** F17作成の架空の洪水シナリオ1件、訓練用出典、未確認事項を表示。練習上の確認条件（ペット同行、段差の少なさ）を任意指定。
- **Step 2 — 比較:** 完全架空の施設A/Bを2列または縦列に並べ、架空出典・条件に関する架空の記載・未確認事項を表示。順位付け、適合判定、開設判定なし。
- **Step 3 — 本人選択・振り返り:** 本人が2件のどちらかを明示選択し、「振り返る」を押した場合だけ、選択内容と未確認事項を表示。正解はない。選択は実避難先の確定ではない。
- ステップ戻り・条件変更・別の選択時に選択／振り返りを破棄。中断・不正アクション・不正Fixtureはfail closed。やり直しは初期状態へ戻す。
- 画面の共通ヘッダーで「完全架空」を常時明示し、ブラウザ内の状態以外は記録しない。JavaScriptの実行はlocalhost / 127.0.0.1 / [::1] のHTTP originに限定。CSPで接続・外部画像・フォーム送信を無効化。
- `frontend/prototypes/f17-training/**` 以外にF17本体・QAを配置しない。既存F01/F02/F05、F04、F07、Dのモデル/Contractとは接続しない。

## 意図的に実装しない将来拡張候補（正式採用ではない）

- 複数の架空シナリオ、読み上げ/字幕、訓練完了の自己評価、利用者別の条件追加。
- F01の公式情報・F02施設記録・DのS1 reducerと連携した実データ版やGPS、経路案内、保存、ログイン。
- 災害情報や施設情報の自動判定、適合性ランキング、避難先の推奨。

上記はいずれも**新しい仕様・安全性審査・出典/Contractの承認が必要**。今回のコードを実データへ結線してはならない。

## 開き方・テスト

```bash
# リポジトリ root で起動。ファイルURLや外部ホストでは不可。
python -m http.server 8000 --bind 127.0.0.1
# http://127.0.0.1:8000/frontend/prototypes/f17-training/

cd frontend
node --test prototypes/f17-training/model.test.js
node --test prototypes/f17-training/browser-http.test.cjs
# または npm test（自動検出）
```

Chrome E2Eは自前のloopback HTTPサーバー・実Chromium CDPを使う。`F17_CHROME_BIN` または `CHROME_BIN` でChrome実行ファイル指定可。CIでChromeがなければ失敗（ローカルは明示SKIP）。320/390/1440 CSS px、Tab/Enter/Space操作、画面遷移、再選択、中断・リセット、実HTTP再読み込み、JavaScript例外、外部リクエスト、横スクロール有無を検査する。物理端末／支援技術の人間QAは別途行う。

## 非公開ガード / 統合条件

現行Render builderはFrontendをコピーするため、このディレクトリを**公開から丸ごと除外するsharedの別PR #437 が必須**。F17本体PRには `Depends on: #437` と記載し、shared guardの最新mainへの統合・配信物の非公開検証・required `test` SUCCESS・人間Merge Captainの判断前にはmainへ統合しない。ローカルHTTP判定・CSPは二次防御であって公開除外の代替ではない。

**実データ・自治体の判断・実際の開設/安全/経路・パーソナルな条件・端末保存・外部APIは一切使用しない。**
