# C → B/E 参考契約：旧下鎌田小学校の3状態 Evidence Case（安全判定とは別）

2026-10-13 | **Cデモ出力・未承認** | Issue #141 / PR #136

## 目的と非目的

2026年の江戸川区水害待避施設一覧、旧下鎌田小学校の校舎・体育館解体契約、議会可決の**出典と時点が異なる資料**を、ユーザーに誤解を与えず見せるためのC-owned閲覧用JSONを用意する。

これは HINANEX が将来目指す「過去の災害再現／成功・失敗ケースの精度検証」では**ない**。実際の洪水発生、浸水シミュレーション、避難ルート、予測精度を測定していない。**現実の避難先の推薦や防災上の安全判定に転用禁止**。

- C generator: `validation/validation/build_shimokamata_evidence_demo.py`。
- C synthetic tests: `validation/validation/test_shimokamata_evidence_demo.py`。
- 上流の非公開行政照会原本の検証: `verify_edogawa_official_reply_intake.py` → `build_shimokamata_review_readiness.py` → 本generator。正規の行政回答は現在未取得。
- 出力する原本ダイジェストは**すでに独立A/Cで確認した公共の行政資料4件だけ**。回答メール・電話メモの原文やダイジェスト、送信者名、原本ファイル名、照会状態を引き継がない。
- 先行するGitHub-hosted公式raw検証: 2026水害計画・後利用文書 `38339232496`、旧校舎解体契約議案 `38340110892`、議決結果HTML `38340990844`。**このデモ生成のたびに実原本を再取得・再照合したわけではない**。
- `D/RegionExport` をimportも更新もしない。現時点の旧校舎の利用可否を判定しない。

## 3段階の発表用証拠ビュー

| key / label | 時点付き根拠 | 示せる内容 | 絶対に示さない内容 |
| --- | --- | --- | --- |
| `DOCUMENTARY_FACT` 「公式資料で確認できること」 | 2025年後利用方針、2026-04-01地域防災計画、2026-06議案PDF、2026-07議決結果HTML | 資料に記された旧新別施設掲載、旧校舎解体契約の議決 | 現在の施設稼働、開設、避難安全性 |
| `SOURCE_VERSION_RECONCILIATION` 「資料間で追加確認が必要なこと」 | 防災計画の時点とその後の工事契約 | 旧新校舎と時点をまたぐ資料の確認が必要、住所表記差が未解決 | 出典同士の法的矛盾が確定したと主張 |
| `CURRENT_OPERATIONS_UNKNOWN` 「現在の状態は未確認」 | 旧体育館の現存・工事制限・外水内水の指定変更日・当日開設の未取得 | `UNKNOWN` を根拠付きで説明 | 「危険/安全」「使用可能/不可」「開いている/閉まっている」 |

2026年防災計画原文の新下鎌田小の住所 `瑞江4-19-1` と学校台帳 `瑞江4丁目19番10号` は修正しない。旧下鎌田小の `東瑞江3丁目11番1号` と**別の敷地**を示す文字列として、C人間による同一施設承認はまだゼロ。

## B/Eへの受渡仕様（消費側は別PR）

`consumer_contract`: `C_PUBLIC_EDUCATIONAL_CASE_STUDY_V1`

- `status` は必ず `PUBLIC_EDUCATIONAL_EVIDENCE_NOT_SHELTER_GUIDANCE`。
- `presentation_only=true`、`may_be_used_as_live_shelter_recommendation=false` を両方必須とする。
- `demo_states` は3件、固定順。`source_documents` は4件、公式URL・原本SHA256・文書対象日・原文証拠の要約を含む。`original_bytes_reverified_by_this_public_export=false`。
- Bにおける推奨表示: 「参考事例／資料の時点差」「防災計画の掲載」「最新の利用状況は未確認」という読み物として表示。利用者の近隣施設一覧、避難ルート地図、選択ボタン、利用可能ピン、リアルタイム開設UIへの直接連結は禁止。
- Eは位置や経路を補完しない。Cの表示JSONには**緯度・経度・安全距離・ハザードの推定ランクが含まれない**。
- Cのデモは公表資料の有効性・現存状況・当日開設を自動判断しない。正式な自治体の情報とC/Dによる人間審査を経ない限り、RegionExportへの昇格は許可しない。
- 個別表示のタイムラインの出来事は文書記載の**対象日とイベント日**であり、「現在」状態の鮮度保証ではない。

## 実行

人間による連絡をまだしていない場合、ユーザーはGit管理下の初期照会票をそのまま使用する。空の既存ディレクトリ `/private/official-replies` を準備し、Git管理外の出力先を指定する。

```bash
python validation/validation/build_shimokamata_evidence_demo.py \
  --packet validation/reviews/2026-10-13-old-shimokamata-inquiry-packet.json \
  --original-dir /private/official-replies \
  --out /private/shimokamata-demo-EVIDENCE-ONLY.json

python -m unittest discover -s validation/validation \
  -p "test_shimokamata_evidence_demo.py" -v
```

JSONの本文は公開用固定文言・公式公共資料のSHAとURLからのみ構築。個人を特定できる行政回答や署名を公開Issueに転記しない。元資料のライセンス・転載可否は別途確認が必要。

**独立C人間による同一敷地承認0件、新規洪水判定0件、前回のD原本監査では152件UNKNOWN。今回のC表示変換処理はDを読まず、最新152件の状態の再検証は実施しない。**
