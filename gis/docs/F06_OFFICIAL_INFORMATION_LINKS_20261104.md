# F06-L01 公式の警報・避難情報への入口（静的リンク）

- 日付: 2026-11-04
- 状態: **PROTOTYPE / PR REVIEW（未統合）**
- 仕様: [F06仕様（Draft #346）](https://github.com/1kz-ma1/HINANEX/blob/docs/feature-specs-20261030/docs/strategy/features/06_OFFICIAL_ALERTS.md)
- スライス: **P1の「公式サイトへのリンク」だけ**。P3の警報データ取得・自動更新・通知・開設状況連携は未実装。
- 範囲: `gis/**`。F01の洪水浸水想定の閲覧、F02の施設検索、RegionExport v0.9とC検証情報を変更しない。

## 挙動

- GISの「災害情報」メニューから独立した「公式の警報・避難情報を確認」を開く。
- 現在の `#region` 選択 `13123`（江戸川区）、`15100`（新潟市）、`23100`（名古屋市）に従い、対応する自治体の**外部公式サイトへのリンクだけ**を表示する。
- 共通の気象庁「あなたの街の防災情報」と「キキクル」へのリンクは常に表示し、移動先で地域と発表時刻を確認してもらう。
- 未対応のコード／未選択の場合は自治体リンクを削除・非表示にし、**未登録は警報なしではない**ことを説明する。
- 外部リンクは明示的なユーザー操作で新しいタブに開く（`target=_blank rel=noopener noreferrer`）。新しいAPI通信、更新確認、状態推定、GPSや閲覧履歴・設定の保存はしない。
- 独立パネルを開く際には他のGISパネルの重なりを避ける。Esc/閉じるで画面を閉じ、表示可能なメニュー見出しへフォーカスを戻す。

## 公式一次サイト確認（2026-11-04）

| 区分 | 表示名 | URL | 確認根拠・用途 |
| --- | --- | --- | --- |
| 江戸川区 | 江戸川区防災ポータル | https://bosai.city.edogawa.tokyo.jp/ | 江戸川区公式サイトが防災ポータルを案内。同ポータルに避難指示等・避難所開設などの区の発表への入口がある |
| 新潟市 | 防災・緊急情報 | https://www.city.niigata.lg.jp/kurashi/bosai/index.html | 新潟市公式「災害時の情報発信」に、市公式ホームページの緊急情報を確認する入口として掲載 |
| 名古屋市 | 防災ポータル | https://www.city.nagoya.jp/bousaiportal/index.html | 名古屋市公式の防災・危機管理ポータル。市の緊急情報への入口 |
| 気象庁 | あなたの街の防災情報 | https://www.jma.go.jp/bosai/ | 気象庁公式入口。利用者が地域を指定する |
| 気象庁 | キキクル | https://www.jma.go.jp/bosai/risk/ | 気象庁の雨による危険度分布。HINANEXの静的洪水浸水想定とは異なる |

根拠ページ:
- 江戸川区: https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/oshirase/bousaiapuri.html （公式ポータル紹介）
- 新潟市: https://www.city.niigata.lg.jp/kurashi/bosai/bosai_taisaku/index_koujo/saigai-joho.html （公式情報発信手段）
- 名古屋市: https://www.city.nagoya.jp/bousaiportal/index.html
- 気象庁: https://www.jma.go.jp/bosai/ , https://www.jma.go.jp/bosai/risk/

**注**: リンクの存在と出版社・発信主体を確認したもので、現在の警報/避難指示の有無、外部ページの可用性、区域・発表時刻や内容の真偽をHINANEXが検証したという意味ではない。外部ページの更新や変更に応じた再確認が必要。閲覧中の地域コードは外部URLのパラメータに渡さない。

## テスト・品質ゲート

- 合成DOM `node gis/tests/official_alert_links.test.js`: 3地域の切替、未対応でリンクなし、JMA固定リンク、外部アクセス/端末保存なし、Esc/重なり。
- required `test`: `gis/tests/facility_list.test.js` からF06合成テストを読み込む。
- E Chromium browser smoke: 390px/1365px、公式リンクと地域切替、未対応地域、Escとフォーカス。**外部の自治体公式サイト/JMAの通信は発生させずリンク文字列のみを検証**。
- 実Safari/スマホ、リンク先での表示・地域選択、公式元サイトの変更監視、アクセシビリティの最終評価、Render Stagingの人間受入は未実施。
- 最新mainと差分、CI、Scope Guardを確認して、Merge Captainが統合可否を判断する。

## 今後

- **F06-L02（P3、HOLD）**: 警報の自動取得・更新判定・発表時刻表示・通知（公式API/許諾/対象地域/障害/負荷/権限設計が成立してから）。
- **F02/F05との接続は保留**。F01の想定被害レイヤーをリアルタイム警報や避難の適否判定に変更しない。
