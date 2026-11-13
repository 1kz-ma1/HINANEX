# F03/P-02 Issue #356 — 保存契約差分・最終QA報告（2026-11-11 JST）

**独立B試作のQA。Draft維持。本番GIS接続・保存契約の採用・main統合は対象外。**

- [Issue #356](https://github.com/1kz-ma1/HINANEX/issues/356) / [Draft PR #359](https://github.com/1kz-ma1/HINANEX/pull/359)
- ブランチ: `feature/b-f03-storage-contract-qa-20261111`
- 引継ぎHEAD: `04e7c1993aa1853c8be60f7d8c13fe1ea68b771c`
- 不具合修正・回帰テストのcommit: `9ffd05055b306e17401157b7ab52cd92f3d59c8d`
- 作業開始時に再取得したmain: `e0d6f7a01644948acc8be787b727b22c926b2442`。引継ぎHEADはbehind=0 / ahead=6。
- root/frontend AGENTS、対象README・テスト、#356・#359・#311・#346を確認。#359の差分はすべて `frontend/**`。未解決インラインスレッド0、レビュー提出・会話コメント0（確認時点）。GitHubではコンフリクトなし。
- 原本ZIPは実ファイルを読んだ。原本中の報告・指示文は参考資料として扱い、今回の依頼を置換しない。

## 参照原本と保存契約差分

原本: `HINANEX_F03_事前準備UI_レビュー修正版_20261104.zip`。
SHA-256: `eb539aea3d1e59fde19de63263bbc2856df80823c846bbeaf18ebc42a865dba5`。
13エントリ、Python `ZipFile.testzip() == None` を今回再確認。原本は変更・推測再作成していない。

#311は `4d22b2d649f169bf35448c7591f2ada21946dde3` の保存モジュール・Nodeテスト、
#346は `2b7ddb858e008a3da6c1391ecff39356d5630b17` の
[F03仕様](https://github.com/1kz-ma1/HINANEX/blob/2b7ddb858e008a3da6c1391ecff39356d5630b17/docs/strategy/features/03_PRE_EVENT_PREPARATION.md)を取得して照合した。両PRともDraft・未採用。

| 項目 | 原本F03修正版UI | [E Draft #311](https://github.com/1kz-ma1/HINANEX/pull/311) | 今回のB独立QA |
| --- | --- | --- | --- |
| 保存キー | `hinanex.preparedness.demo.v1` | `hinanex.gis.pre_event.optin.v1` | 原本キーを維持 |
| schema | `{selected_region:"13123",schema_version:1}` | `{schemaVersion:1,consentSaved:true,savedAt:ISO8601,profile:{regionCode,occupiedFloor,upperFloorAccess}}` | 原本の2キー完全一致・型・値を検証、追加キー拒否 |
| 入力項目 | 地域コード1項目、13123/15100/23100のみ | 5桁地域コード、1–200階またはnull、上階アクセスBooleanまたはnull | 1項目・3地域の表示例のみ |
| 180日ルール | 時刻なし、自動期限なし | 180日超・未来時刻で `STALE_SAVED_DATA`。自動削除ではない | 自動期限なしを維持。180日テストは対象外 |
| 読込 | 起動時にprobe書込・削除・読込 | factory無操作、明示 `read()` | 明示「保存済み設定を確認」のみ、起動時0操作 |
| 保存 | 明示クリック | `save(...,{consentGiven:true})`。実利用者向け同意UIなし | 明示クリック後、書込値の読み戻し一致でのみ成功 |
| 更新拒否 | setItem例外時に旧地域保持 | `STORAGE_UNAVAILABLE` | setItem例外時は旧地域保持。書込受付後の確認失敗は「未確認」 |
| 削除 | removeItem後getItemで確認 | `deleteSaved()`で確認 | 確認できた場合だけ削除成功。破損値も明示削除可能 |
| 保存の性質 | 平文、説明は限定的 | 平文・同一originから参照可能 | 共用端末・平文・同一origin JS・バックアップ保証なし・自動期限なしを明示 |
| 統合 | 独立UI | UI未接続Eモジュール | キー移行・相互読込・本番GIS接続なし |

原本と今回のHTML/CSS/JSを実際に差分比較した。主な差分は以下。

1. 自動 `readSavedRegion()` と保存可否probeを除去し、任意の明示読込ボタンを追加。
2. 保存直後の同値読み戻し、追加キー・不正schema拒否、読込失敗の警告。
3. 次回は手動読込になる説明、平文・共用端末等の注意表示。
4. 560px以下で操作3ボタンを縦並び・44px以上にする。
5. 今回追加した「未確認」表示・破損値削除経路（下記）。
6. 元ZIPの合成画像・インメモリ保存モックの13 PASSを実HTTPの証拠として流用しない。

## 今回再現・修正した不具合

修正前の実HTTP Chromeで **13 PASS / 3 FAIL / 0 NOT_RUN** を記録し、C14–C16が失敗することを確認した。

| ID | 再現条件・修正前の問題 | 修正 | 回帰 |
| --- | --- | --- | --- |
| F03-01 | 保存済み地域から変更。setItemは実際に成功、その直後のgetItemだけSecurityError。旧地域の「✓ 保存済み」が残る | 書込受付と検証完了を分離し、未確認表示に移行。自動で旧値を書き戻さない | C14 |
| F03-02 | removeItemは実際に成功、直後のgetItemだけSecurityError。削除済みなのに旧「✓ 保存済み」が残る | 削除を未確認と表示、成功文言を出さず、再読込・削除再試行が可能 | C15 |
| F03-03 | 破損JSONまたは不正schemaを明示読込。地域nullとなり削除ボタンも無効化される | 地域選択なしでも、読込失敗後の明示削除を許可。削除後のnull確認を必須化 | C16 |

一時選択でも「保存を削除」は実保存領域の削除・確認を試みるよう統一した。失敗時は削除済みと表示しない。
保存・削除が未確認の状態で、現在の表示地域を保存済みと断定しない。

テスト実行上の修正も2点実施した。Windows絶対パスの `F03_CHROME_BIN` に対応し、
ブラウザをCDP `Browser.close` で終了してから再起動、古い `DevToolsActivePort` を除去する。
Windowsで発生したC11の接続ファイル競合を是正し、再実行でC11を含む全16ケースを通過した。
任意の `F03_EVIDENCE_DIR` を指定すると、4幅の実画面PNGとSHA-256を出力する。テスト削除・skip化なし。

## 実HTTP Chromeケースと結果

以下は修正後のローカルWindows実Chromeでの結果。CIは別欄で照合する。
本物のHTTP・Chrome・localStorageを使い、異常系だけStorageメソッドへ例外/no-opを注入する。
ブラウザ全体の保存領域をインメモリモックへ置換していない。
CDPからボタンのclick/選択を起動しており、実利用者の同意やタッチ操作の受入を証明するものではない。

| ケース | 確認内容 | 結果 |
| --- | --- | --- |
| C01 | 保存値があっても未操作時のget/set/removeは0、地域を自動復元しない | PASS |
| C02 | 明示読込、同一origin JSから平文を参照できる | PASS |
| C03 | 明示保存、HTTP再読込、明示読込で復元 | PASS |
| C04 | 地域更新と実保存値の一致 | PASS |
| C05 | quota例外、旧地域表示・旧保存値の保持 | PASS |
| C06 | setItemがno-opでも新保存成功と表示しない | PASS |
| C07 | removeItemがno-opなら削除成功を表示しない | PASS |
| C08 | 削除のnull確認、再読込後も未設定 | PASS |
| C09 | 破損JSON、異なるschema version、追加gpsキーを復元しない | PASS |
| C10 | 操作中のページ要求に外部通信なし、現在URLとリンクURLへ地域コードを混入しない | PASS |
| C11 | 同じprofileでChromeプロセス再起動、明示読込でのみ復元 | PASS |
| C12 | 注意表示と観測したページ実行時例外0 | PASS |
| C13 | 320/375/390/430px、横はみ出しなし、3ボタンが幅200px以上・高さ44px以上 | PASS |
| C14 | 書込受付後の読込拒否で古い保存済みバッジを残さない | PASS |
| C15 | 削除受付後の読込拒否で古い保存済みバッジを残さない | PASS |
| C16 | 破損/不正schemaを読込後、地域未選択のまま明示削除できる | PASS |

**修正後: 16 PASS / 0 FAIL / 0 NOT_RUN。** C11はOSや物理端末の再起動ではなく、同一profileのChrome再起動相当。
容量不足・アクセス拒否は障害注入であり、実ディスク枯渇・OSポリシー変更そのものは行っていない。

## 実行環境・コマンド・全体テスト

2026-11-11 JST、Windows 11 build 26300、Node `v24.16.0`、
Google Chrome `156.0.8078.49`、headless CDP、ランダムポートの `http://127.0.0.1`、毎回専用の一時profile。

```powershell
cd frontend
$env:F03_CHROME_BIN='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:F03_EVIDENCE_DIR='<任意の証拠出力フォルダ>'
node --test tests/f03-storage-http-chrome.test.js
node --test --test-concurrency=1 tests/*.test.js
npm.cmd run lint
npm.cmd run build
node --check prototypes/f03-storage-contract-qa/app.js
node --check tests/f03-storage-http-chrome.test.js
```

Linux CIは既存 `test.yml` のNode 22とrunner内Chromeで `cd frontend && npm test` を実行する。
`npm test` の全体件数81にはF03のNodeラッパー1件を含む。内部の16ケースは別集計であり、81+16の独立テストとは数えない。

| 実行 | PASS | FAIL | NOT_RUN / 状態 |
| --- | ---: | ---: | --- |
| 引継ぎ時CI [42947220130](https://github.com/1kz-ma1/HINANEX/actions/runs/42947220130)、HEAD 04e7c19 | Node 81 / F03 13 | 0 | 0、required test SUCCESSをjobログと照合 |
| 今回の既存13ケース再実行（修正前、Windows） | 13 | 0 | 0 |
| 新規回帰追加・アプリ修正前 | 13 | 3 | 0、意図した不具合再現 |
| 最終Windows F03専用 | 16 | 0 | 0 |
| 最終Windows `tests/*.test.js`（F03実Chrome含む） | 68 | 0 | 0、このディレクトリの全件 |
| Windows `npm test`（Frontend全体） | 全体集計未了 | F02 acceptance 1件を観測 | F02後に進行停止し中断。全体PASSとは扱わない |
| 初回sandbox内Chrome | 0 | runner 1 | F03の13ケースはNOT_RUN（CDP接続不可）。通常実行で再検証 |
| 設定なしでの中間 `tests/*.test.js` | 67 | runner 1 | F03はChrome未検出でNOT_RUN。その後パス指定で68/68確認 |
| 中間Windows再起動競合 | 10 | 6 | C11起動失敗とC12–C16接続タイムアウト。終了・再起動処理修正後16/16確認 |
| lint / build / F03 JS構文 / diff check | 成功 | 0 | 未実行なし |
| 修正commit 9ffd050のCI | Node 81 / F03 16 | 0 | 0、required test SUCCESS |

Windows全体実行ではF02の機能確認ログまではPASSだが、テスト自体はFAILとなり終了しなかった。
F02には強制終了直後の一時profile削除経路があり、Windowsでの後始末が原因と考えられるが、原因確定・修正は今回のF03範囲外。F02は変更していない。
全体件数の最終判断はLinuxの最新HEAD CIログで別途行う。

### 最新CI照合

修正commitの[CI 42948934444](https://github.com/1kz-ma1/HINANEX/actions/runs/42948934444)、job `130288387432` の実ログを取得。required `test` SUCCESS、B Frontend Node **81 PASS / 0 FAIL / 0 skipped**、F03 **16 PASS / 0 FAIL / 0 NOT_RUN** を照合した。runnerはUbuntu 26.04、Node 22。
この文書・画像を追加した最終HEADのCI URLとcommit SHAは、PR本文および納品ZIPの `DELIVERY_METADATA.json` に記録する。
文書に残す検証commitと最終文書commitを区別する。

## 実画面証拠とハッシュ

4枚は今回の**実HTTP Chrome全ページPNG**。320/375/390/430pxをそれぞれ目視し、日本語表示、3操作の縦並び、説明の折返し、横はみ出しなしを確認した。
操作ボタンはそれぞれ252/307/322/362px幅、すべて44px高。物理スマホのタッチ検証ではない。

| 幅 | 実画面 | SHA-256 |
| --- | --- | --- |
| 320 | [PNG](evidence/f03-p02-20261111/real-http-chrome-320.png) | `2124920f5d6ae9891cba5e2b246ca4d53f9db4396c1f83aff6406d04a2e86035` |
| 375 | [PNG](evidence/f03-p02-20261111/real-http-chrome-375.png) | `0840e28a2e33488ab3ffca789dbf9606b8c7337b70cbfcae791710f59d32334f` |
| 390 | [PNG](evidence/f03-p02-20261111/real-http-chrome-390.png) | `632a2baecc42804a42ecaf87577df94a9e678fb1fa2496c4394c722ee65932bb` |
| 430 | [PNG](evidence/f03-p02-20261111/real-http-chrome-430.png) | `575623e9f1b89a46ccc2d7cb2403666d7c59abaf4e950854a12a3b56705a09a6` |

前回CIログ内の390px JPEG Base64も実際に取得・デコードした。
[元CIの実Chrome JPEG](evidence/f03-p02-20261111/ci-42947220130-real-http-chrome-390.jpg)は13,915 bytes、
記録値と実測SHA-256がともに `c3f03c275146a0dd6b90804d40e93050c39aefc368f79e9d1d8e3c9daa59b175`。
ただし日本語が欠字表示で、844px高の画像内に操作ボタンが入っていない。日本語の可読性・操作領域の目視合格根拠にはしない。
今回のWindows PNGとは別の証拠であり、原本ZIPの合成/参考スクリーンショットとも区別する。
原本の合成画像は今回のPASS根拠に含めない。

## リスク・未実施・今後の判断

- 平文localStorageは同一originのJS・端末の別利用者から参照され得る。暗号化保管庫ではなく、期限・バックアップ・端末移行を保証しない。
- 本試作は地域コード以外を保存しない。GPS、住所、氏名、健康・家族情報、利用階等は追加していない。
- 読み戻し一致はその時点の保存値の確認。将来の消失防止、ディスク永続化、複数タブ同時編集、第三者スクリプト耐性を保証しない。
- 外部公式リンクへの手動遷移は通信が必要。公式サイトの現在の応答、情報の最新性や避難先の安全性は検証していない。
- **NOT_RUN:** Safari/iOS、Android物理端末、物理端末/OS再起動、正式なプライバシー・法務審査、実運用の本人同意確認、スクリーンリーダーを含む正式アクセシビリティ受入、Render等の公開配信。
- **対象外:** B schemaにない180日失効。#311の180日テストはコードを読んだだけで今回再実行していない。Eモジュールの実ブラウザ受入も未実施。
- **残課題:** WindowsでのF02全体テスト終了処理。E #311のsaveはsetItem後の読み戻しなしで成功を返すため、E担当による別レビュー候補。Bから変更しない。

オーナーが決める事項:

1. 自動復元から明示読込へ変えた実験UXを製品として採用するか。
2. 地域1項目・期限なしと、Eの3項目・180日要確認のどちらを採用するか。正式キー・schema・移行計画はB/E共同で別途決定。
3. 共用端末の利用方針、同意説明、保存期間、プライバシー審査と削除手順の受入。
4. 物理端末・Safari・アクセシビリティを含む次の受入範囲、将来のGIS接続条件。

**検証完了は本番採用・Integration ready・Merge readyを意味しない。PR #359はDraftのまま、mainへはpush・mergeしない。**
