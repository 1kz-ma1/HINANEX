# HINANEX Frontend

B担当のUI実装です。D担当が生成するRegionExport JSONをConsumerとして読み込み、分析済みの結果を表示します。

## 現在の実装

- RegionExport `0.9`からCapabilityカードを1件表示
- Capability状態、評価理由、依存データを表示
- `requirement_code`を使ってEvidenceへ移動
- `FULL / DEGRADED / BLOCKED / UNKNOWN / NOT_APPLICABLE`を区別
- UI側では評価結果やスコアを再計算しない

`mock/region-export.json`は画面確認専用の合成データです。実在地域の防災状態を表しません。

## 起動

ブラウザーの`fetch`を利用するため、`frontend/`で静的サーバーを起動します。

```powershell
python -m http.server 4173
```

その後、`http://localhost:4173`を開きます。

## テスト

追加パッケージは不要です。Node.js 20以降で実行します。

```powershell
node --test
```

`npm`が利用できる環境では`npm test`でも同じテストを実行できます。

## 契約境界

- JSON Schema: `../pipeline/contracts/region_export.schema.json`
- B向け引き渡し: `../pipeline/docs/HANDOFF_B.md`
- UIルール: `AGENTS.md`

表示に必要なフィールドがContractに存在しない場合は、Frontend独自の意味付けを追加せず、D担当へContract変更として提案します。
