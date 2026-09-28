# Frontend AI Rules

root `/AGENTS.md` を必ず先に読んでください。

このディレクトリは B 担当です。

UI は D が公開する共有 Contract を Consumer として利用します。

## Rules

- JSON の存在しないフィールドを推測して表示しない。
- `score=null` を 0 として表示しない。
- UNKNOWN / NOT_FOUND / BLOCKED を同じ意味で表示しない。
- `NOT_FOUND` を「自治体が公開していない」と言い換えない。
- Gap を自治体ランキングへ変換しない。
- 公式リスク区分の意味を UI 側で独自変換しない。
- Contract 変更が必要なら B 側で独自フィールドを生やさず D / shared contract の PR として提案する。

前提 Contract PR が未マージでも開発可能ですが、PR に `Depends on: #...` を明記し、統合前に最新 main で再確認してください。
