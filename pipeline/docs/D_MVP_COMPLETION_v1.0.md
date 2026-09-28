# HINANEX D担当 完了条件 — v1.0-D-MVP

D担当は、単に分析コードが動くだけでなく、他担当が安全に統合できる状態までを完了とします。

## Engine Ready

- [x] 江戸川区・新潟市・名古屋市の3地域workflow
- [x] Raw -> Normalize -> Assessment -> Capability -> Gap -> Recommendation
- [x] 1地域1JSON
- [x] JSON契約検証
- [x] C向けmanifest
- [x] 全工程の一括実行
- [x] 欠損と不正値、0とnullの意味論分離

## Integration Ready

- [x] GitHub Actionsでユニット/回帰テストを自動実行できる
- [x] JSON Schema同期をCIで確認できる
- [x] `.gitignore`でRaw/生成物/秘密情報を保護
- [x] PR / Issueテンプレート
- [x] A/B/C/E引き渡し文書
- [x] Architecture / Git workflow / Integration checklist
- [x] Project releaseとContract versionを分離

## GitHub上での正式完了判定

以下を満たした時点でD-MVPを正式完了とします。

1. `main` にv1.0-D-MVPがpushされている
2. GitHub Actionsの`test` jobがgreen
3. Branch protection / Rulesetでmainへの直接変更を抑制
4. A/B/C/Eが各handoff文書から作業開始できる

完了後、Dは新機能追加を先行しすぎず、チーム統合で見つかった問題の修正を優先します。
