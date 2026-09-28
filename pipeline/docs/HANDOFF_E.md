# E担当への引き渡し — GIS / Map

EはDが正規化した位置情報を地図表現へ利用します。

## 現在利用できる主なフィールド

`shelter_location` の各record:

- `id`
- `name`
- `latitude`
- `longitude`
- `address`
- `administrative_area`
- `facility_type`
- `detail_url`

## 座標の扱い

- `latitude` / `longitude` は`null`になり得ます。
- Dは住所から暗黙にジオコーディングしません。
- 座標がないrecordを地図から黙って消す場合は、UI上で件数差が分かるようにしてください。
- 将来ジオコーディングする場合、公式座標と推定座標を区別できるEvidence/品質属性を追加してから利用します。

## 責務分離

- D: 取得・正規化・品質判定
- E: 地図描画・レイヤ・空間可視化

E側で自治体固有CSVを直接解釈しないことを推奨します。
