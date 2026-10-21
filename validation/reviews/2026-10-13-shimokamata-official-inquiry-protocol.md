# 旧下鎌田小学校：区への照会と回答原本のC受入手順（2026-10-13）

状態：**未架電・未送信／正式C承認0件／D洪水判定0件**。

## 公式窓口（区の部署案内で確認済み）

- 防災危機管理課 計画係：**03-5662-1992**。出典 https://www.city.edogawa.tokyo.jp/e007/kuseijoho/gaiyo/soshiki/kikikanri/bousaikikikanri.html
- 財産活用課 調整係：**03-5662-9017**。出典 https://www.city.edogawa.tokyo.jp/e085/kuseijoho/zaisei/zaisankatsuyo/advertisement.html

照会すべき内容は以下を分離する。

1. 防災担当：2026-10-13時点の旧下鎌田小（東瑞江3-11-1）について、外水／内水の待避施設指定継続・休止・取消、適用日、対象棟・利用階、工事中の制限、根拠となる最新施設台帳を確認。
2. 財産活用担当：2026-07-01議案第64号可決後の正式契約・実着工日、旧校舎と体育館の現存・解体状況、立入制限の時期と範囲、行政文書の所在を確認。
3. C独立レビュー：2026-04-01防災計画の旧・新敷地は別施設。2026年版「瑞江4-19-1」と学校台帳「瑞江4-19-10」の原文不一致は未訂正のまま保留。

## 未承認の照会・原本保存フォーマット

- 入力JSON：`validation/reviews/2026-10-13-old-shimokamata-inquiry-packet.json`。初期値は両部署とも `NOT_CONTACTED`、送信日時・回答原本とも `null`。
- 人間が送信した後だけ `CONTACTED_AWAITING_REPLY` と実際のUTC送信日時を記録。
- 回答の受領後は `REPLY_ARCHIVED_UNREVIEWED` とし、回答原文のファイル名、実バイトSHA256、受領UTC、返信手段、名乗った所属を記録。メール・文書・電話メモの原本はGit外の権限制限ディレクトリにのみ保存。
- 電話メモは自治体署名済み文書ではない。問い合わせ先を名乗っただけでは正式な本人確認でもない。
- Cコード `validation/validation/verify_edogawa_official_reply_intake.py` は、元資料4件のSHA256固定、窓口ID、日時整合、回答原本バイト、パス移動・偽承認・誤った学校所在地の拒否を確認する。
- C受入テスト：`python -m unittest discover -s validation/validation -p 'test_edogawa_official_reply_intake.py' -v`。
- 入力検証が成功しても、結果は**回答原本取得済み・人間の施設同一性審査待ち**。D/RegionExportの `UNKNOWN` を自動変更しない。

2026-07-01議決可決と2027-03-12契約上の工期終期は、2026-10-13現在の解体済み・利用可否・開設中の証明ではない。独立の最新公式回答が得られない限り `UNKNOWN` を維持。

**他役割のコード・main・Renderの更新はなし。**
