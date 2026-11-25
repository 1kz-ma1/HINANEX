# GSI skhb02 実原本取得・A/C再照合：手動ワンクリック手順（2026-10-26）

## 前提条件と禁止事項

**この手順は災害時の安全判断・施設の開設認定・公式更新日確認・C人的承認ではない。**

利用前に、国土地理院の[免責事項・ご利用上の注意](https://www.gsi.go.jp/bousaichiri/hinanbasho-menseki.html)および[ダウンロード案内](https://www.gsi.go.jp/bousaichiri/hinanbasho.html)を確認すること。市区町村によって未掲載・情報が古い場合があり、最新情報は自治体に確認する。GSIタイル内の場所は市町村の網羅件数ではなく、土砂災害の危険区域ではない。

**人が事前に `z10 / X / Y` の実タイルを確定し、利用注意への同意とGitHub Actionsアーティファクトへの短期間の保存を了解した場合のみ実行する。** タイルの座標は無条件にユーザーの現在地・居住地・避難先に置き換えない。

## GitHub Actionsからの実行（依存PRがmainへ統合された後のみ）

1. A [#310](https://github.com/1kz-ma1/HINANEX/pull/310)、A [#313](https://github.com/1kz-ma1/HINANEX/pull/313)、C [#312](https://github.com/1kz-ma1/HINANEX/pull/312)、C [#314](https://github.com/1kz-ma1/HINANEX/pull/314)の統合・安全審査を終える。**この共通Workflow PR単体では実データにアクセスできない。**
2. このWorkflowがmainに入った後、GitHub → Actions → `GSI skhb02 manual evidence capture (UNREVIEWED)` → `Run workflow`。資料上のタイル `tile_x` と `tile_y` を手で指定。0〜1023の範囲。`acknowledged_gsi_terms`にチェックして1回実行。
3. このWorkflowはGitHub-hosted runnerから**1回だけ**正規のGSI配信ホストへHTTPSリクエストする。接続不能・取得元変更・GeoJSON形式不備・座標とタイルの不整合では失敗して止まる。失敗を「未掲載」や件数0と解釈しない。
4. 成功時は3日間だけActions Artifactsに、**原本バイト**、A未承認検査レポート、A未承認取得証跡、C未承認ローカル再照合結果、GSI注意事項を保存する。リポジトリ、Render、D/E公開データ、ユーザープロファイルは変更しない。
5. 人間が原本と自治体更新時点・掲載範囲・GSI利用条件をレビューし、独立したC取得元検証と人的レビューを別途実施する。Cの`LOCAL_*UNAPPROVED`の一致だけで公的な配信元の真偽は証明されない。

## 例と制限

z10/x/y=10/909/403は既存の**合成テストで使ったタイル例**。実地域の指定避難場所件数を保証せず、対象地域が正しいかを計算・確認する工程も別途必要。`Run workflow`時に手入力が必須で既定値はない。

GitHub Actionsの `workflow_dispatch` は既定ブランチ上のWorkflowだけ実行可能。依存が揃っていないDraft段階ではこのファイル自体がCIを通っても実際の取得は未実行。

## 状態の違い

- `CI PASS`: 合成テストや構造ガードが成功。
- `ARCHIVED_UNREVIEWED`: 1リクエストの原本保存が成功。
- `C_LOCAL_CAPTURE_CHAIN_MATCH_UNAPPROVED`: 保存済み原本／A検査／A取得報告のローカル内容が一致。
- **`C HUMAN APPROVED`：このWorkflowからは絶対に出力しない。**

GitHubから取得したアーティファクトを第三者に提供する場合は、GSIの利用条件と注意事項を一緒に提示し、人間の承認前に避難行動の判定へ利用しない。