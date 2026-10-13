# HINANEX — C / Validation

C担当は公式SourceとDのRegionExportの対応を検証します。出力結果を根拠に公式値の意味を推測しないでください。

## 洪水Scenario（2026-10-08）

- Review: [reviews/2026-10-08-flood-scenario-acceptance.md](reviews/2026-10-08-flood-scenario-acceptance.md)
- C独立raw監査: [validation/verify_flood_scenario_acceptance.py](validation/verify_flood_scenario_acceptance.py)
- 対象D: PR #41 / `role/d-pipeline`
- Current C verdict: **CONDITIONAL / NEEDS_REVIEW**, main統合は未承認

D側の `pipeline/` で `python run_all_workflows.py` を実行してから、リポジトリrootで次を実行します。

```powershell
cd C:\HINANEX
.\pipeline\.venv\Scripts\python.exe validation\validation\verify_flood_scenario_acceptance.py
```

今回の名古屋Excel正規化の回帰テスト（サンプルWorkbookを使用・ネットワーク接続なし）は次を実行します。

```powershell
cd C:\HINANEX
.\pipeline\.venv\Scripts\python.exe -m unittest discover -s validation/validation -p "test_*.py" -v
```

GitHubの必須CI `test` は、現在 `validation/validation/test_*.py` の回帰テストを実行します（`.github/workflows/test.yml` の `C independent raw-source regression tests`）。ただし、ユーザー環境の公式raw原本を使う独立照合スクリプトはCIでは実行されません。**合成テストの成功と公式原本の受入を区別**し、後者は入力バイトのSHA256・取得日・担当者の検証記録を別途残してください。

このチェックはDの評価関数やModelをimportせず、生成済みRegionExport、Niigata公式raw CSV、Nagoya公式raw Excel bundleを突き合わせます。**単体テストのgreenやCスクリプト成功だけで公式記号の意味まで検証済みとはしません。** 元データの配布状況が変化した場合、固定件数を無理に通すのではなく、SourceとCレビューを更新します。

## D #44後の3地域の再受入れ

`role/d-pipeline` にマージ済みのD #44で `pipeline/run_all_workflows.py` を実行し、`verify_d_mvp.py`、`verify_a_handoff_integration.py`、`verify_flood_scenario.py` をPASSさせます。その後 `feature/c-flood-scenario-acceptance` に戻ってCの独立検証を実行してください（出力とrawがGit管理外で同じ作業フォルダーに残っている前提）。

```powershell
cd C:\HINANEX
.\pipeline\.venv\Scripts\python.exe -m unittest discover -s validation/validation -p "test_*.py" -v
.\pipeline\.venv\Scripts\python.exe .\validation\validation\verify_flood_scenario_acceptance.py
```

新潟のC側追加ゲート: 公式raw `2階以上` / `3階以上` / `全階可` と`fact.usable_floor_raw`が一致し、該当施設は`UNKNOWN`を維持すること。数値は最新Sourceから集計し、2026-10-08の256件を固定アサーションにしません。`○/×/－`等のODS固有の公式意味と実際の避難安全性は引き続き別ゲートです。

## 2026-10-13 江戸川区の施設同一性と資料の更新履歴

