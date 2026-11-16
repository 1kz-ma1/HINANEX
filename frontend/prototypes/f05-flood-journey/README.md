# F05/P0 ローカル洪水体験試作（Issue #362）

**状態：Draft / 未承認・非公開。** F01 GISとF02 read-only画面を本人操作で別々に確認するだけ。地域選択は江戸川区の厳密コード 13123 のみ。洪水・位置・施設名を自動結合せず、施設推薦・現在開設判定・参考経路・端末保存は実装しない。

## 起動

リポジトリのルートで以下を実行する。

    python -m http.server 8000 --bind 127.0.0.1

ブラウザで http://127.0.0.1:8000/frontend/prototypes/f05-flood-journey/ を開く。

- F01へのリンクは地域情報を渡さない。地図側で本人が地域と出典・想定条件を確認する。
- F02リンクはHTTP loopbackでかつ江戸川区を本人が選択した場合のみ作成。データが欠損する場合はF02の既存のエラー表示に委ね、合成で代用しない。
- 一般公開ドメインではF02リンクを表示しない。

## 公開・統合ゲート（重要）

**Deploy非配信ガードPR #377は2026-11-16にmainへ統合済み**。現在のビルダーは `frontend/prototypes/f05-flood-journey/**`、`frontend/src/f05-journey-model.js`、対応するBテスト・文書を静的公開バンドルから除外する。既存F02/F03非公開ガードも維持する。**2026-11-16追補：** Render実ログでmain `d461f5912216b54d3f30a2833eb12c08860b4e74` のLiveを確認。デプロイ後のChrome NetworkでF05 `index.html` とF02 `f02.html` がともに404であることを確認済み（[Issue #373](https://github.com/1kz-ma1/HINANEX/issues/373#issuecomment-6905481203)）。**ただし#371のF05ソースはまだmain未統合のため、ソース実在時のRender除外最終確認ではない。** また、ローカルChrome基本操作 F05-01〜14 は[本人報告でPASS](https://github.com/1kz-ma1/HINANEX/issues/372#issuecomment-6906107953)（新しいNetwork HARやSafari/Android物理端末の独立証拠なし）。#371のmain統合判断では、出典/非公開ガード、最新CI、Issue #362のスライス採用判断を別途確認する。B featureで`deploy/**`を変更せず、JSのローカル制限だけを配信除外の根拠としない。

正式利用条件や施設意味はIssue #366、オーナーの#362優先順位/実装承認が別途必要。公開GOではない。

## テスト

frontend ディレクトリで npm test、npm run lint、npm run build を実行する。F05純粋モデル・非公開制御は frontend/tests/f05-journey.test.js で検査。実HTTP Chrome、Mac Safari/Android実機、Render配布物受入は別のゲート。
