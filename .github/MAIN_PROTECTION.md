# main Branch Protection

HINANEX の `main` は統合済み・再現可能な状態だけを置く branch です。

## Protection policy

`main` には次を要求します。

- Pull Request 経由で変更する
- required status check `test` が成功している
- merge 前に最新 `main` を取り込んだ状態で check が成功している
- force push を禁止する
- branch deletion を禁止する
- repository admin / Merge Captain にも同じ保護を適用する
- approval 人数は必須にしない

Approve と Merge は分離します。
コード単体のレビューと、main に今この順番で統合して安全かの判断は別です。

main への最終 merge は Merge Captain が行います。

## Why approval count is zero

5人規模の卒業制作で、Merge Captain 自身が実装する変更もあるため、required approval を必須にすると不要な停止が発生します。

代わりに:

1. PR を必須化
2. CI `test` を必須化
3. 最新 main 追従を必須化
4. Merge Captain が依存関係を確認

で統合安全性を確保します。

必要になった段階で required approvals を 1 以上へ強化できます。

## Initial setup

Protection は Git 管理ファイルだけでは有効になりません。
repository admin 権限を持つ人が一度だけ設定します。

PowerShell:

```powershell
cd C:\HINANEX
.\scripts\setup-main-protection.ps1
```

スクリプトは protection を設定する前に、main の最新 `test` workflow が成功していることを確認します。
CI が赤い場合は設定を中止します。

GitHub CLI の認証が未設定なら先に:

```powershell
gh auth login
```

を実行してください。

## Verify

```powershell
.\scripts\setup-main-protection.ps1 -VerifyOnly
```

または GitHub の repository Settings から Branch protection / Rules を確認できます。

## AI rules

AI は:

- protection を解除しない
- required check を回避しない
- failing test を削除・skipしてgreenに見せない
- Merge Captain の代わりに main へ merge しない
- required check が失敗しているPRを ready と扱わない

でください。

Emergency で protection の変更が必要な場合は、人間が理由を確認して明示的に判断します。
