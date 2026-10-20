# HINANEX：単独責任者＋独立したAI技術検証（2026-10-19）

**状態：試行可能／単独責任者による人間判断は未実施／C→D は HOLD。**

## 運用の切り替え

- A（原本の取得・内容抽出）、C（独立した原本・出力照合）、D（再生成・正規化）は、**人員の役職ではなくソフトウェアの責務境界**。実装・最終判断の人間は1人でよい。
- AIによる調査案と原本ハッシュ・実行レシート等の再現可能な検査は自動化し、人間は具体的な未解決点だけを確認する。
- 旧Cレビュー様式の「原本7件＋横断3件＝10行」の個別詳細台帳は監査証跡として残し、**同じ人が形式上AとCの別人として署名する必要はない**。
- 最終的に単独の責任者が判断・GitHub認証済みアカウントで署名する場合でも、**技術検証の独立性**は別に確保する。人間2名による独立承認があったとは記録しない。
- 今回はあくまで意思決定文書の準備。**Dへの投入承認、自治体情報の意味確定、GSIの洪水判定、本番公開の自動解除は行わない**。

## 人間の判断は4件（AI案、未署名）

| 論点 | 現在のAI調査案 | 安全なレビュー判断例（本人の意思決定ではない） |
|---|---|---|
| `C-SITE-OLD-NEW` 現・旧下小岩小学校 | 区の水害施設表・学校一覧・学校移転発表で、別住所・別校舎の文書上の事実を確認。**学校の供用開始日と防災施設指定日を区別** | 資料上の別敷地の事実だけ `ACCEPT_FACTS_ONLY`。現時点の旧体育館使用可能性や別データ施設ID対応は保留 |
| `C-MUNICIPAL-CROSSSOURCE` 市の水害表×位置CSV | CSVで現校舎・旧校舎が別座標なのに同じ学校URLを共有。URL・名称一致だけでは実敷地を識別できない | 個別結合を採用する意図があるなら `HOLD`、根拠が整ってから施設ごとに承認 |
| `C-GSI-FLOOD-SEPARATION` 自治体水害×GSI洪水 | 制度的な区別は確認できるが、今回の7原本には江戸川区の個別GSI `skhb01` 原本地物がない | 区分を混ぜない設計事実だけ `ACCEPT_FACTS_ONLY`。洪水候補判定は必ず `UNKNOWN` |
| `A-LICENSE` 再利用条件 | 区の一般Web、区のオープンデータ、都立・私立校では条件が異なり、7資料全件の共通ライセンスは未確認 | 原本を配布・転載するなら `HOLD`、出典別の条項を確認。内部の根拠参照と再配布を区別 |

レビュー選択肢：`ACCEPT_FACTS_ONLY`（明記した原文上の事実に限定して確認）、`HOLD`（証拠不足）、`REJECT`（根拠が違う）、`PENDING`（未判断）。
**`ACCEPT_FACTS_ONLY` は D データ結合許可でも「安全な施設」承認でもない。**

## 使用方法（Mac、GitHubでPR #270のコードが利用可能な状態）

1. GitHub上の [C PR #270](https://github.com/1kz-ma1/HINANEX/pull/270) にある `validation/validation/build_single_operator_review.py` を使う。既存の正式C JSON・レシート、およびAI事前レビューJSONをローカルの **Git管理外** に保存する。
2. 対象のファイルを指定して初期票を作る。

```bash
cd "$HOME/HINANEX" # 手元の実際のGit checkoutパスに置き換える
python3 validation/validation/build_single_operator_review.py \
  --formal-report /private/HINANEX/edogawa-C-20261014-v-20261016-UNREVIEWED.json \
  --receipt /private/HINANEX/edogawa-C-20261014-v-20261016-run-receipt-UNREVIEWED.json \
  --ai-prereview /private/HINANEX/HINANEX_EDOGAWA_7_SOURCE_AI_PREREVIEW_20261019_UNAPPROVED.json \
  --create /private/HINANEX/HINANEX-single-operator-decision-PENDING.json
```

3. 出力JSONの `decisions[0..3]` に判断・理由・読んだ一次資料URLを記入する。少なくとも1つの判断をした場合は `single_operator.github_login_claimed` と `reviewed_at_utc`（UTC）を記入する。AIの提案文・原本ハッシュ・source key順は変更しない。判断を変えるときは自分の理由も更新する。
4. `--create ...` を `--check /private/HINANEX/HINANEX-single-operator-decision-PENDING.json` に変更して、文書構造と元証跡との整合性を機械検査する。形式が正しくても状態は `HOLD_EXTERNAL_OWNER_SIGNOFF_AND_SCOPE_REQUIRED`。
5. 本人確認できるGitHubアカウントから [Issue #268](https://github.com/1kz-ma1/HINANEX/issues/268) へ、**判断した4件と個別の承認範囲、未確定事項、review packetのSHA256、対象原本SHA256** を記録する。これが追加の本人確認・監査リンクになる。ソフトウェアの `github_login_claimed` は自己申告であり本人認証ではない。
6. 施設ID間の同一視・特定の洪水CANDIDATE/EXCLUDED・Dへの実データ投入・本番反映を行う必要が出たときは、**それぞれ対象行と原本地物に限定して別途明示的に許可**し、従来のC→D受入ゲートと独立監査を満たす。4問を全部 `ACCEPT_FACTS_ONLY` にしても、既存ゲートは **HOLD** のまま。

## 根拠とチェック対象

- 公式C JSON SHA256：`ec7215818b79f0bd8680470e650103c2f09ddf928807819a8c5ea7886560f418`
- 公式Cレシート SHA256：`d47d219d388f672298405f7176e90bf0ab34a160989dd47f17e271a9a629f21c`
- Oct14/Oct16原本7件の取得Actions：[#38505232094](https://github.com/1kz-ma1/HINANEX/actions/runs/38505232094) ／ [#38857462945](https://github.com/1kz-ma1/HINANEX/actions/runs/38857462945)
- 詳細：A [PR #271](https://github.com/1kz-ma1/HINANEX/pull/271)、C [PR #270](https://github.com/1kz-ma1/HINANEX/pull/270)、D [PR #272](https://github.com/1kz-ma1/HINANEX/pull/272)。3本とも人間がmainマージするまでDraft/未統合。

## 検証境界

`build_single_operator_review.py` は C の `check_edogawa_review_packet.py` と同じ既存正式JSON・レシート検査を呼び出し、AI提案の資料7件・ハッシュ・版の整合性を追加確認する。原本全文を再取得しない。JSONの署名やGitHubログイン本人確認、法的な出典の利用許諾、施設の実際の開設・安全、洪水指定の効果、Dの変更権限は検証しない。改ざん・不整合時は失敗、整合時も実データ反映はHOLD。