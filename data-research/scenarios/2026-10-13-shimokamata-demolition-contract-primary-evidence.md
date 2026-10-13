# A: 旧下鎌田小学校 2026年解体契約の公式証拠 — 災害使用可否は未承認
2026-10-13 / A source investigation / **EVIDENCE ONLY**

## 新たな公式原本と法的処理段階

**江戸川区議会議案第64号・旧下鎌田小学校校舎等解体工事請負契約** の区議会公式PDF原本:
https://www.gikai.city.edogawa.tokyo.jp/voices/GikaiDoc/attach/Gk/Gk2792_gian64.pdf

- 議案提出: **令和8年6月12日**（2026-06-12）、PDF物理ページ1–3。
- 工事場所: **江戸川区東瑞江三丁目11番1号**＝旧下鎌田小学校敷地。2026年度防災計画の「旧下鎌田小」の所在地と同じ表記対象。
- 目的・対象: 校舎棟、屋内運動場棟、プール棟、付属棟、工作物、外構、関連設備等の解体。工事概要では地上3階・5,342平方メートルを示す。
- 契約相手: **株式会社フジムラ**。契約金額: **2億5,850万円**。
- 工期（契約議案内の計画値）: **契約の翌日から2027年3月12日まで**。これを「工事完了日」や「現在の校舎が撤去済み」と断定しない。
- 公式区議会議決結果の別ソース: https://www.gikai.city.edogawa.tokyo.jp/g07_giketsu.asp?BUNRUI=&EXP=AND&KAIGI=2026%2F06%2F12%2C2026%2F07%2F01%2C152&KEKKA=&KENSU=100&KWORD1=&KWORD2=&NENFROM=&NENTO=&SMODE=2&Sflg=2
  同一覧は議案第64号について **令和8年7月1日・可決（全会一致）** と記録。議案PDFのみから議決結果を自動推定しない。今回のA原本アーカイブには**議案PDFのみ**が含まれ、別の公式議決結果HTMLはWebで別途検証済みだがバイト保存されていない。将来の正式Cレビューでは議決結果HTMLも独立してピン留めする。

## A原本取得とC独立監査（実行済み）

- 読み取り専用GitHub-hosted workflow: https://github.com/1kz-ma1/HINANEX/actions/runs/38340110892 。
- Aコード: data-research/tools/archive_edogawa_demolition_contract.py。公式PDF URLのみ許可、レスポンス最終URL・UTC・HTTP metadata・生バイトSHA256を記録し、生PDFはGit外の独立アーカイブに保存。元資料を上書きしない。A negative tests: data-research/tests/test_archive_edogawa_demolition_contract.py。
- Cコード: validation/validation/verify_edogawa_demolition_contract.py。正規の議案PDF原本3ページを独立して読み、建物・金額・工期等を検証。C negative tests: validation/validation/test_edogawa_demolition_contract.py。
- GitHub private UNAPPROVED artifact **#11785618185**, 7日保持、2026-10-20失効。公式議案PDF **89,847 bytes, SHA256 aa9051ef17e94da904e7e11fa228239d59a37e3eb256b0bc44f68991e19adc71**。ZIP **SHA256 637ef5d123b53732d239e3822bd10090a5f6bb444121fde93756bfc687c0a9ad**。ダウンロードしたZIPで生PDF→A Manifest→C独立監査のSHA256一致を確認した。
- PDF原本、Manifest、C audit JSONはGitにcommitせず、CI別の私有7日アーティファクトとしてのみ保管。

## 2025後利用方針 → 2026-04水害一覧 → 2026-07議決

1. **2025年4月** 区の旧下鎌田後利用方針変更: 以前の「体育館を緊急避難所として残す」予定から、校舎や体育館など全建物を将来解体する方針へ変更。工期は当時調整中（公式PDF SHA256 a4fee786088052e1bb787f0db0473245d01cc1cae9784c80ef40b3174ed089bf）。
2. **2026年4月1日時点** 江戸川区地域防災計画（公式PDF SHA256 92e85981c16542e3e28bd80bafc56c8a71f3ded9a8b5e67bcb53919d16e1ebcb）：外水氾濫／内水氾濫の両表に「旧下鎌田小・東瑞江3-11-1」と「下鎌田小・瑞江4-19-1」が**別施設**として掲載。これは2026年4月1日時点の掲載情報であり、同日または将来の施設開設を保証しない。
3. **2026年7月1日** 議案第64号・旧下鎌田小学校校舎等解体工事請負契約を議会可決、工期は契約翌日～2027-03-12と議案に記載。解体工事の実際の着工日、棟ごとの施工時期、2026-10-13現在の建物現存・一時利用可否・安全性について追加の公式資料は**未確認**。

いずれのソースも相互に時間的矛盾ではない：2026年4月の指定一覧と2026年7月議決は異なる時点の事実。**どの時点で水害待避施設としての適用が変更されたか**は区の所管への確認が必要。旧・新施設の座標は同名学校の自動joinで処理しない。

## 次のA/C調査候補（未承認）

- 工事の正式な契約確定日、着工日、立入制限日、体育館の解体時期及び完了・現存確認。
- 防災危機管理課が運用する当該旧校舎の水害待避施設指定・外水／内水の条件変更日と根拠資料。
- 財産活用／施設担当部署が記録する旧体育館の現在の使途と解体状況。
- 区の2026 PDFにある新下鎌田小の「瑞江4-19-1」と、現行学校所在地「瑞江4-19-10」の原文不一致の確認。
- 情報更新日と今日の開設状況は別管理し、回答を得るまで「現在利用可能」とも「利用不可」とも判断しない。

**No new D records / changes. No human C physical site signoff. 0 flood CANDIDATE/EXCLUDED, D 152 UNKNOWN, main/Render unchanged.**
