# 市川市4施設 OSM原本取得 GitHub Actions（2026-10-27）

**手動ワークフロー・未承認。データ取得を自動起動しない。** 依存先は [A Draft #326](https://github.com/1kz-ma1/HINANEX/pull/326)（取得ロジック）。先に#326のレビュー/統合が必要。GitHub Actionsは `main` にこのワークフローが入ってから手動選択できる。

## 設計とデータ境界

- GSI skhb02取込済み原本は [run #40258746945](https://github.com/1kz-ma1/HINANEX/actions/runs/40258746945) のアーティファクトを `actions/download-artifact@v4` で復元する。**GSI公式サイトへ再ダウンロードしない**。GSI原本のSHA-256はA #326のコード内の固定値と照合。
- 以前のGSIソースアーティファクトの有効期限は**2026-10-29 11時頃 JST**。期限切れやアクセス不能の場合はBLOCK。自動再取得・勝手な代替データ利用はしない。期限が切れたときは、アーカイブ保全と公式データ利用について別途人間の判断が必要。
- 利用者が先に [OSMライセンス](https://www.openstreetmap.org/copyright/ja) と [GSIの注意事項](https://www.gsi.go.jp/bousaichiri/hinanbasho-menseki.html) を確認し、2つのboolean入力をtrueにした場合のみ開始する。OSMデータはODbL 1.0、© OpenStreetMap contributorsの帰属表示が必要。
- A #326のコードで、単一の限定[Overpass API](https://overpass-api.de/api/interpreter)クエリ（4地点、各半径300m、候補ノード/way/relation）を1回送信。429/504は自動再試行しない。エラーを「入口ゼロ」「避難先ゼロ」に変更しない。
- アーティファクトにGSI・OSMの**原本**、OverpassQL原文、SHA-256、取得時刻・HTTP観測、ライセンス、全安全承認falseの状態を保存（3日間）。
- 出力は *周辺候補地物* であり、施設名や共通IDとの公式同一性・敷地・入口の位置・災害時の利用可否を検証したものではない。**避難先案内/GISへ自動接続しない**。
- GSI referencePointを入口として使わず、OSM entranceタグや建物・公園の座標を `navigation_endpoint` に自動的に入れない。河川敷 #571の所在地範囲差もHOLD。

## 取得成功後の独立監査（#329に依存）

`#329` で統合されたA領域の `inspect_osm_four_site_evidence.py` を、OSM取得の直後・いずれのartifactアップロードよりも前にオフライン実行する。**実取得自体は従来どおり手動のみ**であり、この変更により自動取得や定期実行は追加しない。

- GSI・OSM・クエリ原本とmanifest・利用注意の**5ファイルだけ**をA独立監査器で検証。SHA、固定GSI原本、4施設の参照点、300m×4の固定クエリ、HTTP証跡、OSMの一意な地物ID、すべてfalseの承認状態を独立に確認する。
- 監査JSONを原本フォルダの**外**に出力する。元の5ファイルだけを再監査できる原本artifact `OSM-Ichikawa-4-sites-UNREVIEWED` の構成を変更しない。
- 新たに `OSM-Ichikawa-4-sites-UNREVIEWED-AUDIT` artifact（保存期間3日間）を分離して保存する。監査器や承認状態の検証が失敗したら、両artifactのアップロード前に停止する。
- OSM地物は4施設のどれにも自動割当せず、`associated_gsi_feature_index=null`、`navigation_endpoint=null`、`navigation_allowed=false` のまま保持。**監査のPASSは施設同一性・入場可能性・災害時安全性の承認ではない。**
- 新しい独立監査のCI検証は静的ワークフローガードと合成データのA単体テストであり、実OSM取得・取得後監査の成功実績とは区別する。

## 手動実行
#326 をmain統合し、本Shared PRをmain統合した後、**`main` を選択した状態でのみ** GitHub Actions → `Ichikawa four-site OSM candidate capture (UNREVIEWED)` → Run workflow → 両方の利用注意確認チェック。main以外のブランチからのworkflow_dispatchはネットワーク取得前に拒否する。

ワークフロー側でも、元の取得コードから独立して保存済みGSI原本の固定SHA-256 `cef1058d29dba55c6f4f9257f94ffd51bb2215051078c23c881ebbb1c4343f84` と対象feature index `[571, 639, 682, 707]` を照合する。失敗時は原本アーティファクトを公開しない。

**未実行:** 本PR CIはworkflow構文/静的安全ガード検証のみ。実Overpassへのアクセスや候補地物の取得・施設ごとの割当・C人的承認は、手動実行して初めて別途確認できる。
