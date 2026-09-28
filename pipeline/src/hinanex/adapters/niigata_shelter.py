from __future__ import annotations

import html as html_lib
import re
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin

import httpx
import pandas as pd

from src.hinanex.adapters.base import SourceAdapter
from src.hinanex.models.common import Evidence, NormalizedDataset
from src.hinanex.models.shelter import ShelterRecord


class _AnchorCollector(HTMLParser):
    """Collect href + visible/alt text without adding a scraping dependency."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if tag.lower() == "a":
            self._href = attributes.get("href")
            self._parts = []
        elif tag.lower() == "img" and self._href:
            alt = attributes.get("alt")
            if alt:
                self._parts.append(alt)

    def handle_data(self, data: str) -> None:
        if self._href:
            text = data.strip()
            if text:
                self._parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._href:
            return

        label = " ".join(self._parts).strip()
        self.links.append((self._href, label))
        self._href = None
        self._parts = []


class NiigataShelterAdapter(SourceAdapter):
    """Adapter for Niigata City's current standard evacuation-space CSV.

    The official open-data page publishes a current
    「指定緊急避難場所一覧」 CSV. The concrete CSV URL may change when the
    municipality updates the file, so the adapter discovers the current link
    from the official catalog page before downloading it.
    """

    REGION_CODE = "15100"
    REGION_NAME = "新潟県新潟市"

    SOURCE_PAGE_URL = (
        "https://www.city.niigata.lg.jp/"
        "shisei/seisaku/it/open-data/"
    )

    RAW_PATH = Path("data/raw/niigata/niigata_evacuation_space.csv")

    DISASTER_COLUMNS = {
        "災害種別_洪水": "flood",
        "災害種別_崖崩れ、土石流及び地滑り": "landslide",
        "災害種別_高潮": "storm_surge",
        "災害種別_地震": "earthquake",
        "災害種別_津波": "tsunami",
        "災害種別_大規模な火事": "large_fire",
        "災害種別_内水氾濫": "inland_flood",
        "災害種別_火山現象": "volcanic_phenomenon",
    }

    def __init__(self) -> None:
        self._resolved_source_url: str | None = None
        self._published_at: datetime | None = None

    def fetch(self) -> bytes:
        page = httpx.get(
            self.SOURCE_PAGE_URL,
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "HINANEX/0.6 (+graduation-project)"},
        )
        page.raise_for_status()

        self._resolved_source_url = self.discover_csv_url(page.text)
        self._published_at = self.extract_update_date(page.text)

        response = httpx.get(
            self._resolved_source_url,
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "HINANEX/0.6 (+graduation-project)"},
        )
        response.raise_for_status()
        return response.content

    def save_raw(self, raw: bytes) -> str:
        self.RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.RAW_PATH.write_bytes(raw)
        return str(self.RAW_PATH)

    def normalize(self, raw: bytes) -> NormalizedDataset:
        df = self._read_csv(raw)

        name_col = self._resolve_column(df, "名称", "施設名", "SAFIELD000")
        latitude_col = self._resolve_column(df, "緯度", "latitude")
        longitude_col = self._resolve_column(df, "経度", "longitude")

        id_col = self._resolve_optional_column(df, "ID", "id", "SAUID")
        url_col = self._resolve_optional_column(df, "URL", "url")
        notes_col = self._resolve_optional_column(df, "備考", "コメント")

        records: list[dict] = []

        for row_index, row in df.iterrows():
            name = self._optional_string(row[name_col]) or ""
            latitude = self._optional_float(row[latitude_col])
            longitude = self._optional_float(row[longitude_col])

            source_id = (
                self._optional_string(row[id_col]) if id_col else None
            )

            disaster_columns_present = [
                column
                for column in self.DISASTER_COLUMNS
                if column in df.columns
            ]

            supported_disasters: list[str] | None
            if disaster_columns_present:
                supported_disasters = [
                    self.DISASTER_COLUMNS[column]
                    for column in disaster_columns_present
                    if self._is_supported_marker(row[column])
                ]
            else:
                supported_disasters = None

            shelter = ShelterRecord(
                id=self._build_id(
                    source_id=source_id,
                    row_index=int(row_index),
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                ),
                name=name,
                latitude=latitude,
                longitude=longitude,
                facility_type="designated_emergency_evacuation_site",
                supported_disasters=supported_disasters,
                accessibility=None,
                capacity=None,
                detail_url=(
                    self._optional_string(row[url_col]) if url_col else None
                ),
                notes=(
                    self._optional_string(row[notes_col]) if notes_col else None
                ),
            )

            records.append(shelter.model_dump())

        evidence = Evidence(
            source_name="新潟市 自治体標準オープンデータセット：指定緊急避難場所一覧",
            source_url=self._resolved_source_url or self.SOURCE_PAGE_URL,
            publisher="新潟県新潟市",
            published_at=self._published_at,
            fetched_at=datetime.now(timezone.utc),
            license="新潟市オープンデータ利用規約",
            source_format="CSV",
            retrieval_method="OFFICIAL_PAGE_LINK_DISCOVERY_HTTP_DOWNLOAD",
            notes=(
                "新潟市公式オープンデータページから現在のCSVリンクを発見して取得。"
                "shelter_location評価では名称・緯度・経度のみを必須項目として扱う。"
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

    @classmethod
    def discover_csv_url(cls, html: str) -> str:
        parser = _AnchorCollector()
        parser.feed(html)

        candidates: list[str] = []

        for href, label in parser.links:
            normalized_label = re.sub(r"\s+", "", label)
            if "指定緊急避難場所一覧" not in normalized_label:
                continue

            absolute = urljoin(cls.SOURCE_PAGE_URL, href)
            candidates.append(absolute)

            if ".csv" in absolute.lower():
                return absolute

        if candidates:
            return candidates[0]

        raise ValueError(
            "新潟市公式オープンデータページから"
            "指定緊急避難場所一覧のリンクを発見できませんでした。"
        )

    @staticmethod
    def extract_update_date(html: str) -> datetime | None:
        # Only record a date when it can be associated with the target dataset
        # in the page text. Failure to parse is UNKNOWN, not an invented date.
        visible = re.sub(r"<[^>]+>", " ", html)
        visible = html_lib.unescape(visible)
        visible = re.sub(r"\s+", " ", visible)

        match = re.search(
            r"指定緊急避難場所一覧.{0,300}?"
            r"(20\d{2})年(\d{1,2})月(\d{1,2})日",
            visible,
        )
        if not match:
            return None

        year, month, day = map(int, match.groups())
        jst = timezone(timedelta(hours=9))
        return datetime(year, month, day, tzinfo=jst)

    @staticmethod
    def _read_csv(raw: bytes) -> pd.DataFrame:
        last_error: UnicodeDecodeError | None = None

        for encoding in ("utf-8-sig", "utf-8", "cp932"):
            try:
                return pd.read_csv(BytesIO(raw), encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc

        if last_error:
            raise last_error
        raise ValueError("CSVを読み込めませんでした。")

    @staticmethod
    def _normalized_column_map(df: pd.DataFrame) -> dict[str, str]:
        return {str(column).strip(): str(column) for column in df.columns}

    @classmethod
    def _resolve_column(cls, df: pd.DataFrame, *aliases: str) -> str:
        column_map = cls._normalized_column_map(df)
        for alias in aliases:
            if alias in column_map:
                return column_map[alias]

        raise ValueError(
            "必要な列を確認できません: " + " / ".join(aliases)
        )

    @classmethod
    def _resolve_optional_column(
        cls,
        df: pd.DataFrame,
        *aliases: str,
    ) -> str | None:
        column_map = cls._normalized_column_map(df)
        for alias in aliases:
            if alias in column_map:
                return column_map[alias]
        return None

    @staticmethod
    def _optional_string(value) -> str | None:
        if pd.isna(value):
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _optional_float(value) -> float | None:
        if pd.isna(value):
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return float(value)

    @staticmethod
    def _is_supported_marker(value) -> bool:
        if pd.isna(value):
            return False

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return float(value) == 1.0

        normalized = str(value).strip().lower()
        return normalized in {"1", "○", "〇", "true", "yes", "可", "有"}

    @classmethod
    def _build_id(
        cls,
        *,
        source_id: str | None,
        row_index: int,
        name: str,
        latitude: float | None,
        longitude: float | None,
    ) -> str:
        source_key = "|".join(
            [
                cls.REGION_CODE,
                source_id or "",
                str(row_index),
                name,
                "" if latitude is None else f"{latitude:.7f}",
                "" if longitude is None else f"{longitude:.7f}",
            ]
        )
        digest = sha256(source_key.encode("utf-8")).hexdigest()[:16]
        return f"niigata-{digest}"
