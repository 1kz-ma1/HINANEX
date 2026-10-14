# 2019年台風19号・江戸川区 — 3ケース説明用データ（C所有）

**閲覧・発表専用**。Cの先行機械監査を元に構成した固定説明資料であり、同じ時点の予測と結果を再計算するHistorical Replayではない。原本の歴史的な同一版承認／当日の建物同一性は未完了。Issue #142。

- `trace`: T0原本→抽出値（65運用グループ／66明細／26,761人）の**機械的整合**。T1/T2予測のMATCHではない。
- `abstain`: 205+11人の報告は存在するが、当日使われた建物は不明。T1は**NOT_EVALUABLE**（予測の正誤を評価できない）。ABSTAINと混同しない。
- `negative`: 意図的に不正な入力を作った**合成負系テスト**（明細削除、校舎住所の当日建物への転用）をCが拒否する。**実災害の予測MISMATCHではない**。

元監査は `validation/validation/generate_20261022_t0_evidence_brief.py` で4つの独立C報告から生成される。ここに記録した原本SHA256/監査runはそのC正本と照合するが、この固定JSONは人手C承認署名でも、現在の原本再取得でもない。

このJSONは説明・参考リンクにのみ使用し、**D RegionExport、shelter eligibility、避難先、危険度、開設状態、GIS施設座標を変更しない**。発表中のボタン操作で認証/検証ステータスを変えない。Bは内容を再分類せず表示し、合成と未検証を必ず目立つように表示する。

検証: `python -m unittest discover -s validation/validation -p 'test_2019_edogawa_demo_cases.py' -v`。このテストに通っても2019年当時版の人手確認が完了したことにはならない。
