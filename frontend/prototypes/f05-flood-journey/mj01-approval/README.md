# MJ-01 限定是正の承認依頼 2026-11-27

DECISION REQUEST / NOT ADOPTED / DO NOT MERGE / PUBLICATION NO-GO

@1kz-ma1 に以下の判断を依頼する。既存 #483 の固定HEAD 03d8f92a1c776664765dc898acdefa94730cc040 は維持する。

- A: 固定HEAD制限を既存7ファイルの3是正（A-P2-01 厳密文字列型、02 安定toggle名、03 復帰focus）、必要な回帰試験と最新mainへの非force同期に限定して解除。
- B: 架空fixture、loopback HTTP、通信許可リスト、一時profile、cleanupを条件に独立PC Chrome検証を許可。実AX、旧操作、実tab復帰、実BFCacheは成立時のみPASS。

根拠: #362 comment7120366611、#483 comment7120927222、独立review6082138791/6082236655、#494/#371/#498統合済み。実ブラウザ・正式パッチ未確認。

回答は A承認/B承認、条件付き承認または保留。許可後はB-Devが是正し、確定HEAD CI・候補bundle・独立QAを提出。ソース統合は別決裁。実施設、正式S0/S1接続、MJ-02、GPS、保存、公開、物理端末、LAN、外部通信は対象外。このPRは承認記録専用でマージせず閉じる。
