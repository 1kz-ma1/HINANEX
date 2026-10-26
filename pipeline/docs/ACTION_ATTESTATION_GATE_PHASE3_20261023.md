# Phase 3 — オフライン署名・取消・失効検査（2026-10-23）

状態：D内部 Draft。災害時の公的安全認定ではない。

## 実装
- cryptographyのEd25519を使い、署名の対象に本文＋receipt ID＋key IDを含める。ドメイン分離・JSON正規化で差分を厳密に照合。
- 出典URL、元データSHA256、災害種別、地域、確認項目、範囲ID、観測・取得・宣言有効期限、署名発行と有効期限を照合する。
- 運用者が別の信頼経路で用意した公開鍵集合を受け取る。出典照合役と独立レビュー役は異なるprincipalと鍵が必要。
- 運用者が別途認証して渡した取消台帳の鍵・receipt取消と期限を検証し、欠損・期限切れはBLOCKED。
- 正しい2署名ならSIGNATURES_VALID_ONLY。どんな場合でもofficial_source_authenticated=false、independent_human_review_proven=false、eligible_for_action_decision=false、published_for_disaster_use=false。

## 重要な制約
- このコード自体は公開鍵台帳と取消情報の真偽・発行者・更新の完全性を証明しない。ブラウザやユーザー提供JSONを信頼根拠として渡してはいけない。
- 署名が有効でも、原本の実バイトが正しく取得されたこと、公式公開者の真正性、審査者の人的独立性、施設・建物・避難経路の安全性は証明されない。
- 署名用の秘密鍵をリポジトリ・DB・PRへ保存しない。合成テストは毎回使い捨て鍵を生成。
- DRILL用の実験のみ。LIVE、公式警報接続、共有Schema、RegionExport、GIS、デプロイ、個人情報保存は対象外。
- 本番運用には、人間が承認した鍵登録・鍵失効・取消台帳の認証/配信・独立監査プロセス・期限評価が別途必須。

## テスト
pipelineディレクトリから、単体テスト（test_action_attestation_gate）とtest全体を実行。合成鍵による署名の正/負、改ざん、重複/別人、地域と災害の混入、期限切れ、取消、LIVE誤昇格防止を確認する。

このPRは未承認の#306→#307→#308の後続Draft。mainへの統合は別のMerge Captain判断を要する。
