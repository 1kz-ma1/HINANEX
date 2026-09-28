# C担当への引き渡し — Validation

CはHINANEXの判定を人間が再確認し、ルールの誤判定・過剰断定・不足を発見します。

## 追跡経路

```text
Source / Evidence
  -> NormalizedDataset
  -> DatasetAssessment
  -> CapabilityAssessment
  -> Gap
  -> Recommendation
```

主な結合キー:

- `requirement_code`
- `capability_code`

地域横断サマリは `data/output/manifest.json` を利用できます。

## 検証記録の推奨項目

- region
- source
- HINANEX result
- human judgment: valid / needs_review / misclassified
- reason
- expected correction
- reviewer / date

## 特に確認してほしい点

- `null` と0が混同されていないか
- `NOT_FOUND`を「未公開」と断定していないか
- GapがEvidenceから説明可能か
- Recommendationが確認できた不足を超えて断定していないか
- Capabilityの状態とreasonsが矛盾していないか
