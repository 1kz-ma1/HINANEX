# HINANEX — D-MVP v1.0

HINANEX は、自治体ごとに形式の異なる防災データを取得・正規化し、**データ品質 → Application Readiness → Capability → Data Gap → Recommendation** までを、根拠付きで再現可能にする分析基盤です。

このリポジトリの `v1.0-D-MVP` は、D担当（データ基盤・評価エンジン）の中間発表向け完成基準です。B/UI、C/検証、E/GIS、A/データ調査が後から安全に合流できることを重視しています。

## 現在の検証対象

| 地域 | コード | 入力の特徴 |
| --- | --- | --- |
| 東京都江戸川区 | `13123` | CSV / 緯度経度あり |
| 新潟県新潟市 | `15100` | 自治体標準ODS系CSV |
| 愛知県名古屋市 | `23100` | 16区別の屋内施設Excelのみを統合 / 機械可読座標なし |

既存の縦スライスは `shelter_location -> Shelter Discovery` です。加えて、A PR #37を受けてScenario-local `shelter_hazard_applicability -> flood_shelter_selection` を **任意の `RegionExport.scenarios[]`** として追加しています。従来の位置データ品質・Capability判定は変更しません。Scenarioの仕様と未解決事項は [`docs/FLOOD_SCENARIO_CONTRACT.md`](docs/FLOOD_SCENARIO_CONTRACT.md) を参照してください。

```text
公式データ
  -> Raw保存
  -> 自治体別Adapter
  -> NormalizedDataset
  -> Data Quality / Application Readiness
  -> Capability
  -> Gap / Recommendation
  -> 1地域1JSON
  -> 契約検証 / C向けmanifest
```

## セットアップ

Python 3.12を基準環境とします。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 全工程を再生成

```powershell
python run_all_workflows.py
```

成功すると主に以下を生成します。

```text
data/output/
├─ edogawa.json
├─ niigata.json
├─ nagoya.json
└─ manifest.json

contracts/
└─ region_export.schema.json
```

`data/raw/`、`data/normalized/`、`data/output/` の実行生成物は原則Git管理しません。公式ソースから再生成できることをD-MVPの再現性要件としています。

## テスト

```powershell
python -m unittest discover -s tests -v
```

PRではGitHub Actionsが同じテストを実行し、コミット済みJSON SchemaがPydanticモデルと同期していることも検証します。

## A → D Integration Check

A担当のEvidence handoffとD Pipelineの接続前提は、通常のunit testに加えて実データ出力でも確認できます。

```powershell
python run_all_workflows.py
python verify_d_mvp.py
python verify_a_handoff_integration.py
```

詳細は `docs/A_D_INTEGRATION.md` を参照してください。

## バージョン

- Project release: `v1.0-D-MVP`
- B/C RegionExport contract: `0.9`
- Assessment / Capability / Gap engine: `0.9`

**プロジェクトのリリース番号とJSON契約番号は分離しています。** リポジトリ側の改善だけでB/Cへ不要なSchema移行を要求しないためです。

## 評価上の重要ルール

- `score = 0`: 評価した結果、その軸では利用できない。
- `score = null`: 未評価・評価不能。0点と同一視しない。
- 欠損と不正値を分離する。値が存在しないだけならValidityで二重減点しない。
- `NOT_FOUND` は「現在のHINANEX取得経路で見つからない」であり、自治体の未公開を断定しない。
- Capabilityは自治体の優劣を評価するものではなく、**現在取得できるデータで実行可能な支援能力**を表す。
- `Shelter Discovery = FULL` は `shelter_location` の名称・緯度経度による位置ベース探索条件を満たす意味に限定し、災害別安全性・収容人数・アクセシビリティ等を保証しない。
- `Evidence.published_at` は公開日を公式Sourceで確認できる場合のみ設定し、更新日しか確認できない場合は初回公開日を推測しない。

## チーム別の入口

- A / データ調査: `docs/HANDOFF_A.md`
- B / UI: `docs/HANDOFF_B.md`
- C / 検証: `docs/HANDOFF_C.md`
- E / GIS: `docs/HANDOFF_E.md`
- 全体構成: `docs/ARCHITECTURE.md`
- Git/PR運用: `docs/GIT_WORKFLOW.md`
- 統合時チェック: `docs/INTEGRATION_CHECKLIST.md`
- JSON契約詳細: `docs/HANDOFF_CONTRACT_v1.0.md`

## リポジトリ構成

現在のDパイプラインは、動作中のimport構造を壊さないためリポジトリ直下に維持します。A/B/C/E用の受け皿だけ先に用意しています。

```text
HINANEX/
├─ src/hinanex/          # D: 共通Schema / Adapter / 評価エンジン
├─ tests/                # D: 回帰テスト
├─ data/                 # D: 実行時データ（生成物は原則ignore）
├─ contracts/            # B/Cとの機械可読契約
├─ docs/                 # 設計・引き渡し文書
├─ data-research/        # Aの成果物の入口
├─ frontend/             # Bの実装入口
├─ validation/           # Cの検証成果入口
├─ gis/                  # Eの実装入口
└─ .github/              # CI / PR / Issueテンプレート
```

## D担当の完了条件

`docs/D_MVP_COMPLETION_v1.0.md` を基準とします。

D-MVP完了後は新規基盤開発を広げず、A/B/C/Eとの結合で見つかった問題を修正する統合フェーズに移ります。
