# E: GSI公式掲載地点の2地点比較（2026-10-20）

## CURRENT / 実装した機能（PR段階）
- Eの既存 `flood_discovery.js` によって **REFERENCE_ONLY / source_status=C_ACCEPTED / HTTPS replay MATCH** などの既存の検査をすべて通過した地物だけが比較の入力。
- Eで使用している GSI skhb01 z10 公式掲載地点の **最大5件**から、利用者が手動で異なる**2地点**を選べる。3件目は追加不可、選択解除可能。
- 比較項目：掲載名、公式住所原文、備考原文、指定地点からの直線距離（経路距離ではない）、source feature trace、公式GeoJSON原本URL。
- GSIのみの比較であり、Dの自治体施設とは**同一施設と推認しない**。掲載順位も安全・開設・推奨順位にしない。
- 地図の公式掲載情報パネルから手動で開く。通常は閉じており、スマホでは最大54%高のスクロール可能なシートにする。新規の地図マーカーやルート線を作らない。
- origin/region変更、再読込開始、出典未照合・タイル圏外ではセッションを破棄、パネルを閉じ、比較の選択内容を残さない。Dだけの表示モードでは比較パネルを閉じる。
- 比較用ロジックは新規 `gis/gis/js/reference_site_compare.js` のメモリ内セッション。データを再取得・ローカル保存・外部送信しない。すべて表示テキストは `textContent`。公式リンクは既存の `safeExternalUrl` を通す。
- B比較ラボPR #276とは別の独立したE実装。そちらは**資料2件の比較**、こちらは**GSI掲載地点2地点の原属性表示**。B/GISを相互改造・統合していない。
- A/Cの自治体公式施設レビューとD3地域再生成（#264、#265、#266、#268）は独立したHOLDを維持。

## 受入シナリオ（手動未確認）
1. 既存の指定地点探索を実行、出典照合済みの参照地点が2件以上表示されたら「掲載地点を2つ比較（試作）」を押す。
2. 2地点選び、両施設の原文・公式source URLを開ける。3件目は選べず、解除で再び選択可能になる。
3. 選択済みの情報と直線距離が避難経路や安全推奨と誤解されないか確認。
4. 地点・地域変更、通信失敗、独立照合なし、GSI表示OFFで前の比較データが残らない。
5. iPhone Safari 390pxなどの狭い画面で地図を過度に覆わず、比較の開閉・縦スクロール・44px操作領域が利用可能。
6. GSI原文値に危険な文字列があってもHTMLが実行されない。
7. デモ中のピン操作・右側詳細カード、D/GSI表示切替、既存の地図レイヤーは退行しない。

## テスト
- `node gis/tests/reference_site_compare.test.js`：GSI実検証エンジンのsynthetic fixtureから入力して二件選択/解除/3件目拒否/破損/出典URLチェック/静的DOMを確認。
- 必須CIが実行する `node gis/tests/flood_discovery.test.js` から新テストを読み込み、shared workflowは変更しない。
- `node gis/tests/map_controller.test.js` のCSS/JSキャッシュキー期待値は新規map scriptに更新。
- GitHub `test` 成功と実ブラウザの操作成功は区別して記録する。

## FUTURE / 未実装
- 自治体施設とGSI掲載の同一建物判定、自治体施設の個別洪水適合判定、現在の開設・容量・混雑、現況災害判断、安全な経路、避難先の自動推薦。
- Bから検証済みE地点を読み込む共通画面、またはGSI/D跨ぎの比較には別途明示的な契約・受入判断が必要。
- 2027年2月9日を目標とするシナリオMVPの全工程（条件抽出→根拠比較→人間選択→参考経路）を本PRの完了と見なさない。

## 統合条件
Draft PRのままCI実行、desktop/mobile実機確認、A/C/Dの安全境界の独立維持を確認し、Merge Captainの判断を待つ。main push・自動merge・Renderデプロイは行わない。

## 2026-10-20 13時台：実Chromium比較操作の自動受入（合成fixture）

- 追加：`gis/tests/reference_site_compare_browser.js`。既存の `gis/tests/demo_20261022_browser_smoke.js` のE専用 `HINANEX_WHEEL_ONLY=1` profileから呼び出し、`main` のshared workflowは変更しない。
- **CI結果:** [required test #39370677376](https://github.com/1kz-ma1/HINANEX/actions/runs/39370677376) SUCCESS、[GIS Chromium #39370677402](https://github.com/1kz-ma1/HINANEX/actions/runs/39370677402) SUCCESS。
- desktop 1365×900 と mobile 390×844 で実Leaflet/Chromiumを起動。GSIタイル JSONのHTTP応答のみEテスト内で一時差し替え、C-accepted catalogの**schema・状態を模した明記済み合成fixture**を使用する。実在の自治体施設情報ではない。GISの通常データ・配布物や原本は変更しない。
- 実ブラウザ操作を自動化：表示前ボタン非表示→地点指定→合成GSI3件を出典検査経路から読み込む→明示的に比較を開く→2件選択→3件目無効化→選択解除・再選択→閉じて再開→地点を検証済み範囲外に移動すると比較を消去。
- PCでは比較2列、390pxでは縦1列。ダイアログがビューポートからはみ出さず、モバイルでは地図の54%を超えないことをDOM実寸で検証。選択したsource URLのHTTPSリンクと`noopener noreferrer`を照合。
- HTML混入を意図した合成名称が`<img>`タグにならず、`textContent`のまま可視化されることを確認。
- 未取得タイル・`source_status=PENDING` の負系も実ブラウザで確認。紫ピン／比較操作を創作しない。
- 出力証跡：workflow artifacts内 `reference_site_compare_browser_audit.json`、`gsi-comparison-ci-fixture-1365.png`、`gsi-comparison-ci-fixture-390.png`（[artifacts付きrun #39370677402](https://github.com/1kz-ma1/HINANEX/actions/runs/39370677402)、2026-10-27 UTC頃までの保持設定）。スクリーンショットは合成fixtureのみ。

**制約：** Chromiumの自動操作は通過したが、iPhone Safari実機、ユーザーが情報を誤認しないかの観察、現在の公式原本の更新確認、実GSIの配信到達性、Render本番・ステージングへの反映・閲覧は未実施。今回のCI成功はA/C正式承認・実災害時の安全性・実経路の検証ではない。
