# GSI skhb02 A取得マニフェストのC側ローカル証跡照合（2026-10-26）

**DRAFT / UNAPPROVED**。PR #312に依存するC単独の検証機能。A側PR #310および#313から生成されるJSONの値を無条件には信用しない。

## 入出力
同一原本のraw GeoJSON、A構造検査レポート、A取得マニフェスト、正確なGSI URLを指定する。Cは自前のGeoJSON再検査とWeb Mercatorタイル照合のうえ、
保存原本のSHA256、バイト長、取得時刻（タイムゾーン必須・未来拒否）、ホスト・HTTP 200・転送最終URL・feature数、未承認と公開禁止の各フラグを比較する。
レスポンスヘッダーは観測値（NULL可）であり、自治体公式更新日へ変換しない。

検証結果は `C_LOCAL_CAPTURE_CHAIN_MATCH_UNAPPROVED` または `C_EMPTY_TILE_COVERAGE_UNKNOWN` のみ。**実際のHTTPS取得をCが独立に再実行したわけではない**ため、取得元の真正性、公式更新日・自治体掲載範囲・施設同一性・最新開設情報・安全性・人間の独立承認はすべて未成立。

## コマンド
    python validation/validation/verify_gsi_skhb02_capture_chain.py --raw /outside-repo/capture/skhb02-10-909-403.geojson --a-report /outside-repo/capture/a_inspection_UNREVIEWED.json --capture-manifest /outside-repo/capture/capture_manifest_UNREVIEWED.json --source-url https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson --report-out /outside-repo/capture/c_capture_chain_UNAPPROVED.json

例のタイル座標は書式の説明のみ。原本のURLから受入対象自治体や危険区域を自動決定しない。

## 保留条件
1. #310→#313 による実原本取得とA保存。取得できないなら件数は UNKNOWN。
2. 独立した取得経路または署名された公式原本の真正性検証。現時点のCローカル一致は取得元を認証しない。
3. 人間が公表日・自治体区域・災害属性の意味・施設更新状況を確認し、別途C正式承認。
4. D/Eへの接続は別契約・別PR。すべての災害時の実行可否／公開許可は false。

合成のみの回帰テストは既存の validation/validation unittest discoveryで実行する。