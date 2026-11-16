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

## テスト

```powershell
cd frontend
node --test prototypes/f05-flood-journey/b2-compare/model.test.js
npm test
npm run lint
npm run build
```

GitHub Actionsの `test` はmainへの統合可否判断の必須ゲート。ただしCI成功はローカル実Chrome/物理スマホの検証や人間の公式災害情報承認を意味しない。

## 配信・権利の安全境界

- mainの `deploy/build_staging.py` は `frontend/prototypes/f05-flood-journey` **ディレクトリ全体を配布から除外**する（PR #377）。B2の5ファイルは**すべてその配下**。B2用コードを別の公開ディレクトリに置かない。
- **PR #371の新しいF05/B1ページは含めない**。ブランチは最新mainから独立し、F01/F02/E/D/Schema/Deployを編集しない。
- 画面自体の「localhost以外でブロック」は二次防御であり、**配布除外の代わりではない**。
- 原本CSV/GSI/実施設属性・座標・開設/経路の公式承認は [Issue #366](https://github.com/1kz-ma1/HINANEX/issues/366) など別ゲート。F07 [#358](https://github.com/1kz-ma1/HINANEX/issues/358) はHOLD。
- 公式出典と施設IDをD実モデルから接続するには別途D/SharedのContract受入が必要。本スライスのローカルUIや合成statusを実施設の安全判断へ流用しない。

## 受入記録

- `Implementation`: 5ファイル、`frontend/prototypes/f05-flood-journey/b2-compare/**` のみ。
- `Passed`: Node単体テストおよびrequired CIはそれぞれ実行結果をPRに記録する。
- `Not run`: 実ChromeでのB2操作・画面幅320/390/1440px・Android/iOS/Safari・独立Network HAR。物理端末は [Device QA #372](https://github.com/1kz-ma1/HINANEX/issues/372) に登録する。
- `Published`: NO、`main merged`: NO、`Decision`: Draft/blocked、`Safety`: NO-GO。
