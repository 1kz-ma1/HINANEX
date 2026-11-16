# F05/P0 B最小導線：受入メモ（Issue #362）

## ユーザー操作

1. F01 GISは常に独立入口。GIS側のデータ/洪水ラスタ/出典/取得エラーを維持。
2. F05ローカル試作で江戸川区13123を本人が明示選択。位置/GPS/地図のviewport/ハザード/施設IDは渡さない。
3. HTTP loopbackでのみF02非公開read-only画面への明示リンク。一般公開originではF02へリンクしない。JSONエラーはF02自身に任せる。
4. F05側には施設比較・安全認定・開設中表示・経路・外部API・F03保存はない。参考経路は未提供と明示。

## 主な実装と受入条件

- frontend/src/f05-journey-model.js : 明示地域コードとloopback originだけの純粋判定
- frontend/prototypes/f05-flood-journey/index.html : local-only UI。本人操作がないとF02へのhrefなし。公式情報はユーザークリックのみに限定
- frontend/tests/f05-journey.test.js : 非ローカルorigin、偽origin、未選択/地域不一致、旧選択破棄、施設ID未連携、誤認防止のテスト
- Schema/D Contract/E GIS/A/C/実データに変更なし
- F01、F02は別画面のまま動作。表示誤解の確認はChrome/Safari/Android実機の独立受入とする

## 確認の区分

- Implementation: Draft試作、main未統合
- Test Passed: 新HEADのCI結果を記載してから判定
- Independent Data Review: C全行照合は別（元CSV再配信や施設安全の証明ではない）
- Published: **NO**。独立Deployガード [PR #377](https://github.com/1kz-ma1/HINANEX/pull/377) は2026-11-16にmain統合済み。ただしRender実環境での直接GETによる非配信受入は [Issue #373](https://github.com/1kz-ma1/HINANEX/issues/373) で **NOT_VERIFIED**
- Owner approval: WIP順序/実装採用/公開範囲は未決定。#360の現行規則を維持

## 次に必要なゲート

- [ ] オーナー：#362 Bの初期スライスとして採用する判断
- [ ] exact HEAD required test SUCCESS
- [x] F05独立試作に対するDeploy除外ガードがmain先行統合（PR #377）
- [ ] Renderの実配信コミット照合とF05試作・モデルJSの直接GETが404/非配信であることを記録（Issue #373）
- [ ] 実HTTP Chromeの320/390/1440幅・キーボード・外部自動通信ゼロの受入
- [ ] 必要ならE側F01入口変更を別Issue/PRで採用
- [ ] #366原CSV再配信/第三者権利など、公開ゲートを別承認

**この文書・PRは公式の避難先を認定せず、一般公開の同意でもない。**

## 2026-11-16 main追従・レビュー追補

- B Draft PR #371はmain `c65fe1d4f19db2ddd907df8d8556bdedcd2a40d7` （Deploy #377まで含む）をブランチへ取り込み、F05の実装差分は引き続きB `frontend/**` 内の5ファイルのみ。
- 実装の静的検査：本人選択した江戸川区13123 + HTTP loopback以外ではF02 hrefが生成されず、公式洪水データ・施設ID・位置・安全・開設・経路を推測しない。
- **追加受入が必要：** F05試作そのものの実HTTP Chrome（320/390/1440px）/キーボード操作/遷移/外部通信のテスト。既存F02/F03 Chrome成功は代替にならない。F05テストはNodeモデル・HTML静的検証のみ。
- 最新mainでの必須CIの実行結果は、この追補とは独立にPR #371の本文へ記録。Render本番相当HTTPは依然NOT_VERIFIED。
