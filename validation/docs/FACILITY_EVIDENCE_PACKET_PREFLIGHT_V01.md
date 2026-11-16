# C / 施設・出典・災害意味・利用条件 — 証拠パケット事前点検 v0.1

**2026-11-16 / 実装スコープ: Cだけ / READ-ONLY / 機械的な不足・衝突一覧。人間承認・公開・S1実データ接続は一切認めない。**

## 1. 目的と境界

S1-P0/P1/P2（#391/#394/#397）とC合成E2E（#400）は**架空の `synthetic:` レコードだけ**を検査している。公式施設をそれらへ接続する前に、実資料と施設単位の検証に必要な「何の証拠がないか」を見落とさず列挙するため、**C専用の提出メタデータpreflight**を設ける。

この実装はGit上の特定の自治体データや実Rawを自動読み込みしない。利用者/担当者が**アクセス制御された別領域に用意したJSONの参照情報**（URL・バージョン・SHA・レビュー参照）を読み、構造と相互整合を調べる。サンプルは全て `example.invalid` と架空ID/架空digestの固定合成ケース。ネットワークアクセス、原本バイト取得、本人確認、実データの閲覧、添付されたレビューメモの真正性確認、S1への出力渡し、ソースの自動採用、施設やGPSの推定はしない。

既存の領域/根拠の独立性を維持する：
- A原本・Evidenceの保全/取得、C独立原本SHA・形式照合、施設や敷地の同一性、D側ハザード意味の承認、A利用条件の確認は**別々のレビューと原本**を要する。
- 関連Issueは [#134](https://github.com/1kz-ma1/HINANEX/issues/134)（江戸川の実施設・別ソース同一性）、[#366](https://github.com/1kz-ma1/HINANEX/issues/366)（F02利用許諾・出典表記）、[#48](https://github.com/1kz-ma1/HINANEX/issues/48)（災害区分の意味）、[#305](https://github.com/1kz-ma1/HINANEX/issues/305)（S1の後続）。
- [C既存レビュー学習ループ](REUSABLE_REVIEW_EVIDENCE_LEARNING_LOOP_20261027.md)が示す**「確認可能な属性ごとに承認し、版が変われば再確認」**の原則を変えない。S0→UI設計Draft #386/#387とkoutaのF05 Draft #371は保留/不変更。

## 2. 入力とデータモデル（C内部のみ、共有Schemaではない）

`validation/validation/preflight_facility_evidence_packet.py` に `preflight(packet)` を実装。入力`schema_id=hinanex.c.facility_evidence_packet_preflight.v0.1`、`records` は1件以上。各`case_id`は**opaqueなレビューケースID**（施設名ではない）で重複不可。未知キーやbool・数値の代入は許可しない。

1件の入力グループ:
- ケース`hazard`、`requested_asof`（UTC）、`asof_evidence_ref`: 検証する具体的な災害の種類・対象時点と、資料がその時点に適用できることを人間が調査するための参照。**後年に取得したページの現在表示は過去時点の証明ではない。**
- `source`: `url / publisher / raw_sha256 / c_raw_audit_sha256 / captured_at_utc / source_revision / source_record_locator`。SHAは**文字列の形式と提出された2つの値の一致**だけをチェック。原本ファイルのバイトと照合はしない。
- `identity`: 別資料の`target_source_url / target_raw_sha256 / target_c_raw_audit_sha256 / target_captured_at_utc / target_source_revision / target_record_locator`、元資料への`bound_source_sha256`、`independent_pair_review_ref`、`disposition`。同名・近接・同一学校名・運用グループだけでは施設／棟の一致を認定しない。現時点は**別ソースのペア審査前提**であり同一原本内のID付与については別仕様にする。
- `hazard_meaning`: 原本の`raw_marker`、自治体等の`official_meaning_ref`、`reviewed_hazard`、`bound_source_sha256`、`independent_review_ref`、`disposition`。原本上の記号を独自に洪水対応・安全等へ変換しない。
- `reuse`: `terms_url / attribution_text / exception_check_ref / bound_source_sha256 / independent_review_ref / disposition`。CC等の**一般的なページの表示が、この資料の個別例外・第三者権利まで解消したとは限らない**。
- レビュー`disposition`は `UNREVIEWED` / `CONFLICTING` / `DOCUMENTED_PENDING_AUTHENTICATION` のみ。`VERIFIED` / `APPROVED` / `SAFE` 等は入力スキーマ段階で拒否。後者は「参照欄が揃っているという**提出者の自己申告**」に過ぎない。

全てのフィールドは**必ず存在**し、未知なら`null`として提出する。`UNKNOWN`や`TBD`等の文字列も欠落と評価。正規のURLはHTTPS形式（ホスト名があって認証情報/フラグメントなし）、SHAは英小文字hex64桁、取得/対象時刻はTZ付きUTCのみ。仕様追加時はこのC内部入力versionとテストを変更し、D/B/E共有Contractとは独立させる。

## 3. 検査する事実と、検査しない事実

機械で検出する:
- 原本取得URL、提供者、ハッシュ、C側SHA報告、取得時刻、資料版、レコード行参照の欠落。
- 元Rawと独立C報告SHAの不一致、対象別Rawと独立C報告SHAの不一致。
- 施設ペア・ハザード意味・利用条件レビューに記録された**元資料SHAと今回の原本SHAの不一致**（版更新や参照違いを保留）。
- 原本の明示的な災害範囲と入力ハザードの相違、未レビュー/衝突、意味資料・許諾・表示クレジット・個別例外確認・各独立レビュー参照の欠落。
- 「資料の版/対象時点の根拠なし」を`SOURCE_ASOF_EVIDENCE_MISSING`として明示。

機械では検出できない・承認しない:
- **SHAが実在する公式バイトに対応すること、URLの公式性、独立レビュー提出者の本人認証、レビュー内容の妥当性、指定施設の同一敷地・建物の証明、原本解釈、法的利用許諾、現時点の開設や経路安全**。
- SHAが同じ・参照URLが揃う・全`disposition`が`DOCUMENTED_PENDING_AUTHENTICATION`でも、出力は`PACKET_METADATA_PRESENT__HUMAN_AUTHENTICATION_REQUIRED`。原本・施設/災害条件は**S1未受入**のまま。完全な提出パケットを読めるようにしただけで、レビュー済の認定でも公開許可でもない。

レポートは`case_id`と理由コードだけを出し、URL/Raw/レビュー本文・人物名はコピーしない。各領域`reason_codes_by_area`に明示し、必要資料を絞り込む。未確認資料を「自治体が持たない/公開していない」と表現しない。

## 4. 判定と終了コード

- 入力スキーマ不正・余計な公的安全承認フラグ・ID重複は`PacketInputError` / CLI **exit 2**。
- 必要な記録が1つでも欠損・衝突・不整合なら`HOLD__NO_REAL_DATA_ADOPTION` / CLI **exit 2**（診断結果は表示）。
- 形式上、必要な参照欄が埋まれば`PACKET_METADATA_PRESENT__HUMAN_AUTHENTICATION_REQUIRED` / CLI **exit 0**。**exit 0も「原本照合/安全/公式受入/ライセンス承認のPASS」ではない。** 外部の独立C/A/D原本・権限レビューが必要。

すべてのレポートで`source_original_bytes_verified_by_this_run=false`、`identity_pairs_approved=0`、`official_hazard_semantics_approved=false`、`license_and_publication_approved=false`、`eligible_for_s1_real_facilities=false`、`safe_route_verified=false`、`facility_open_now_verified=false`、`human_independent_review_required=true`に固定する。

## 5. 実行・テスト

rootで、Gitに含まれる**架空例**（完全1件・不完全1件・矛盾1件）:

~~~sh
python validation/validation/preflight_facility_evidence_packet.py \
  --packet validation/fixtures/facility_evidence_packet_synthetic_v01.json --json
~~~

この例は**意図的にexit 2**となる。正常運用では実RawをGitに追加せず、検証入力もGit外の制限領域に置く。CLIは読み取りだけで、ファイル作成・上書き・外部通信はしない。

~~~sh
python -m unittest discover -s validation/validation \
  -p 'test_preflight_facility_evidence_packet.py' -v
~~~

**Device QA: NOT_REQUIRED**（C側の純粋Python/参照メタデータ診断のみ）。実機での施設候補UI・経路・一般公開・実資料承認はNOT_RUN/NO-GO。

## 6. 採用範囲・次の判断

今回の受入条件は、新規Cテスト、既存required `test`、最新mainのC Scope Guard PASSと、**原本なしでも確実にHOLDを返せること**。未確定な公式意味を埋める・施設の自動同一視を行うDの改修はしない。

人間の独立レビュー後の限られた属性だけをDの実施設S1へ渡す、次段階の**真正性確認・属性単位の共有Contract**は、A/C/DとMerge Captainの別仕様/別PRとして決める。今回のローカルpreflightの`exit 0`を利用する自動公開ゲートは**作らない**。
