# HINANEX Frontend

B担当のUI実装です。現在は、RegionExport `0.9`形式の合成データを使ってSC02地域詳細画面の見え方を確認できます。

## 現在の実装（3地域の仮UI）

画面上部のボタンで、次の3地域を切り替えられます。

- 東京都江戸川区: Capability `FULL`、Gapなし、Recommendationなし
- 新潟県新潟市: Capability `FULL`、Gapなし、Recommendationなし
- 愛知県名古屋市: Capability `BLOCKED`、Gapあり、Recommendationあり

地域を切り替えると、地域基本情報、Capability、Dataset Assessment、Data Quality、Application Readiness、Gap、Recommendation、Evidenceをまとめて再描画します。

表示するデータは`mock/region-exports.js`にあるUI確認専用の仮データです。実在地域の評価、施設数、公開状況、安全性を表さず、実際の自治体評価や防災判断には使用できません。

UI側では評価結果、スコア、Gap、Recommendationを再計算しません。`score=0`は`0 / 4`、`score=null`は`未評価`として区別します。非取得状態の`record_count=0`も、実施設が0件という意味では表示しません。

## 起動

`frontend/`で静的サーバーを起動します。D Pipelineの実行やruntime artifactの生成は不要です。

```powershell
cd frontend
python -m http.server 4173
```

その後、`http://localhost:4173`を開きます。

## テスト

追加パッケージは不要です。Node.js 20以降で実行します。

```powershell
npm test
npm run lint
npm run build
```

このFrontendは依存なしの静的サイトです。`build`は配布物の生成ではなく、必須ファイルとHTML参照を検証します。

## 今後の実データ接続

D Pipelineの実RegionExportとの接続は次の作業として分離します。現在の仮UIでは`pipeline/data/output/*.json`を読み込まず、Frontend内のmockだけを利用します。

## 契約境界

- JSON Schema: `../pipeline/contracts/region_export.schema.json`
- B向け引き渡し: `../pipeline/docs/HANDOFF_B.md`
- B/C契約: `../pipeline/docs/HANDOFF_CONTRACT_v1.0.md`
- UIルール: `AGENTS.md`

表示に必要なフィールドがContractに存在しない場合は、Frontend独自の意味付けを追加せず、D担当へContract変更として提案します。
