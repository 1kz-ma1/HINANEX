# 避難行動の情報源と検証報告の参照契約 / Phase 2（2026-10-23）

**Draft / D内部のみ / DRILL専用 / UNKNOWN固定。公式の承認処理ではない。**

## 目的
Phase 0（#306）の事前条件・避難行動の型、Phase 1（#307）の複合災害・情報欠落に対して、出典・原本ハッシュ・災害種別・地域・確認項目・適用範囲・観測/取得/期限・報告上の独立レビュー結果を同じ識別子で突き合わせる。

- SourceClaim: HTTPS形式のURL、provider_label、source_id、SHA256文字列、地域コード、災害、カテゴリ、MUNICIPAL_REGIONまたはGSI_TILEとscope、観測/取得時刻と任意の申告期限。文字列が一致しても実原本や地理適用範囲を証明しない。
- ReviewClaim: review ID、reporter名、報告上のPASS/REJECTED/NOT_REVIEWED、対象SourceのSHA・地域・災害・範囲、報告時刻。「PASSと自己申告されたJSON」は信頼できる監査証跡ではない。
- EvidenceClaimBundle: Source・レビューの一意性、孤立したレポートの拒否。IDが重複しないことと正規性の証明は別。
- review_evidence_claims: 既存DRILLとの比較により、災害・地域・時点・範囲・カテゴリ・期限切れ・報告対象不一致を列挙する。報告PASSでも未認証とし、すべてUNKNOWN、承認・公開・避難行動の実行可能性は常にfalse。

## 防災安全性のゲート
- simulated fixtureにしか接続しない。DRILLをLIVEへ変換せず、現実の警報や開設状況を扱わない。
- SourceのURLを訪問しない。実際のraw取得、SHA計算、C独立監査、承認主体の認証、監査結果の署名・取り消しを実施しない。
- 「期限内と申告した」だけでは現況の最新性を確認できない。GSI tileは行政区域やユーザーの現在地への適用証明ではない。
- 新潟ODS公式記号・名古屋位置データの意味解釈を追加せず、RegionExport/Scenario/GIS/既存データの契約も変更しない。
- 個人の住所、精密位置、健康情報、備蓄などは保持しない。事前入力はまだ永続化しない。
- 公式データ接続と独立レビューの認証は別PRで、人間による承認・原本照合を必須とする。

## 合成テスト
SHA不一致、別地域・別災害・別カテゴリ、GSI tileと自治体区域の混同、期限切れ・時刻逆転、REPORTの偽装、重複・孤立、URL不正、DRILLに登録されていないcue、プロファイル値を漏らさないこと、すべてUNKNOWNを検証する。

テスト入口（pipeline/から）:

    python -m unittest tests.test_action_evidence_claims -v
    python -m unittest discover -s tests -v
    python verify_d_mvp.py

**本契約はD内部の未認証参照モデル。公的資料の承認や災害時利用の許可ではない。**
