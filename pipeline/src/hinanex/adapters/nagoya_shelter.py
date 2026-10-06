from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
import pandas as pd

from src.hinanex.adapters.base import SourceAdapter
from src.hinanex.models.common import Evidence, NormalizedDataset
from src.hinanex.models.shelter import ShelterRecord


class _AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        attributes = dict(attrs)
        self._href = attributes.get("href")
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            text = data.strip()
            if text:
                self._parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._href:
            return
        self.links.append((self._href, " ".join(self._parts).strip()))
        self._href = None
        self._parts = []


class NagoyaShelterAdapter(SourceAdapter):
    """Adapter for Nagoya City's ward-separated indoor shelter Excel files.

    The official page publishes one Excel file per ward. `fetch()` discovers
    the current Excel links, downloads every ward file, and packs the untouched
    source files plus a manifest into one ZIP so the common SourceAdapter
    interface can still return `bytes`.

    Current indoor files contain facility names/addresses and disaster markers,
    but not machine-readable latitude/longitude. HINANEX therefore preserves
    the rows with null coordinates instead of geocoding silently. The existing
    shelter_location evaluator can then surface that confirmed geospatial gap.
    """

    REGION_CODE = "23100"
    REGION_NAME = "愛知県名古屋市"

    SOURCE_PAGE_URL = (
        "https://www.city.nagoya.jp/"
        "bousaiportal/hinan/1013390/1013492.html"
    )

    RAW_BUNDLE_PATH = Path(
        "data/raw/nagoya/nagoya_indoor_shelters_bundle.zip"
    )
    RAW_EXTRACT_DIR = Path("data/raw/nagoya/indoor")

    DISASTER_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
        "flood_inland": ("洪水内水", "洪水・内水", "洪水 内水"),
        "storm_surge": ("高潮",),
        "landslide": ("土砂", "土砂災害"),
        "tsunami": ("津波",),
    }

    DISASTER_OUTPUTS: dict[str, list[str]] = {
        "flood_inland": ["flood", "inland_flood"],
        "storm_surge": ["storm_surge"],
        "landslide": ["landslide"],
        "tsunami": ["tsunami"],
    }

    DATASET_SCOPE_NOTE = (
        "このshelter_location Datasetは、公式ページで区別に公開されている"
        "16区別の屋内施設Excelのみを対象とし、同ページ上の屋外施設データは"
        "含めていない。"
    )

    def __init__(self) -> None:
        self._page_updated_at: datetime | None = None

    def fetch(self) -> bytes:
        page = httpx.get(
            self.SOURCE_PAGE_URL,
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "HINANEX/0.7 (+graduation-project)"},
        )
        page.raise_for_status()

        links = self.discover_indoor_excel_links(page.text)
        self._page_updated_at = self.extract_page_update_date(page.text)

        manifest: list[dict[str, str]] = []
        bundle = BytesIO()

        with ZipFile(bundle, "w", compression=ZIP_DEFLATED) as archive:
            for ward, url in links:
                response = httpx.get(
                    url,
                    timeout=30.0,
                    follow_redirects=True,
                    headers={"User-Agent": "HINANEX/0.7 (+graduation-project)"},
                )
                response.raise_for_status()

                suffix = Path(urlparse(url).path).suffix.lower() or ".xls"
                safe_ward = re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龠_-]", "_", ward)
                filename = f"{safe_ward}{suffix}"

                archive.writestr(filename, response.content)
                manifest.append(
                    {
                        "ward": ward,
                        "url": url,
                        "filename": filename,
                    }
                )

            archive.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )

        return bundle.getvalue()

    def save_raw(self, raw: bytes) -> str:
        self.RAW_BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.RAW_BUNDLE_PATH.write_bytes(raw)

        self.RAW_EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
        with ZipFile(BytesIO(raw)) as archive:
            for name in archive.namelist():
                if name == "manifest.json":
                    continue
                target = self.RAW_EXTRACT_DIR / Path(name).name
                target.write_bytes(archive.read(name))

        return str(self.RAW_BUNDLE_PATH)

    def normalize(self, raw: bytes) -> NormalizedDataset:
        records: list[dict] = []
        evidence: list[Evidence] = []

        with ZipFile(BytesIO(raw)) as archive:
            manifest = json.loads(
                archive.read("manifest.json").decode("utf-8")
            )

            for item in manifest:
                ward = item["ward"]
                url = item["url"]
                filename = item["filename"]
                workbook_bytes = archive.read(filename)

                table = self._read_excel(workbook_bytes, filename)
                ward_records = self.normalize_table(table, ward=ward)
                records.extend(record.model_dump() for record in ward_records)

                evidence.append(
                    Evidence(
                        source_name=(
                            "名古屋市 指定緊急避難場所・指定避難所 "
                            f"{ward}（屋内施設）"
                        ),
                        source_url=url,
                        publisher="愛知県名古屋市",
                        published_at=None,
                        fetched_at=datetime.now(timezone.utc),
                        license="CC BY 4.0",
                        source_format=Path(filename).suffix.lstrip(".").upper(),
                        retrieval_method=(
                            "OFFICIAL_PAGE_LINK_DISCOVERY_HTTP_DOWNLOAD_"
                            "MULTI_EXCEL_BUNDLE"
                        ),
                        notes=self._build_evidence_notes(),
                    )
                )

        return NormalizedDataset(
            region_code=self.REGION_CODE,
            region_name=self.REGION_NAME,
            requirement_code="shelter_location",
            records=records,
            evidence=evidence,
            normalized_at=datetime.now(timezone.utc),
        )

    def _build_evidence_notes(self) -> str:
        notes = (
            "公式ページで区別に公開されている屋内施設Excelを取得。"
            "所在地は保持するが、このExcelから緯度経度は得られないため"
            "座標は推測・自動ジオコーディングせずnullのまま保持する。"
            + self.DATASET_SCOPE_NOTE
        )
        if self._page_updated_at is not None:
            notes += (
                "公式ページの更新日として"
                f"{self._page_updated_at.date().isoformat()}を確認。"
                "初回公開日とは確認できないため"
                "Evidence.published_atには使用しない。"
            )
        return notes

    @classmethod
    def discover_indoor_excel_links(
        cls,
        html: str,
    ) -> list[tuple[str, str]]:
        parser = _AnchorCollector()
        parser.feed(html)

        found: list[tuple[str, str]] = []
        seen_urls: set[str] = set()

        for href, label in parser.links:
            absolute = urljoin(cls.SOURCE_PAGE_URL, href)
            lower_url = absolute.lower().split("?", 1)[0]
            if not lower_url.endswith((".xls", ".xlsx")):
                continue

            compact = re.sub(r"\s+", "", label)
            match = re.search(r"([^（）()\s]+区)[（(]屋内施設[）)]", compact)
            if not match:
                continue

            if absolute in seen_urls:
                continue
            seen_urls.add(absolute)
            found.append((match.group(1), absolute))

        if not found:
            raise ValueError(
                "名古屋市公式ページから区別の屋内施設Excelを発見できませんでした。"
            )

        return found

    @staticmethod
    def extract_page_update_date(html: str) -> datetime | None:
        visible = re.sub(r"<[^>]+>", " ", html)
        visible = re.sub(r"\s+", " ", visible)
        match = re.search(
            r"更新日\s*(20\d{2})年(\d{1,2})月(\d{1,2})日",
            visible,
        )
        if not match:
            return None

        year, month, day = map(int, match.groups())
        jst = timezone(timedelta(hours=9))
        return datetime(year, month, day, tzinfo=jst)

    @classmethod
    def normalize_table(
        cls,
        table: pd.DataFrame,
        *,
        ward: str,
    ) -> list[ShelterRecord]:
        header_row = cls._find_header_row(table)
        column_labels = cls._build_column_labels(table, header_row)

        name_col = cls._find_column(column_labels, "施設名称")
        address_col = cls._find_column(column_labels, "所在地")
        number_col = cls._find_column_optional(column_labels, "番号")
        shelter_col = cls._find_column_optional(column_labels, "指定避難所")

        disaster_columns: dict[str, int] = {}
        for disaster_key, aliases in cls.DISASTER_COLUMN_ALIASES.items():
            index = cls._find_column_optional(column_labels, *aliases)
            if index is not None:
                disaster_columns[disaster_key] = index

        records: list[ShelterRecord] = []

        for row_index in range(header_row + 1, len(table)):
            row = table.iloc[row_index]
            name = cls._optional_string(row.iloc[name_col])
            address = cls._optional_string(row.iloc[address_col])

            if not name or not address:
                continue
            if "施設名称" in name or name.startswith("※"):
                continue

            source_number = (
                cls._optional_string(row.iloc[number_col])
                if number_col is not None
                else None
            )

            supported: list[str] = []
            for disaster_key, column_index in disaster_columns.items():
                if cls._is_available_marker(row.iloc[column_index]):
                    supported.extend(cls.DISASTER_OUTPUTS[disaster_key])
            supported = list(dict.fromkeys(supported))

            designated_shelter = False
            if shelter_col is not None:
                designated_shelter = cls._is_available_marker(
                    row.iloc[shelter_col]
                )

            if designated_shelter and supported:
                facility_type = "designated_shelter_and_emergency_evacuation_site"
            elif designated_shelter:
                facility_type = "designated_shelter"
            elif supported:
                facility_type = "designated_emergency_evacuation_site"
            else:
                facility_type = "evacuation_facility"

            records.append(
                ShelterRecord(
                    id=cls._build_id(
                        ward=ward,
                        source_number=source_number,
                        name=name,
                        address=address,
                    ),
                    name=name,
                    latitude=None,
                    longitude=None,
                    address=address,
                    administrative_area=ward,
                    facility_type=facility_type,
                    supported_disasters=(
                        supported if disaster_columns else None
                    ),
                    accessibility=None,
                    capacity=None,
                    detail_url=None,
                    notes=(
                        f"source_number={source_number}"
                        if source_number
                        else None
                    ),
                )
            )

        if not records:
            raise ValueError(
                f"{ward}のExcelから避難施設レコードを抽出できませんでした。"
            )

        return records

    @staticmethod
    def _read_excel(raw: bytes, filename: str) -> pd.DataFrame:
        suffix = Path(filename).suffix.lower()
        engine = "xlrd" if suffix == ".xls" else "openpyxl"
        return pd.read_excel(
            BytesIO(raw),
            sheet_name=0,
            header=None,
            dtype=object,
            engine=engine,
        )

    @classmethod
    def _find_header_row(cls, table: pd.DataFrame) -> int:
        for row_index in range(min(len(table), 30)):
            values = [
                cls._normalize_text(value)
                for value in table.iloc[row_index].tolist()
            ]
            if any("施設名称" in value for value in values) and any(
                "所在地" in value for value in values
            ):
                return row_index
        raise ValueError("Excel内で施設名称・所在地のヘッダー行を発見できません。")

    @classmethod
    def _build_column_labels(
        cls,
        table: pd.DataFrame,
        header_row: int,
    ) -> list[str]:
        # Nagoya uses multi-row/merged headers. Combining the header row and
        # the following two rows lets us identify 洪水内水/高潮/土砂/津波 etc.
        end = min(header_row + 3, len(table))
        labels: list[str] = []

        for column_index in range(table.shape[1]):
            parts: list[str] = []
            for row_index in range(header_row, end):
                text = cls._normalize_text(table.iat[row_index, column_index])
                if text and text not in parts:
                    parts.append(text)
            labels.append("".join(parts))

        return labels

    @classmethod
    def _find_column(cls, labels: list[str], *aliases: str) -> int:
        result = cls._find_column_optional(labels, *aliases)
        if result is None:
            raise ValueError(
                "必要なExcel列を発見できません: " + " / ".join(aliases)
            )
        return result

    @classmethod
    def _find_column_optional(
        cls,
        labels: list[str],
        *aliases: str,
    ) -> int | None:
        normalized_aliases = [cls._normalize_text(alias) for alias in aliases]
        for index, label in enumerate(labels):
            normalized_label = cls._normalize_text(label)
            if any(alias in normalized_label for alias in normalized_aliases):
                return index
        return None

    @staticmethod
    def _normalize_text(value) -> str:
        if pd.isna(value):
            return ""
        return re.sub(r"\s+", "", str(value)).strip()

    @classmethod
    def _optional_string(cls, value) -> str | None:
        text = cls._normalize_text(value)
        return text or None

    @classmethod
    def _is_available_marker(cls, value) -> bool:
        text = cls._normalize_text(value)
        if not text:
            return False
        if text in {"○", "〇"}:
            return True
        if re.fullmatch(r"[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]+", text):
            return True
        if re.search(r"\d", text) and ("階" in text or text.isdigit()):
            return True
        return False

    @classmethod
    def _build_id(
        cls,
        *,
        ward: str,
        source_number: str | None,
        name: str,
        address: str,
    ) -> str:
        source_key = "|".join(
            [
                cls.REGION_CODE,
                ward,
                source_number or "",
                name,
                address,
            ]
        )
        digest = sha256(source_key.encode("utf-8")).hexdigest()[:16]
        return f"nagoya-{digest}"