[独立監査の報告](reviews/2026-10-10-edogawa-water-join-snapshot-audit.md) および Draft [PR #136](https://github.com/1kz-ma1/HINANEX/pull/136) を参照。水害待避施設HTML・位置CSV・歴史的D RegionExport・Aの未承認候補台帳を突き合わせ、施設ID/座標/元URL/原文階数の一致を検査する。旧・現下小岩小学校では、2023年選挙資料と2025年学校移転・水害資料で、同じ名前が異なる住所を指している履歴を区別する。**同じ学校URLが複数の位置施設レコードにあっても施設同一性の確定キーに使わない。** 

専用合成テスト：`python -m unittest discover -s validation/validation -p "test_edogawa*py" -v`。実データに対するC最終承認・洪水単独の適合判定は引き続き別ゲート。前提A PR #133、D #135とIssue #134/#137を確認する。


### 公式HTML/CSV原本の取得とSHA256（C作業環境で別途実行）
`python validation/validation/archive_edogawa_official_sources.py --out-dir "C:\HINANEX-evidence\official-20261013"` で、江戸川区の公式水害・位置・学校・移転資料と学校運営者の2ページをHTTPSで保存し、HTTPメタデータと生バイトのSHA256を記録できる。**取得日時とページの更新日・情報対象日を区別する**。2023年選挙資料を2025年の学校現所在地の根拠へ転用しない。

このコマンドはCIでは**合成テストのみ**を行い、実際のネットワーク取得は実行しない。収集したファイルはGitに追加せず、独立したC担当者がソース版、施設IDと物理施設の対応、水害待避施設／洪水単独の意味を審査する。収集完了だけでは避難適合性はUNKNOWNのまま。


### 公式原本アーカイブの保存後検証（2026-10-13 C追加）

収集したデータはGit管理外で保持し、保存直後・Aへの受け渡し前・Cレビュー直前に、**同じディレクトリ内の実バイトとManifestを突き合わせ**ます。

~~~powershell
python validation/validation/archive_edogawa_official_sources.py --out-dir "C:\HINANEX-evidence\official-20261013"
python validation/validation/archive_edogawa_official_sources.py --verify-dir "C:\HINANEX-evidence\official-20261013"
python -m unittest discover -s validation/validation -p "test_edogawa*.py" -v
~~~

「--verify-dir」はネットワーク不要で、7件の取得元URL・最終URLの発行元ホスト・全ファイル名・生バイト長・SHA256・必須フラグ・UTC取得時刻・余計なファイルの混入をfail-closedで検査します。結果が ARCHIVE_BYTES_CONSISTENT_REVIEW_REQUIRED なら**保存済みデータとそのManifestが整合**しただけです。原本発行元の真正性、Manifest自体の第三者改ざん、原本の現行性、施設の同一性、洪水適合性は証明できません。

**独立性の限界:** RawとManifestを一緒に差し替えられると内部SHA256は一致し得ます。CはGit管理外の信頼できる別経路にManifest/SHA256を控え、公式本文の取得日と情報対象時期（旧下小岩の2023年選挙情報など）を独立に確認してください。人間のCレビュー承認false、承認ペア0、洪水分類追加0は変更しません。実ネットワークの収集は通常のオフラインCIに含めません。


### 江戸川区の学校2件：Cのレビュー用資料生成（2026-10-13）

原本取得と保存後のSHA256検証が成功し、同じ市公式HTML・位置CSVを使ったC独立監査が完了した場合のみ、葛西工科高校・関東第一高校について人間の照合確認用JSONを生成できます。

~~~powershell
python validation/validation/archive_edogawa_official_sources.py --verify-dir "C:\HINANEX-evidence\official-20261013"
python validation/validation/verify_edogawa_water_join.py --water-html "C:\HINANEX-evidence\official-20261013\water_facilities.html" --location-csv "C:\HINANEX-evidence\official-20261013\municipal_locations.csv" --region-export "C:\HINANEX-evidence\edogawa-current.json" --a-ledger "C:\HINANEX-evidence\edogawa-current-a-ledger.json" --report "C:\HINANEX-evidence\c_audit_current.json"
python validation/validation/build_edogawa_identity_review_packet.py --archive-dir "C:\HINANEX-evidence\official-20261013" --c-audit "C:\HINANEX-evidence\c_audit_current.json" --output "C:\HINANEX-evidence\c_priority_review_packet.json"
~~~

- **Important**: 上記のD出力・A台帳は、採取した公式位置CSV・HTMLと同一版を使って再生成すること。2026-09-27の歴史的 edogawa.json や旧A台帳を現在のデータと混在させない。元の正式コマンドは各担当仕様を優先してください。
- build_edogawa_identity_review_packet.py は先に7件すべてのRaw+Manifestを再検証。C監査JSONに含まれる市の水害施設HTMLと位置CSVのSHA256が、公式アーカイブと一致しない場合は **fail-closed** にし、新しい版でD/A/Cの再監査を要求します。
- 出力は市の学校一覧と学校運営者ページの**住所・電話番号文字列の存在有無**、取得バイトSHA256、公式水害一覧・Dレコードの引用元ID、Cの確認事項を併記します。文字列が存在しても同一施設の承認にはなりません。欠落しても避難施設ではないという判定にはなりません。
- 旧下小岩・現下小岩の異なる物理施設、共有される学校Web URL、旧校舎の大規模水害時の非使用条件を別枠で保持します。資料の更新日・情報の対象時点も人間が独立に確認してください。
- 出力ファイルはGit外に作成。C本人の署名・正式な施設ペア承認は**未実施**、洪水単独適合判定は**UNKNOWN**。2校のレビュー用資料生成と自治体の洪水適合指定は完全に別工程です。


### 再取得した公式原本の差分検証（C / 2026-10-13）

7件の公式アーカイブを実際に取得できた後、ユーザーが過去に保存した **水害施設HTML / 2025年12月11日施設位置CSV** と、新しい原本の差分を独立に検査できます。

~~~powershell
python validation/validation/compare_edogawa_official_revisions.py --baseline-water-html "C:\HINANEX-evidence\old_water_saved.html" --baseline-location-csv "C:\HINANEX-evidence\20251211_hinanhokan.csv" --current-archive "C:\HINANEX-evidence\official-20261013" --report "C:\HINANEX-evidence\official_revision_diff.json"
~~~

- 7件の最新Raw/Manifestを先に再ハッシュ検証し、水害施設一覧の全フィールド（名称・住所・電話・原文使用階数等）と位置CSVの原文6列をそれぞれ比較します。順序では施設同一性を決めません。
- 結果は3種類：BASELINE_AND_CURRENT_BYTES_EQUAL_STILL_REVIEW_REQUIRED（2原本バイト一致）、SOURCE_BYTES_DIFFER_STRUCTURE_SAME_REVIEW_REQUIRED（バイト差はあるが構造化行は同じ）、STRUCTURED_SOURCE_DRIFT_REVIEW_REQUIRED（構造化行が変更）。いずれも要レビューであり正式承認ではありません。
- 追加・削除されたRawの行を記録し、学校2件と旧・現下小岩を優先監査対象として別表示。**原文階数・住所の差分をAIの推測や名称照合で吸収しません。**
- HTMLの改行や空白だけの差異は、SHA256では変化として記録しながら、構造化内容の比較時だけ空白正規化して区別します。
- 新しい原本と古いD/A/C成果物を混在させない。新旧版に実質差分がある場合は、最新版に合わせA・D生成とC監査をやり直してからレビュー資料を生成します。
- 履歴基準HTMLの真正性・取得日、最新原本の適用時期、公式の洪水適合指定、施設の開設・安全性は差分比較だけでは証明できません。**承認ペアと新規洪水適合判定はゼロのまま**です。


### HTTP 200の誤コンテンツを拒否するC原本検査（2026-10-13）

公式7件のHTTPS取得後、SHA256整合だけでなく「URLは200を返したが中身はエラーページ」という事故を除外するため、次の **C Content Preflight** を必ず実施します。

~~~powershell
python validation/validation/archive_edogawa_official_sources.py --verify-dir "C:\HINANEX-evidence\official-20261013"
python validation/validation/validate_edogawa_official_archive.py --archive-dir "C:\HINANEX-evidence\official-20261013" --report "C:\HINANEX-evidence\c_content_preflight.json"
~~~

- 元位置CSVがCP932で読めること、オリジナルの6列見出しと各行・数値座標が正常なことを確認。HTTP 200でもHTMLがCSVのふりをしていた場合、Content-Typeや列構造で拒否します。
- 水害施設一覧の正式表見出し・原文の施設データ・#108/#109の施設行・旧/現下小岩の別の所在地があることを確認。学校一覧・移転発表・学校運営者のページには各対象施設名などの基本文脈があることを確認します。
- 固定の152件/111件の件数で合否を決めません。更新で実データ件数が増減することを許容し、変更は別の原本差分監査で人間に提示します。ただし構造や必要施設行が変わった場合は、それ自体を人間の再調査対象としてfail-closedにします。
- 出力状態 ORIGINAL_CONTENT_STRUCTURE_CHECKED_HUMAN_REVIEW_REQUIRED は「中身が期待する形式と最低限の文脈だった」ことのみ。取得先の真正性、公式更新日・適用時期、別ソースのD施設IDとの同一性、洪水適合性は**証明しません**。承認ペアは0のまま。
- 実サーバーへの外部通信はオフラインCIには組み込まず、合成テストでHTTP 200の誤コンテンツ・CSV偽装・ソース表欠落・旧新校舎混同を検出します。
