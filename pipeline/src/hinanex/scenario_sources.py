"""Scenario adapters read the SAME archived official source as shelter_location.

A handoff supplies meaning and discovery leads, never per-facility truth values.
No fuzzy-name join, geocoding, or independent hazard inference is performed.
"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from src.hinanex.adapters.edogawa_shelter import EdogawaShelterAdapter
from src.hinanex.adapters.nagoya_shelter import NagoyaShelterAdapter
from src.hinanex.adapters.niigata_shelter import NiigataShelterAdapter
from src.hinanex.models.common import NormalizedDataset
from src.hinanex.models.scenario import HazardFact, ScenarioJoinStatus

EDOGAWA_HAZARD_SOURCE = (
    "https://www.city.edogawa.tokyo.jp/"
    "e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html"
)


def edogawa_facts(location: NormalizedDataset) -> list[HazardFact]:
    """Fail closed: A found no verified cross-source join or common ID.

    The official water-disaster source has a different scope. Until D can
    safely match raw official facility rows to location records, every
    facility-level official status remains unverified, not 'not applicable'.
    """
    return [
        HazardFact(
            facility_id=record["id"],
            facility_name=record["name"],
            hazard_scope_raw="水害",
            source_semantics="水害時の待避施設・使用可能階数。洪水単独指定ではない。",
            official_status_raw=None,
            source_url=EDOGAWA_HAZARD_SOURCE,
            source_record_trace=None,
            join_status=ScenarioJoinStatus.UNVERIFIED,
            latitude=record.get("latitude"),
            longitude=record.get("longitude"),
        )
        for record in location.records
    ]


def niigata_facts(
    location: NormalizedDataset, raw: bytes,
) -> list[HazardFact]:
    """Join flood markers by the exact SAME CSV row that created the ID."""
    adapter = NiigataShelterAdapter()
    df = adapter._read_csv(raw)
    name_col = adapter._resolve_column(df, "名称", "施設名", "SAFIELD000")
    lat_col = adapter._resolve_column(df, "緯度", "latitude")
    lon_col = adapter._resolve_column(df, "経度", "longitude")
    id_col = adapter._resolve_optional_column(df, "ID", "id", "SAUID")
    hazard_col = adapter._resolve_optional_column(df, "災害種別_洪水")
    source_url = location.evidence[0].source_url if location.evidence else None
    if not source_url:
        raise ValueError("Niigata official source URL is missing from Evidence")

    result = []
    for idx, row in df.iterrows():
        name = adapter._optional_string(row[name_col]) or ""
        latitude = adapter._optional_float(row[lat_col])
        longitude = adapter._optional_float(row[lon_col])
        source_id = adapter._optional_string(row[id_col]) if id_col else None
        facility_id = adapter._build_id(
            source_id=source_id, row_index=int(idx), name=name,
            latitude=latitude, longitude=longitude,
        )
        result.append(HazardFact(
            facility_id=facility_id,
            facility_name=name,
            hazard_scope_raw="災害種別_洪水",
            source_semantics="指定緊急避難場所一覧・洪水に対応する公式災害種別列",
            official_status_raw=(
                adapter._optional_string(row[hazard_col])
                if hazard_col is not None else None
            ),
            source_url=source_url,
            source_record_trace=f"csv_row={int(idx) + 2}",
            join_status=ScenarioJoinStatus.DIRECT_SAME_SOURCE,
            latitude=latitude,
            longitude=longitude,
        ))
    _assert_same_source_ids(result, location, "niigata")
    return result


def nagoya_facts(
    location: NormalizedDataset, raw_bundle: bytes,
) -> list[HazardFact]:
    """Preserve the combined 洪水・内水 column from each of 16 indoor Excel files."""
    adapter = NagoyaShelterAdapter()
    result: list[HazardFact] = []
    with ZipFile(BytesIO(raw_bundle)) as archive:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        for item in manifest:
            ward, url, filename = item["ward"], item["url"], item["filename"]
            table = adapter._read_excel(archive.read(filename), filename)
            head = adapter._find_header_row(table)
            labels = adapter._build_column_labels(table, head)
            name_col = adapter._find_column(labels, "施設名称")
            address_col = adapter._find_column(labels, "所在地")
            number_col = adapter._find_column_optional(labels, "番号")
            flood_col = adapter._find_column_optional(
                labels, *adapter.DISASTER_COLUMN_ALIASES["flood_inland"]
            )
            for row_index in range(head + 1, len(table)):
                row = table.iloc[row_index]
                name = adapter._optional_string(row.iloc[name_col])
                address = adapter._optional_string(row.iloc[address_col])
                if not name or not address:
                    continue
                if "施設名称" in name or name.startswith("※"):
                    continue
                number = (
                    adapter._optional_string(row.iloc[number_col])
                    if number_col is not None else None
                )
                facility_id = adapter._build_id(
                    ward=ward, source_number=number, name=name, address=address,
                )
                value = (
                    adapter._optional_string(row.iloc[flood_col])
                    if flood_col is not None else None
                )
                result.append(HazardFact(
                    facility_id=facility_id,
                    facility_name=name,
                    hazard_scope_raw="洪水・内水",
                    source_semantics=(
                        "16区屋内施設・指定緊急避難場所の洪水・内水結合列。"
                        "洪水と内水を別々に判定していない。"
                    ),
                    official_status_raw=value,
                    usable_floor_raw=(
                        value if value is not None
                        and any(char in value for char in "①②③④⑤⑥⑦⑧⑨⑩階")
                        else None
                    ),
                    source_url=url,
                    source_record_trace=(
                        f"file={filename};sheet=0;excel_row={row_index + 1}"
                    ),
                    join_status=ScenarioJoinStatus.DIRECT_SAME_SOURCE,
                    latitude=None,
                    longitude=None,
                ))
    _assert_same_source_ids(result, location, "nagoya")
    return result


def _assert_same_source_ids(
    facts: list[HazardFact], location: NormalizedDataset, region: str,
) -> None:
    location_ids = [record["id"] for record in location.records]
    fact_ids = [fact.facility_id for fact in facts]
    if (
        len(fact_ids) != len(location_ids)
        or len(set(fact_ids)) != len(fact_ids)
        or set(fact_ids) != set(location_ids)
    ):
        raise ValueError(
            f"{region}: exact same-source facility IDs differ; "
            "do not silently substitute a fuzzy join"
        )
