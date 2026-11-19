# F01 読込失敗から既存設定へ戻る（Issue #441）

地域詳細画面の読込失敗カードに「読み込み設定を開く」を追加する。本人が押すと既存の詳細設定を開き、summaryへフォーカスを移す。続けてTabで読込対象/再読込/手動JSON/明示合成デモの既存操作を選べる。

このボタンだけではデータ取得、合成へのfallback、ファイル選択ダイアログを起動しない。再読込は既存ボタンを本人が実行した時だけ、既存controllerのsame-origin JSONへ行う。失敗を施設0件と同一視せず、以前の結果を表示しない。既存JSONの契約不一致・手動JSON不正にも同じ設定導線を使う。

実HTTP/headless Chromeでは、初回JSON503→native Enterで設定open/summary focus→Tabで再読込へ移動→Enterで同じJSONを1回だけ再取得→再503でも施設行なし、を320/390/1440pxで検証する。44px操作領域、カードの横溢れ、設定を開くだけで追加データリクエスト0、暗黙合成読込なしを確認。後続の既存F01ページ操作/UNKNOWN/出典/異常系回帰を維持する。

**Device QA DEFERRED / #372 DQA-008追加**。物理Safari/VoiceOver、Android/TalkBack、iOS、手動タッチ/読み上げ/独立HARはNOT_RUN。設定へ移動したことの理解・読み上げ・Tab順はQA-1（2026-12-06 JST）候補、担当UNASSIGNED。自動Chrome成功を実機受入へ流用しない。

新API/URL/controller/Schema/評価/データ/出典/位置/安全意味を変更せず、B以外の未完了実装への依存なし。新GPS/外部送信/保存/経路/実施設追加なし。F02/F05非公開ガードを維持。#362/#371/#366/#358/#373等の原本権利・施設安全・一般公開・Render LIVE受入は別ゲート。
