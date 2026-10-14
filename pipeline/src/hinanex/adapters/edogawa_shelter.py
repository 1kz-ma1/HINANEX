from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import httpx
import pandas as pd

from src.hinanex.adapters.base import SourceAdapter
from src.hinanex.models.common import Evidence, NormalizedDataset
from src.hinanex.models.shelter import ShelterRecord


class EdogawaShelterAdapter(SourceAdapter):
    """Adapter for Edogawa City's shelter / supplementary shelter CSV."""

    REGION_CODE = "13123"
    REGION_NAME = "東京都江戸川区"

    SOURCE_URL = (
        "https://www.city.edogawa.tokyo.jp/"
        "documents/4408/20251211_hinanhokan.csv"
    )

    SOURCE_PAGE_URL = (
        "https://www.city.edogawa.tokyo.jp/"
        "e004/kuseijoho/opendata/map_data.html"
    )

    RAW_PATH = Path("data/raw/edogawa/20251211_hinanhokan.csv")

    def fetch(self) -> bytes:
        response = httpx.get(
            self.SOURCE_URL,
            timeout=30.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.content

    def save_raw(self, raw: bytes) -> str:
        self.RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.RAW_PATH.write_bytes(raw)
        return str(self.RAW_PATH)

    def normalize(self, raw: bytes) -> NormalizedDataset:
        df = pd.read_csv(BytesIO(raw), encoding="cp932")

        required_columns = {
            "名称",
            "URL",
            "災害種別記号",
            "コメント",
            "緯度",
            "経度",
        }

        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(
                f"必要な列がありません: {sorted(missing_columns)}"
            )

        # This is a lossless pass-through of address text ONLY if the current
        # official location CSV actually supplies an address column. Neither
        # site name nor latitude/longitude is used to guess an address. This
        # does not join a separate flood-hazard HTML source to any location.
        address_columns = [
            col for col in ("住所", "所在地") if col in df.columns
        ]
        records: list[dict] = []

        for _, row in df.iterrows():
            name = str(row["名称"]).strip()
            latitude = float(row["緯度"])
            longitude = float(row["経度"])
            raw_addresses = {
                value for col in address_columns
                if (value := self._optional_string(row[col])) is not None
            }
            # Conflicting official columns cannot be reconciled by D without
            # additional evidence. Preserve null rather than select a guess.
            address = next(iter(raw_addresses)) if len(raw_addresses) == 1 else None

            facility_type = (
                "supplementary_shelter"
                if "（補完施設）" in name
                else "shelter"
            )

            shelter = ShelterRecord(
                id=self._build_id(name, latitude, longitude),
                name=name,
                latitude=latitude,
                longitude=longitude,
                address=address,
                facility_type=facility_type,

                # 「災害種別記号」は実データ上アイコンURLであり、
                # 対応災害を安全に意味付けできないため推測しない。
                supported_disasters=None,

                # このCSV単体では確認できない。
                accessibility=None,
                capacity=None,

                detail_url=self._optional_string(row["URL"]),
                notes=self._optional_string(row["コメント"]),
            )

            records.append(shelter.model_dump())

        evidence = Evidence(
            source_name="江戸川区 地図データ：避難所・避難所補完施設",
            source_url=self.SOURCE_PAGE_URL,
            publisher="東京都江戸川区",
            published_at=None,
            fetched_at=datetime.now(timezone.utc),
            license="CC BY 2.1 JP",
            source_format="CSV",
            retrieval_method="HTTP_DOWNLOAD",
            notes=(
                "災害種別記号列はアイコンURLとして取得されるため、"
                "supported_disasters の判定には使用していない。"
                "住所/所在地は元CSVに存在し、同一行内で矛盾しない場合だけ原文保存する。"
                "この住所を別Sourceの水害待避施設との確定joinとは扱わない。"
                "公式ページ上の2025-12-11は更新日として表示されるため、"
                "初回公開日とは扱わず published_at は null とする。"
            ),
        )

        return NormalizedDataset(
            region_code=self.REGION_CODE,
            region_name=self.REGION_NAME,
            requirement_code="shelter_location",
            records=records,
            evidence=[evidence],
            normalized_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _optional_string(value) -> str | None:
        if pd.isna(value):
            return None

        text = str(value).strip()
        return text if text else None

    @classmethod
    def _build_id(
        cls,
        name: str,
        latitude: float,
        longitude: float,
    ) -> str:
        source_key = (
            f"{cls.REGION_CODE}|"
            f"{name}|"
            f"{latitude:.7f}|"
            f"{longitude:.7f}"
        )
        digest = sha256(source_key.encode("utf-8")).hexdigest()[:16]
        return f"edogawa-{digest}"
