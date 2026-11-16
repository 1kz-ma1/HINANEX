---
name: Device QA session
about: 予定日ごとにまとめて行う実機QAの手順・結果・不具合を追跡する
title: "[Device QA] YYYY-MM-DD QA-? "
labels: "area: shared"
assignees: ""
---

> 共通バックログ: [#372](https://github.com/1kz-ma1/HINANEX/issues/372) | 運用仕様: [Implementation-first Device QA](https://github.com/1kz-ma1/HINANEX/blob/main/docs/strategy/HINANEX_IMPLEMENTATION_FIRST_DEVICE_QA_20261113.md) | 最優先: [AGENTS.md](https://github.com/1kz-ma1/HINANEX/blob/main/AGENTS.md)
>
> 本Issueは**人間の物理端末検証**だけを記録する。Chrome CI / Simulatorを実機PASS扱いにしない。未承認災害データ・経路・施設位置/開設/安全性を勝手に承認しない。

## 検証回と準備
- QA枠/日付(JST):
- 時間帯・上限（目安60〜90分）:
- 進行担当（未確定はUNASSIGNED）:
- 対象commit SHA / Render deploy / TestFlight等ビルド識別子:
- **公開してよい対象か**（公開不可ならローカル限定/合成fixtureで実施）:
- 固定データ・Contract版・環境/機能フラグ:
- 検証対象Issue/PRとDQA-ID（3〜5フローを推奨）:

## 端末と参加
| 検証者 | 端末・OS・ブラウザ/VoiceOver等 | 担当DQA-ID |
| --- | --- | --- |
| UNASSIGNED | 未確認 | — |

## 検証シナリオ
| DQA-ID | 事前条件・操作手順 | 期待結果 | 結果(PASS/FAIL/BLOCKED/NOT_RUN) | 証跡/Issue |
| --- | --- | --- | --- | --- |
| DQA-### |  |  | NOT_RUN |  |

## 操作順
- [ ] スモーク（表示/初期読込/重大エラー）
- [ ] 主要ユーザーフロー（検索→比較→本人選択等、未承認表示を避ける）
- [ ] 画面幅/ズーム/タップ/スクロール/戻る
- [ ] 読み上げ・キーボード・アクセシビリティ（予定がある場合）
- [ ] ネットワークエラー/未確認/欠損/拒否のフォールバック
- [ ] 実機でしか分からない不具合を別Issueへ起票（重要度を記載）

## 結果・追跡
- Passed:
- Failed:
- Blocked:
- Not run:
- 不具合Issue:
- 元の[#372](https://github.com/1kz-ma1/HINANEX/issues/372) DQA-IDに結果URLを追記:
- 次の回へ繰越す項目:
- 最終受入判断（オーナー）: 未承認 / APPROVED_SCOPED / HOLD
- 安全・出典・一般公開承認: **別判定**（本Issueでは自動承認しない）
