# 江戸川区原本：A/C 人間レビュー記録プロトコル（2026-10-19）

**状態：C技術比較 PASS／A・C人間レビュー未承認／D引継ぎ HOLD。** これは新しい承認ロジックではなく、既存の [2実取得回比較仕様](FINAL_SOURCE_RECAPTURE_20261016.md) と [C正式JSON引継ぎ](EDOGAWA_REAL_C_COMPARATOR_HANDOFF_20261019.md) に対する**署名・判断材料を揃えるための書類検査**。防災施設の同一性、指定状況、現在の開設・安全性は判定しない。

## 実装と使用

`validation/validation/check_edogawa_review_packet.py` はPython標準ライブラリだけで動作する。ネットワーク取得、原本の変更、D・B・Eへの書き込みを行わない。

Macの非公開レビュー環境で、正式Cレポートと実行レシートを指定する。**テンプレートや記入済みJSONはGit管理外**に保存する。

```bash
python3 validation/validation/check_edogawa_review_packet.py \
  --formal-report /private/HINANEX/edogawa-C-20261014-v-20261016-UNREVIEWED.json \
  --receipt /private/HINANEX/edogawa-C-20261014-v-20261016-run-receipt-UNREVIEWED.json \
  --create-template /private/HINANEX/edogawa-human-review-PENDING.json

# A・Cの担当者が記録し、本人確認可能なプロジェクトのレビュー手順で確認した後：
python3 validation/validation/check_edogawa_review_packet.py \
  --formal-report /private/HINANEX/edogawa-C-20261014-v-20261016-UNREVIEWED.json \
  --receipt /private/HINANEX/edogawa-C-20261014-v-20261016-run-receipt-UNREVIEWED.json \
  --check /private/HINANEX/edogawa-human-review-PENDING.json
```

対象CレポートSHA256：`ec7215818b79f0bd8680470e650103c2f09ddf928807819a8c5ea7886560f418`。実行レシートSHA256：`d47d219d388f672298405f7176e90bf0ab34a160989dd47f17e271a9a629f21c`。Git pinned SHA：`8615c0060a02f9c824ebc846dcf930b042a29a6f`。実行された比較の報告は原本7件中6一致・1件のHTML日時メタデータ差分。これらは**原本との同一性を示す技術証拠**であり、人間の意味解釈や承認ではない。

## レビュー単位（合計10件）

- **A担当（7件）**：`water_facilities`, `municipal_locations`, `municipal_school_list`, `municipal_primary_school_list`, `municipal_2025_school_relocation`, `tokyo_kasaikoka_school_access`, `kanto_ichiko_school_overview`。原本の出典、取得日と資料の更新日／適用日との違い、資料の対象範囲、表現上の注意、再利用・転載条件を**根拠のある範囲で**判定する。公表日／適用日を捏造しない。
- **C担当（3件）**：`C-SITE-OLD-NEW`＝下小岩小学校と旧校舎の時点・別敷地の根拠、`C-MUNICIPAL-CROSSSOURCE`＝水害時待避施設HTMLと自治体位置CSVを同じ施設として扱ってよいか（個別レコード・住所・時期に限定）、`C-GSI-FLOOD-SEPARATION`＝自治体の「水害時待避施設」とGSI `skhb01` 洪水指定緊急避難場所の用途差。これらは**横断結合の自動承認ではない**。

人間レビュアーは該当行の `disposition` を `PENDING`（未確認）／`DOCUMENTED`（根拠を確認して記述済み、承認ではない）／`NEEDS_FOLLOWUP`（追調査が必要）のいずれかにする。後二者は `reviewer`、`reviewed_at_utc`、`finding`、少なくとも1つの一次資料 `evidence_urls` を必須とする。`limitations` は必要に応じて記入する。判断ができない場合は `PENDING` または `NEEDS_FOLLOWUP` のままにする。

**不可変の監査対象**：正式JSON・レシートのSHA256、原本のsource_key順とURL／過去・現在SHA256、Gitコミット、Actions run ID、承認0件、災害区分追加0件。これらをレビュー欄から書き換えると不整合エラーになる。HTTPS根拠URLは入力形式だけ検査し、URLの出典真正性・本文・レビュアーの実在性をソフトウェアが検証するわけではない。

## 安全境界と次段階

- このCツールが返す結論は、どのような記入内容でも `HOLD_PENDING_EXTERNAL_HUMAN_SIGNOFF`。**10件すべて `DOCUMENTED` でもDに投入可能とは判定しない。** 原本・証拠と人間による承認・同一敷地の決定・防災指定は別工程。
- 記入された `reviewer` は**自己申告の文字列**であり、デジタル署名や人間の本人確認ではない。承認する場合は、プロジェクトの認可されたレビュー担当者がGitHub PR Review・外部署名記録等で本人確認可能な方法を用い、判断対象・根拠・有効範囲とともに別途承認する必要がある。AIがレビュアーを代替して署名したり、署名を捏造したりしない。
- D #266 は、A #264 と C #265 の必要な人間による個別承認、対象とする原本スナップショットの確定、ソース意味の互換性確認が終わるまで実データ再生成を行わない。
- 旧／新下小岩小学校、2026年水害計画、GSI原本は別々の版／用途として保持する。`UNKNOWN`／`UNVERIFIED`、null／0、洪水と水害を混同しない。地理院と区のデータを名称や近さだけで自動joinしない。
- 検証の失敗は **integrity FAILURE**、文書構造が正しいだけなら **HOLD**。成功を人間の承認と読み替えない。

**ローカルテスト：** `python3 -m unittest discover -s validation/validation -p 'test_check_edogawa_review_packet.py' -v`。fixtureは架空データ、11テストで非承認保持と改ざん検出を検証する。GitHub PRのrequired CIは別途確認すること。