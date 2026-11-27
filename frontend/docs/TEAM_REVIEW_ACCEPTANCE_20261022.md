# HINANEX 班員向けJSONレビュー受入テスト（2026-10-22）

**現在の状態：CI合格／Mac・Windowsでのこの更新版の実ブラウザ受入は未実施。**
対象はDraft PR #292、D側PR #293の公開情報だけを収録したローカルP1用JSON。
このドキュメントは「操作とレビュー結果の引継ぎ」を確認するもので、災害時の安全性、施設開設、敷地の物理同定、位置承認のテストではない。

## 事前準備

- Mac Safariと、別の班員のWindows Edge（可能ならChromeも）で**同じ単体** `team-review-v2.html` を開く
- JSONはD側で生成した `team_review_p1_sources_LOCAL.json`（正当な公開元・配布範囲を責任者が確認）を使用。候補座標・PRIVATE CSV・生のABR/GSIの実験データを班員へ配布しない
- 既存の結果JSON `hinanex-team-review-*.json` はバックアップ。操作中も古いものを上書きしない
- 2人以上の班員には同じ元JSONのコピーを配る。配布後の編集はそれぞれの結果JSONで行う。共有ドライブ上の「同じJSONファイル」を同時編集しない

## チェックリスト

- [ ] Mac SafariでHTMLを開くと見出しとファイル選択が表示（JSON未読込でも白画面にならない）
- [ ] Windows Edgeの `file://` でHTMLを開くと同じ画面が表示
- [ ] P1基準JSONを読み込むと**9件**。P1以外0件。新しい公式PDFリンクのグループが**5件**表示
- [ ] 区別PDFグループで、天白3／守山3／緑1／東1／中村1に絞り込める
- [ ] 公式PDFは班員が**自分でクリックして**外部ブラウザで開く（HTMLは自動ダウンロード・追跡送信しない）
- [ ] 未確認・根拠不足の表示で、URLなしの「根拠あり」は**未完了に残る**。状態は位置承認へ昇格しない
- [ ] 施設メモを編集して保存ボタンを押さずに別施設へ移動すると、未反映警告が出てメモを失わない
- [ ] 保存ボタンを押した後にJSONを書き出し、**別名で保存**したファイルを再読み込みするとメモが残る
- [ ] 別施設を担当した班員A/Bの2つのJSONを「まとめて取り込む」でインポートすると、変更結果が両方残る
- [ ] 同じ施設へ異なる変更を入れた班員A/Cの結果JSONをまとめて読み込むと**全体が中止**され、基準JSONは変更されない
- [ ] 不正なJSONや安全フラグ `approved_for_map=true` への改変は拒否される。B/C/EのRegionExportを班員レビューJSONとして誤読しない
- [ ] 更新後の結果JSONにも `approved_for_map=false`、`data_promotion_authorized=false`、`official_facility_positions_accepted=0` が残る
- [ ] 各班員が確認したURL、確認理由、判断保留事項、担当名が自分の結果JSONに残る（URLなしを資料確認完了とみなさない）
- [ ] 配布予定JSONにPRIVATE原本、座標、個人情報、不要なファイルパス・認証情報がないか担当者が確認

## 判定と次の手順

- **CI**: `frontend/tests/team-review.test.js` ではJSON契約、座標・追加安全フィールド拒否、競合時の原子的中止、作業記録の上書き防止を自動検証
- **実ブラウザ**: 上記のうち、操作したテストだけWindows／Mac別に記録する。実施していないものはPASSにしない
- **もし不具合が出たら**: OSとブラウザの版、操作順、UIのメッセージを報告。PRIVATE JSON全文や生座標はGitHub Issueへ貼らない
- **main統合前**: PR #283→#293の依存を確認し、PR #292の最新main追従・required CI・人のMerge Captain確認を別途実施。配布データの許可も必要
- 公式資料の更新検知は独立のDraft PR #295。取得ファイルのバイト差分を調べるだけで、実際の施設安全や災害種別を判定しない

## 2026-11-25 追加ゲート

- 前記CI合格は当時の記録。最新main追従後の確定HEAD CIは別途記録する。
- 書き出し開始／取消／失敗では未保存警告を解除しない。実ファイルの保存確認後に本人確認ボタンを押す。読込中の編集、二重読込、基準入替も負例として実機検証する。
- ローカル専用。公開indexから導線を追加しない。Deploy担当によるHTML・fixture・QA・文書の除外と候補実バンドル不在確認が必要。直接URL不在、実データの配布許可、物理端末は未確認。

## 2026-11-27 #495 配布境界の整理

以下は従来のREADMEの班員限定操作説明を省略せず移管した記録です。公開側READMEはmainと同一に戻し、公開build-checkの班員限定検査を既存の非公開 `tests/team-review.test.js` へ移管しました。`npm test` は必須CIで実行されます。公開 `npm run build` はmainと同一の公開静的資材検査に戻します。HTML・fixture・テスト・本書の配布除外は依然として #495 のShared担当による別PR・実候補コピー検査・人間の決裁が必要です。

## チーム向け施設レビュー（JSON交換・完全ブラウザ内）

