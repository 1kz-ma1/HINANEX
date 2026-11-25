# 国土地理院・土砂災害種別 skhb02 の原本調査（2026-10-26）

- 状態: **A SOURCE FEASIBILITY / 未取得・未承認 / 非公開**
- 公式出典: https://maps.gsi.go.jp/development/ichiran.html
- 公的配信パターン: `https://cyberjapandata.gsi.go.jp/xyz/skhb02/{z}/{x}/{y}.geojson`
- 元属性: `disaster2=1` は、GSIが公開する**崖崩れ・土石流・地滑りに対して指定された緊急避難場所**を示す。これは土砂災害**危険区域図でも、現時点の安全性・開設状況でもない**。
- 地理院の掲載タイルはズーム10。地理院の公表範囲・各自治体の掲載/更新時点・ライセンス・利用注意事項は原本ごとに独立確認が必要。
- この時点で**実際のskhb02原本を取得した実測件数、適用自治体境界、公開日/更新日、利用可否、独立C承認は未取得**。
- 洪水 `skhb01/disaster1` と混ぜない。自治体の D `shelter_location` や新潟ODSと施設名から照合・同一施設認定しない。

## 本PRで実装した安全なオフライン下調べ

`tools/inspect_gsi_skhb02_archive.py` は既に外部の承認済み手順で保存した**原本バイト**を明示的に渡したときだけ、厳密なホスト/タイル/レベル・GeoJSON・座標・`disaster2=1`形式を確認し、SHA256と原文だけを抽出する。

コマンド例（**実原本はGitリポジトリへcommitしない**）:

    python data-research/tools/inspect_gsi_skhb02_archive.py --archive /outside-repo/skhb02-z10.geojson --source-url https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson

ここでの座標とタイルは**コマンドの書式例**であり当該地域の証拠ではない。実作業では原本のURLと一致した座標・ファイルを使用する。

出力はあくまで `A_SKHB02_SOURCE_FEASIBILITY_ONLY`。特定タイルのfeatureが0でも市町村全体に避難場所がないと断定しない。raw→独立C照合→D抽出→地図掲載の工程を短絡しない。原本を検証せず更新されたものに置き換えることも禁止。

## 次の人間・C/地域拡張ゲート

1. 国土地理院の配信利用条件/掲載自治体・更新時点を人間が確認し、正確な実タイルを指定。
2. 同一原本と配信URL、バイトハッシュ、取得時刻、対象災害の意味を A が別途固定保存。Pythonツールが示すのは構造の初期検査のみ。
3. Cはfeature単位で原本と独立照合、タイル外/他自治体への越境・GSI更新差分を検証。
4. D/Eによる reference-only 出力は別PR。**市町村指定緊急避難場所の掲載 = 災害時の安全な避難先**にはならない。
5. [Issue #89](https://github.com/1kz-ma1/HINANEX/issues/89) の地域×災害2×2には、この未受入セルを `UNVERIFIED` のまま記載。

テストはsynthetic GeoJSONのみ：`python -m unittest discover -s data-research/tests -p "test_*.py" -v`。実ネットワーク取得・利用規約の適合審査・原本件数確認・自治体掲載範囲の証明は未実行。
