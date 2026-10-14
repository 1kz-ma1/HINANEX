# A — 2019年台風19号・気象庁原本候補の取得と時点境界

**状態: A tooling only / ORIGINAL BYTES NOT YET CAPTURED / 未承認。**

関連: [全体 Issue #142](https://github.com/1kz-ma1/HINANEX/issues/142)、[A 事前情報候補 #149](https://github.com/1kz-ma1/HINANEX/pull/149)、[C as-of gate #148](https://github.com/1kz-ma1/HINANEX/pull/148)。

## 原本候補 — 正式URL

| 記者会見/報道発表日 | HTML原本 | 添付PDF原本 | PDF本文の時刻の意味 |
|---|---|---|---|
| 2019-10-09 | https://www.jma.go.jp/jma/press/1910/09a/201910091400.html | https://www.jma.go.jp/jma/press/1910/09a/20191009_1400.pdf | PDFの「令和元年10月9日14時00分」は**資料に記された時刻** |
| 2019-10-10 | https://www.jma.go.jp/jma/press/1910/10c/201910101400.html | https://www.jma.go.jp/jma/press/1910/10c/20191010_1400.pdf | PDFの「10月10日14時現在」は**情報の基準時刻** |
| 2019-10-11 | https://www.jma.go.jp/jma/press/1910/11b/201910111100.html | https://www.jma.go.jp/jma/press/1910/11b/20191011_1100.pdf | PDFの「令和元年10月11日11時00分」は**資料に記された時刻** |

Aの公開サイトの初期目視では3組とも公式の2019年報道発表・台風接近の事前見通しを掲載。HTMLから同じ気象庁PDFへの正式リンクをたどれる。ただし、**PDFに表示された時刻をPDF自体の初回公開時刻と同一視しない**。現在配信されるPDF/HTMLの内容が2019年当時の原本と完全同一という証拠（保管当時の別原本・署名・公開史など）もない。

## A原本取得・再照合

コード: `data-research/tools/archive_jma_typhoon19_originals.py`。
候補資料: `data-research/scenarios/2019-typhoon19-contemporaneous-input-candidates.json`。

```bash
python -m unittest discover -s data-research/tests -p "test_archive_jma_typhoon19_originals.py" -v
python data-research/tools/archive_jma_typhoon19_originals.py \
 --ledger data-research/scenarios/2019-typhoon19-contemporaneous-input-candidates.json \
 --out-dir /tmp/jma-2019-UNREVIEWED
python data-research/tools/archive_jma_typhoon19_originals.py \
 --ledger data-research/scenarios/2019-typhoon19-contemporaneous-input-candidates.json \
 --verify-dir /tmp/jma-2019-UNREVIEWED
```

固定6件 (3 HTML + 3 PDF) の HTTPS `www.jma.go.jp`のみ。既定のリダイレクトは拒否、HTTP 200以外は拒否、ファイルサイズ/書式判定、変更不可の候補URL、SHA256と取得日時・HTTPヘッダ（参考）を原本ごとに記録。空でない出力は上書きしない。

**原本をGit commitしない**。sharedワークフローの短期GitHub Actions artifactを用いて、CがAとは独立に元の原本bytesを検証する。HTTP Date/Last-Modifiedは現在の配信に関する参考情報であり2019年時点の立証と扱わない。

## 分離・承認条件

- **T0（現在配信される原本）**: AのSHA照合とCの独立raw監査の後、原本由来の表示内容の整合だけを確認できる。A成功=C承認ではない。
- **as-of input**: 独立した当時の版・公開時刻証拠が得られ、Cが承認して初めて `historical_version_verified` の判定を検討できる。元のA候補JSONの`published_at_jst`と`asof_input_accepted`を推測で更新しない。
- **T1/T2予測**: 同一時点の施設版、区の施設種別・運用、当時の自治体警報等が必要。JMAの広域予報だけで区内の避難所開設数、個別洪水安全性を予測できると主張しない。
- **地図版**: 江戸川区の現在配布「2019年5月発行」ハザードマップPDFは2023年の変更を反映しており、2019 INPUTへ採用しない。

この調査は **A Evidenceだけ**。Cの真値監査やDの判断/RegionExportは更新しない。