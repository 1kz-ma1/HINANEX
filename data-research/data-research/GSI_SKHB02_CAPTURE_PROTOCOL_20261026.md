# GSI skhb02 HTTPS 原本取得・固定保存手順（2026-10-26）

状態：**A UNREVIEWED CAPTURE — 実原本は未取得、C人間承認・公開は未実施**。

## 公式ソースと意味
国土地理院の https://maps.gsi.go.jp/help/use.html の `skhb02` は「崖崩れ、土石流及び地滑り」の指定緊急避難場所GeoJSON（z10）。`disaster2=1`は対象災害種別の指定であり、危険区域/現在の開設/利用可能性や経路安全性の証明ではない。自治体別更新日・適用範囲やライセンスと利用上の注意は別途人間確認が必要。

## 新しい取得コマンド（インターネットが使える端末で明示的に実行）

    python data-research/tools/capture_gsi_skhb02_original.py --fetch --tile-x 909 --tile-y 403 --out-dir "$HOME/HINANEX-evidence/skhb02-10-909-403-20261026-UNREVIEWED"

上記座標・タイルはCLI説明用の合成例であり、現実の特定自治体の採用地点を示す根拠ではない。**実際の対象タイルは利用者が公式地図で確認して指定する。** `--fetch`を付けなければ接続しない。取得先はGitリポジトリ外の、新規フォルダで親フォルダは既存必須。

1リクエスト・公式HTTPSホスト/パス完全固定・TLS検証・リダイレクト拒否・20秒タイムアウト・12MB上限・HTTP 200のみ。原本のGeoJSON構造とz10タイル整合性をAで確認後、バイトそのままの `.geojson`、`capture_manifest_UNREVIEWED.json`、`a_inspection_UNREVIEWED.json` を保存する。既存フォルダは上書きしない。通信に失敗した場合はエラーで止まり、件数をゼロと解釈しない。

保存先の `etag` / `last_modified` は**HTTPレスポンスの観測値**であり、自治体による公式掲載日/更新日ではない。外部アーカイブをGitHubにコミットしない。`ARCHIVED_UNREVIEWED` はまだ独立認証・C受入前。

## C独立照合（Draft PR #312と併せて使う）

    python validation/validation/verify_gsi_skhb02_archive.py --raw "$HOME/HINANEX-evidence/skhb02-10-909-403-20261026-UNREVIEWED/skhb02-10-909-403.geojson" --a-report "$HOME/HINANEX-evidence/skhb02-10-909-403-20261026-UNREVIEWED/a_inspection_UNREVIEWED.json" --source-url https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson --report-out "$HOME/HINANEX-evidence/skhb02-10-909-403-20261026-UNREVIEWED/c_local_UNAPPROVED.json"

**C_LOCAL_MATCH_UNAPPROVEDも公的な承認ではない。** 真正な取得経路の独立再検証、人間の施設/掲載範囲/災害種別/更新日レビューと参照掲載ゲートを別途行う。GSIの一つのタイルの件数は市町村全体の件数を意味しない。

CIはネットワーク接続を行わず合成fixtureだけを使う。実取得しなければ実測件数は記録しない。今後の2×2災害/地域受入はIssue #89で継続。