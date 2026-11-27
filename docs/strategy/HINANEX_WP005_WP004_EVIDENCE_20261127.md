# HINANEX WP-005｜WP-004証拠引渡し記録

2026-11-27 JST · 送信側の照合・直接ダウンロード用の引渡し

対象は #483 確定HEAD `4612c2e6cb5d5e40a6f22bd030b39f2f7f738f9f`、検証基準main `4fc17aa056c5a13e2611aa9188bd61fda75484f3`。旧固定HEADは `03d8f92a1c776664765dc898acdefa94730cc040`。旧候補パッチの原本は未回収。ここで固定するパッチは、承認範囲で再作成し、旧固定HEADへの適用後に候補7ファイルの最終blobを照合した版。[限定再作成の承認](https://github.com/1kz-ma1/HINANEX/pull/483#issuecomment-7207654634) · [WP-004限定受入](https://github.com/1kz-ma1/HINANEX/pull/483#issuecomment-7208069914) · [確定HEADのCI](https://github.com/1kz-ma1/HINANEX/actions/runs/45925384942/job/140266406205)

## 1. 固定資材

| ファイル | サイズ | SHA-256 |
| --- | ---: | --- |
| `evidence.zip` | 35,086 bytes | `8098881ddd6de3e392672ccc7aafd6afa32fc8e70493b797fce0b82d0f86ea54` |
| `manifest.sha256` | 2,379 bytes | `61cd99b6cf965f2ca4d0284640ee9f9c2ba015a4948d93b0e70b3e04d3d04d15` |
| `mj01-wp004-reconstructed.patch` | 9,957 bytes | `cae741ab9f2de7cee77315849f4a71e10d42258729c00b2a6739f1421019cb70` |
| `REVIEW.txt` | 3,135 bytes | `1a8afbd7fa19b944f3f353f23597104505575b1b143ada348764307237a2a37c` |

ZIPは以下の27ファイルと `manifest.sha256` の計28項目。manifestが27ファイルの個別SHA-256を列挙する。

| 分類 | 収録ファイル |
| --- | --- |
| 原本・追跡 | `REVIEW.txt`, `mj01-wp004-reconstructed.patch`, `patch-replay.log`, `changed-blobs.txt`, `final-blobs.txt`, `pr-blobs.tsv`, `commit-history.txt` |
| 実装側・CI | `implementation-model.tap`, `implementation-lint.log`, `implementation-build.log`, `ci-evidence.log` |
| 独立モデル | `independent-model.mjs`, `independent-model-old.tap`, `independent-model-final.tap` |
| 独立Browser・通信 | `independent-browser.cjs`, `browser-old.log`, `browser-final.log`, `browser-network-audit.txt`, `browser-old.inet.trace`, `browser-final.inet.trace`, `independent-browser-proxy-attempt.log`, `guarded-chromium`, `restrict-datagrams.c` |
| オフライン配布 | `check-bundle.py`, `bundle-4612c2e6.log`, `bundle-manifest-4612c2e6.json`, `deploy-regressions-4612c2e6.log` |

## 2. 引渡し状況

WP-005の作業環境でWP-004の原本からダウンロード用コピーを作成。別の一時ディレクトリにそのコピーを取り込み、ZIPのCRC、名前の重複なし、収録集合、個別27ハッシュ、原本との全収録実バイト一致、standaloneのmanifest・再作成パッチとZIP内の同一性を確認した。既存試験の再実行は行っていない。

今回の受け渡しはOwner指定の直接ダウンロード。本作業チャットのファイルリンクからZIPと必要な同梱原本を取得し、司令塔・次の作業環境へ非公開で引き渡す。このMarkdownに原本は添付しない。司令塔または別環境の受領者による取得と実体照合は、受領記録が入るまで未確認。新しい非公開リポジトリ保管は今回の完了条件に含めない。

## 3. 受領側の照合

1. 取得したZIPと、別ファイルとして扱うmanifest・パッチのSHA-256を上表と照合する。
2. 空の作業フォルダーに展開し、ZIPのCRC・28項目・manifest 27行を確認する。展開先で `sha256sum --check manifest.sha256` を実行し、全件一致を記録する。同等のハッシュ検証手段も可。
3. `REVIEW.txt` の確定HEAD、`final-blobs.txt` の7 blob、`ci-evidence.log` の第1・第2試行、配布manifestと独立Browser／通信監査の対象を確認する。試験ログはその確定HEADの証拠として固定し、新HEADの受入には流用範囲を明記する。
4. 受領日（JST）、取得元、受領者、対象HEAD、ZIP・manifest・patchの実測SHA-256、収録件数と合否を司令塔へ返す。不一致・不足はD04の引渡し条件を保留し、同じ版の原本を再取得する。

この記録で確定するのは証拠の同一性と受け渡し方法。[D04の条件付き統合](https://github.com/1kz-ma1/HINANEX/pull/483#issuecomment-7208108799)には受領者の照合と[残存統合条件](HINANEX_WP005_STAGE2_GATES_20261127.md)が適用される。WP-004のオフライン非配信証拠は実LIVE manifestやCDNの確認を含まない。