- エントリ：ローカルの `frontend/team-review.html`（班員限定。公開サイトの導線は追加しない）
- 単体配布：`frontend/team-review.html` を班員へ共有し、ブラウザで直接開く。スタイルと処理はHTMLに内蔵し、サーバー・外部JS・通信は不要。
- JSONサンプル：`frontend/mock/team-review-example.json` は**完全に合成データ**。実在施設に関する事実は含まず、正式データとして利用できない。
- アプリはJSONの読み込み・施設別の確認メモ/根拠URL/作業状態編集・JSON書き出しに対応。**自動保存なし・同時編集なし**。班員間では各自の書き出し版を別ファイルとして保存すること。最新UIは出典fingerprintと施設ID・施設情報の一致を検証したうえで**複数JSONのレビューを統合**できる（同施設の異なる記録は競合として全件中止）。未反映フォームや未書き出しの変更を失わないよう操作をブロック／タブ閉鎖を警告する。実ファイルの保存完了自体は自動検証できないため、書き出し後に実際のファイルを本人が確認し、確認済みボタンを押すまで未保存扱いとする。
- ローカルページには実施設の確認データを埋め込まず、配布専用JSONだけを**ユーザーがブラウザへ明示的に読み込む**。PRIVATE CSV/HTMLや未承認のABR/GSI候補座標は入力禁止。JSONのスキーマは厳密で、余計なフィールドは拒否する。
- オフラインでもJSONをファイル選択で読み込める（file://からのfetchを使わない）。生成JSONもブラウザ内のBlob APIでダウンロードする。
- 全レコードの施設位置・災害適合性・開設状況・経路安全性は**未承認**。作業状態`evidence_found`は資料を見つけたという意味でのみ使用。出力に`approved_for_map:false` / `data_promotion_authorized:false` / `official_facility_positions_accepted:0`を必須とする。
- Schema（v1、入力時に余分なフィールドを拒否）：
  `schema_id:hinanex.team-review.v1`
  `dataset:{id,region,source_fingerprint}`（source_fingerprintは64桁hex）
  `safety:{approved_for_map:false,data_promotion_authorized:false,official_facility_positions_accepted:0}`
  `records:[{id,name,address,priority:P0|P1|P2,issues:[],sources:[{title,url}],review:{status,checks:{official_source,identity,address,position_evidence},reviewer,notes,evidence_url,reviewed_at}}]`
  status = `not_reviewed|in_progress|evidence_found|needs_follow_up`。位置の評価結果、事実関係の採否、避難先としての安全性を一切表現しない。
- 共有パッケージを生成するときは、**行政が公表している名称・掲載住所・共有を許可した確認理由/出典に限定すること**。座標、個別の実験経緯、監査に使用する秘密のID、GitHub認証情報は含めない。共有する相手や手段を確認する。
- ブラウザーに読み込んだJSONはサーバーへ送信せず、ローカルHTMLに保持するだけ。ただし公式外部リンクを押した場合は訪問先へアクセスするので、通常の閲覧ログは発生する。
- テスト：`cd frontend && npm test`。Windows Edge/ChromeおよびMac Safariの**実機E2Eは未実施**。PRの統合判断前にファイルインポート・保存・再インポート、ブラウザ再読込後の非保持、ローカルHTTPとfile://の同等性を確認する。
- `main`はRenderへ自動デプロイされるため、Merge Captainの承認前にはマージしない。共有UIの一般公開はアクセス制御ではない。守秘の対象をブラウザーへ読み込む運用が必要な場合、別途認証・配布権限制御を設計する。


### 班員3人のJSON自動統合と差分確認（2026-10-22 Draft追加分）

- 最初に**基準JSON**を読み込む。その後「班員の結果JSONをまとめて取り込む」から最大20ファイルを選ぶ（例: 3人の提出ファイル）。**基準データを直接上書きしない**。成功時に表示状態を更新し、必ず別名JSONで書き出す。
- `dataset.id`/`dataset.region`/`dataset.source_fingerprint`、全施設数・不変の名称・住所・優先度・要確認コード・不変IDが揃うか厳密検証。同じ施設の異なるレビュー内容が見つかった場合は**統合全体を中止**し、元データを変更しない。片方の未確認初期状態は更新内容を持つ側を優先。レビュー内容が同じで日時だけ異なる場合は後の日時を保持。
- 基準ファイルの公式PDF資料リンクを維持し、読み込んだ他者JSONから `sources` を自動取り込まない。元データが更新されて参照資料が増えていても、既存レビューの統合を妨げないようにする。異なる施設情報に対するレビューは拒否。
- 「根拠・確認が未完了の施設だけ表示」チェックONがデフォルト。班員の確認記録として必要な4項目のチェック、`evidence_found`、根拠URLのどれかが欠けていれば確認待ちで表示する。**作業記録の形式上の完了は、実際の施設位置承認を意味しない**。
- `evidence_found` なのに根拠URLが空の記録（初期パイロットで実際に発生）は警告し、報告時に補足出典を記録する。
- 名古屋市公式の区別PDFリンクは D側PR #293 の `nagoya_team_review_official_sources.py` により**施設名+住所が完全一致**する9件のみに付与される（2026-09-01時点の公開一覧、2026-10-22確認）。PDF掲載は施設位置・現在の開設・災害適合性の立証とは異なる。
- まだE2E実機未確認。**Draft PR #292, #293, #283 の統合順・展開はMerge Captainの判断。** 自動共有・自動公開・レビューの正式認可は実装していない。

- 非公開ゲート：現行Deployのコピー除外には本HTML・合成fixture・QA・受入文書が未登録。一般公開リンクを追加しないだけでは直接URL配信を防げないため、Deploy担当による独立除外回帰・候補バンドルでの不在確認・人間の配布決裁が成立するまでソース統合HOLD。
