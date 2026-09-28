# Validation AI Rules

root `/AGENTS.md` を必ず先に読んでください。

このディレクトリは C 担当です。

C の目的は、HINANEX の結果が根拠まで追跡できることを検証することです。

基本トレース:

```text
Official Source
→ Evidence
→ Normalized Record
→ DatasetAssessment
→ CapabilityAssessment
→ Gap
→ Recommendation
```

## Rules

- Source と出力が違う場合、出力に合わせて Source の解釈を変えない。
- 検証で見つけた不整合を黙って production logic に直接埋め込まない。
- 期待結果が仕様から導けない場合、テストを推測で固定しない。
- `null` と 0、UNKNOWN と BLOCKED を区別して検証する。
- Evidence の欠落は明示する。
- 「自治体が悪い」という評価ではなく、HINANEX が何を確認できたかを検証する。

不具合は再現条件・source・expected・actual を揃えて報告してください。
