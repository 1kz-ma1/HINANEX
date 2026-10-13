# A調査: 国土地理院の指定緊急避難場所データと江戸川区水害時待避施設（2026-10-13）

状態: **公式候補ソースの確認のみ、江戸川区の該当CSV原本は未取得、施設ペアは未承認。**

## 公式資料

1. 国土地理院「指定緊急避難場所・指定避難所データ」 https://www.gsi.go.jp/bousaichiri/hinanbasho.html
   - 指定緊急避難場所は自治体が災害種類ごとに指定した施設・場所であり、「指定避難所」（生活拠点）とは区別される。
   - 同ページは国土地理院・内閣府・消防庁等と連携したデータの公開を案内している。
2. 国土地理院「避難所等データダウンロードサイト」 https://hinanmap.gsi.go.jp/hinanjocp/hinanbasho/koukaidate.html
   - 市町村別の指定緊急避難場所CSV仕様には、全国共通ID・施設/場所名・住所・洪水/高潮/内水氾濫等の災害別指定欄・緯度・経度・備考がある。
   - 指定緊急避難場所の「洪水」は該当時 1、非該当時空欄。データにおける空欄は、その施設が安全でないことの直接証拠とは扱わない。
   - サイトの更新日はGSIデータベースの更新日時。市町村の法的指定・改定日とは別。
3. 国土地理院「免責事項・ご利用上の注意」 https://www.gsi.go.jp/bousaichiri/hinanbasho-menseki.html
   - 市町村が登録・公開同意した情報に限り、未掲載・更新遅延があり得る。最終的な最新指定状況は自治体に確認する必要がある。
4. 江戸川区「水害時の避難はどうする？」 https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/suigaihinan.html
   - 待避施設は、広域避難ができない状況等での緊急待避を説明する文脈。洪水のみの法令上指定緊急避難場所と同義と決めない。

## Existing data is NOT a key or flood status

- 既存の20251211_hinanhokan.csv：元列は名称/URL/災害種別記号/コメント/緯度/経度のみ。住所や全国共通IDは存在しない。災害種別記号はアイコンURLであり指定の意味を推測できない。152施設。
- 2026-10-13保存した江戸川区水害待避施設のHTML原本：番号/名称/住所/電話/使用可能階数、111行。「洪水指定緊急避難場所」の証明書ではない。
- 両者には現在独立に確認された共通施設IDがない。名称類似・住所・緯度経度・学校Web URLはレビューの手掛かりであって、自動joinや洪水適合性の承認ではない。
- 旧下小岩小学校と現下小岩小学校は所在地・施設IDが異なり、共有学校Web URLを施設IDとして使用しない。

## Next evidence gate

- [ ] 公開されているかどうかを含めて **江戸川区単体**のGSI指定緊急避難場所CSVの公式公開状況を確認。サイトは動的なためWeb本文に市区町村個別ダウンロードURLが見えないだけで「未公開」とは断定しない。
- [ ] 該当CSVが実際に公開されていれば、ダウンロードURL、HTTPS最終URL、取得UTC、原本バイト、SHA256、行スキーマ、自治体別最終更新情報を**別の未承認原本**として保存。推測した固定URLを作らない。
- [ ] 施設名称・住所・共通ID・災害別の原文列を保持し、Cが独立監査できる照合候補を作成する。GSIの共通IDが古い江戸川区CSVにも水害HTMLにもないので、**他ソースのD施設IDと同じ識別子ではない**。
- [ ] 多対一・別校舎・移転・名称変更・座標ずれ・異なる出典更新時期を厳格にレビューする。GSI指定の「洪水 1」があっても、同一物理施設をC人間が承認し、かつD/Cが洪水専用の指定を制度上検証するまでは既存ScenarioはUNKNOWN。
- [ ] 区・GSIの行政上の指定時点と、当日の開設/避難経路安全性を別管理する。GSIへの未掲載や洪水列空欄を EXCLUDED に直結しない。
- [ ] データの存在・形式・更新版・実際に江戸川区の何施設が掲載されているかは**未確認**として記録。件数や個別施設一致を作らない。

**当段階の正式な施設ペア承認0件、新規洪水CANDIDATE/EXCLUDED0件。** Aの調査記録であり、D/B/Eの利用条件・UI・Contractには影響させない。


## 2026-10-13 official GSI national emergency evacuation CSV actually acquired

**Supersedes the earlier GSI "not retrieved" statements above.** The GSI nationwide DESIGNATED EMERGENCY EVACUATION PLACES CSV (not designated shelters) is https://hinanmap.gsi.go.jp/hinanjocp/defaultFtpData/csv/mergeFromCity_2.csv . The URL was identified in an open-source client but the actual file was successfully retrieved directly from this GSI HTTPS host and checked against the official published national CSV schema.

GitHub-hosted read-only A evidence run https://github.com/1kz-ma1/HINANEX/actions/runs/38335153343 succeeded. Original national CSV bytes: **17,001,696**, SHA256 **e75b3e94c65dd2d348572ea6f9288fef920bb8ee4b7d1d607d51202f6abed16c**. Received 2026-10-13T02:04:41Z. HTTP Last-Modified Tue 06 Oct 2026 (transport metadata, NOT legal designation date). UNREVIEWED private artifact #11784940180 expires 2026-10-20. Nothing committed to Git.

Independent offline CSV parse confirms **115,872 nationwide entries**, **111 rows whose original municipality field is exactly 東京都江戸川区** and **111/111 source row-level equality** against A-generated extraction. All 111 GSI Edogawa rows have original earthquake field **地震=1** and original **洪水 field blank**. Other hazard columns are blank in these rows. This is a source-specific observation; GSI warns of incomplete/outdated/suppressed public registrations. A blank GSI flood column does NOT establish a site's unsafety, an EXCLUDED classification, or any result for the separate Edogawa emergency water-standby dataset.

Four raw GSI review leads, not cross-source matches:

| National GSI ID (not D ID) | GSI name | GSI address | GSI raw flood / earthquake |
| --- | --- | --- | --- |
| E1312300003201 | 都立葛西工科高校 | 東京都江戸川区一之江7-68-1 | blank / 1 |
| E1312300028201 | 私立関東第一高校 | 東京都江戸川区松島2-10-11 | blank / 1 |
| E1312300088202 | 下小岩小 | 東京都江戸川区南小岩5-5-1 | blank / 1 |
| E1312300089201 | 旧下小岩小 | 東京都江戸川区南小岩7-8-1 | blank / 1 |

Two Shimo-Koiwa physical locations receive different GSI IDs. Neither GSI ID nor name/location similarity automatically maps to the D municipality ID or a flood decision. A-only retrieval code data-research/tools/retrieve_gsi_edogawa_official.py and synthetic negative tests data-research/tests/test_retrieve_gsi_edogawa_official.py accompany this report; all outputs keep human approval 0 and flood changes 0. Independent human C coordinates-to-campus verification, D/C legal flood-only scope, opening and staging acceptance remain unresolved. No main or Render mutation.
