# F05/B2 — 合成データの根拠付き2施設比較（Issue #398）

**非公開・合成Fixture限定・ローカルHTTP検証専用。** F05/B1 [PR #371](https://github.com/1kz-ma1/HINANEX/pull/371) のマージ待ちに依存しない小さなB担当スライスです。

## 実装範囲

- `index.html`: スマホ幅対応の比較/本人選択UI。表示は `textContent`、ボタンは標準の `button`。ローカルHTTPのloopback origin以外では画面本体を表示しない。
- `model.js`: 独立した合成Fixture検証・表示状態・最大2件比較・本人選択のメモリ内状態。D/Eコードや共通Contractを変更しない。
- `fixtures.js`: 完全な架空の3施設。CANDIDATE/EXCLUDED/UNKNOWNは**合成であらかじめ与えられた分類の表示**に過ぎない。現実の評価結果は作らない。
- `model.test.js`: 形式/出典/対象災害不一致、重複ID、UNKNOWN不変、ゼロ件/ゼロ一致/模擬失敗、2件制限、選択消去、XSS回避、一般ドメイン拒否などのNodeテスト。

この画面は **本物のRegionExportやD ScenarioResultを読み込まない**。Dの既存status名は表示値としてのみ使用し、安全な避難先、現在開設、災害適合、位置、経路、ランキングは生成しない。

## Windows 11で実行

リポジトリのrootで、PowerShellから以下を実行:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Chromeで `http://127.0.0.1:8000/frontend/prototypes/f05-flood-journey/b2-compare/` を開く。

合成3件 → 架空施設A/B選択 → 二つの理由/未確認事項比較 → 本人確認対象を選択。検索/区分変更、Fixture切替で前の選択を消す。**取得失敗を模した選択肢は実際の通信を行わず、モックの失敗状態を表示する。**

### キーボード操作（B-Dev Issue #410）

比較に追加/解除、本人確認対象を選択した際は、画面の再描画後も**操作した架空施設の新しいボタンへフォーカスを復元**します（`focus({preventScroll:true})`）。連続してEnterで選択・解除でき、意図しない画面スクロールを避けます。繰返し現れる比較ボタンは、アクセシブル名称に**架空施設名と操作内容**を含めます。これは合成・非公開画面の操作性改善であり、実施設の選定・安全性判断・データ承認ではありません。

`browser-http.test.cjs` で追加/解除・本人選択後の実Chromeフォーカス、`aria-pressed`とアクセシブル名称、繰返しEnterを回帰検証します。さらに **320×480 CSS pxの実Chromeに非ゼロのスクロール位置を設定し、画面外の一覧A/Bと本人選択Bのボタン操作後も `scrollY` が変わらない**ことを検証します。実行前にページが実際にスクロール可能で、対象ボタンが画面外にあることをassertして、常に`scrollY=0`の無効な試験を防ぎます。物理Android/iOS/Safari/VoiceOver/TalkBackは別途DQA-005で確認します。

## テスト

```powershell
cd frontend
node --test prototypes/f05-flood-journey/b2-compare/model.test.js
node --test prototypes/f05-flood-journey/b2-compare/browser-http.test.cjs
npm test
npm run lint
npm run build
```

`browser-http.test.cjs` は 127.0.0.1 の一時HTTPサーバーから既存HTML/ESM/架空Fixtureを配信し、実headless Chrome（CDP）で比較・選択リセット・異常系・画面幅320/390/1440px・Tab/Enter・通信/保存の有無を検査します。Chromeは `B2_BROWSER_BIN` または `CHROME_BIN` で指定可能です。**CIでChromeがない場合はFAIL**、ローカル実行ではSKIPと明示します。新規NPM依存は不要です。

GitHub Actionsの `test` はmain統合可否判断の必須ゲート。2026-11-17の [PR #405 initial HEAD `3526c9e` のrequired CI](https://github.com/1kz-ma1/HINANEX/actions/runs/43989795917) で、**Frontend Node 114/114 PASS、失敗0・skip0、B2 Chrome HTTPテストPASS**（GitHub Actionsのログで確認）。この記録は**初回HEADの証拠**で、README追記後のHEADのCIは別確認が必要です。

headless Chromeの成功は物理スマートフォン、Safari/VoiceOver/TalkBack、Render配信と公式災害情報の人間承認の代替ではありません。

## 配信・権利の安全境界

- mainの `deploy/build_staging.py` は `frontend/prototypes/f05-flood-journey` **ディレクトリ全体を配布から除外**する（PR #377）。B2の5ファイルは**すべてその配下**。B2用コードを別の公開ディレクトリに置かない。
- **PR #371の新しいF05/B1ページは含めない**。ブランチは最新mainから独立し、F01/F02/E/D/Schema/Deployを編集しない。
- 画面自体の「localhost以外でブロック」は二次防御であり、**配布除外の代わりではない**。
- 原本CSV/GSI/実施設属性・座標・開設/経路の公式承認は [Issue #366](https://github.com/1kz-ma1/HINANEX/issues/366) など別ゲート。F07 [#358](https://github.com/1kz-ma1/HINANEX/issues/358) はHOLD。
- 公式出典と施設IDをD実モデルから接続するには別途D/SharedのContract受入が必要。本スライスのローカルUIや合成statusを実施設の安全判断へ流用しない。

## 受入記録

- `Implementation`: 5ファイル、`frontend/prototypes/f05-flood-journey/b2-compare/**` のみ。
- `Passed`: Node単体テストおよびrequired CIはそれぞれ実行結果をPRに記録する。
- `Not run`: **この実行者自身の独立ローカル手動Chrome操作**、Android/iOS/Safariの物理端末・VoiceOver/TalkBack、独立HAR、実Renderの公開URL受入。CIのheadless Chrome E2Eは別途PASS済み（上記の実行HEADを参照）。物理端末は [Device QA #372](https://github.com/1kz-ma1/HINANEX/issues/372) に登録する。
- `Published`: NO、`main merged`: NO、`Decision`: Draft/blocked、`Safety`: NO-GO。
