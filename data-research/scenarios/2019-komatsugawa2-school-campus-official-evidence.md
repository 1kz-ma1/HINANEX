# A: 江戸川区「小松川第二中学校改築の概要」2019年3月更新の証拠

**2026-10-13 / 現行HTMLの取得候補 / 当時原本版の真正性未承認 / 学校校舎 ≠ 台風避難所施設**

公式ページ: https://www.city.edogawa.tokyo.jp/e071/kosodate/kyoiku/kyouiku/shiryo/keikaku/kaichiku/komanichu.html

現行公式ページの表記:
- **「更新日：2019年3月1日」**（現在表示される更新日。ページがその後一切更新されなかったことを証明しない）。
- 改築前は**平井3丁目**で学校運営。
- 平成30年（2018年）**4月から**通常課程は**小松川2丁目**の新校舎で学校運営。
- **「夜間学級は平井3丁目で学校運営しています」**。
- 新校舎の施設概要の所在地は**小松川2丁目10番2号**。これは新校舎の住所であり、夜間学級に適用してはいけない。

### Evidence distinctions

1. **学校運営場所の区別**：当該2019年3月更新表記の自治体公式ページ上では、通常課程（小松川2丁目）と夜間学級（平井3丁目）は異なる地区で授業をしていたと記載。**校舎の説明としての地点区別は明示的**。
2. **当日開設した避難所の具体的な建物IDは未確定**。2020年作成の学校避難所事後報告は、`junior_high:02`の**通常205人／夜間11人**を同じ*運用グループ番号*で記録するだけ。学校校舎配置をそのまま避難者の受入建物に対応させない。
3. 夜間学級の**正確な住居表示（平井3丁目以降）はこの公式ページでは記載されていない**。2022年以降に移転した夜間学級の現行住所を2019年へ流用禁止。
4. `2019年3月1日`は**現行ページの表示上の更新日**。その時点で同じHTML bytesが存在したことの独立証明はまだない。
5. 出典の個別の意味は **SCHOOL_CAMPUS_CONFIGURATION_REFERENCE**。災害時の避難所開設状況、物理IDと人数の対応、浸水安全性、被害予測、収容人数の断定に使用禁止。

### Additional 2017 contemporaneous source

[江戸川区教育委員会 平成29年第20回議事録](https://www.city.edogawa.tokyo.jp/documents/8574/29-20gijiroku.pdf) は、学校改築に伴い新校舎への移転と、夜間学級は当面旧校舎に残す計画を記録（PDF index=4）。**2017年時点の将来計画**であって2019年の避難所運用そのものの確認ではない。正式な原本アーカイブと2019時点での実施状況の独立検証が必要。

### A archive

`data-research/tools/archive_edogawa_2019_campus_overview.py` は正確な上記URLをHTTPS（リダイレクト禁止）で取得、SHA-256/HTTP応答/原本バイト/現在の取得時刻を記録。rawはGit管理外。別shared runnerでGitHub Actions短期private artifactに保管し、別C実装によって原本確認する。

```bash
python -m unittest discover -s data-research/tests -p 'test_archive_edogawa_2019_campus_overview.py' -v
python data-research/tools/archive_edogawa_2019_campus_overview.py --out-dir /tmp/edogawa-2019-campus-UNREVIEWED
python data-research/tools/archive_edogawa_2019_campus_overview.py --verify-dir /tmp/edogawa-2019-campus-UNREVIEWED
```

次: Cで2019年3月の日付・通常校舎所在地・夜間学級の運営場所を*現在の公式原本から*独立に検査。人間レビューまで原本版/当時INPUTは未承認。公式の災害当日避難所施設番号が特定できる資料を別に探す。

関連: [2018年学校広報 A #165](https://github.com/1kz-ma1/HINANEX/pull/165)、[C #166](https://github.com/1kz-ma1/HINANEX/pull/166)、[65/66 post-event #156](https://github.com/1kz-ma1/HINANEX/pull/156)、[Issue #142](https://github.com/1kz-ma1/HINANEX/issues/142)、[施設同一性 #134](https://github.com/1kz-ma1/HINANEX/issues/134)。
