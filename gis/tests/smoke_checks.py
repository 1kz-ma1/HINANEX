from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1] / "gis"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


html = (ROOT / "index.html").read_text(encoding="utf-8")
map_js = (ROOT / "js" / "map.js").read_text(encoding="utf-8")
adapter_js = (ROOT / "js" / "d_region_adapter.js").read_text(encoding="utf-8")
ref_js = (ROOT / "js" / "reference_data.js").read_text(encoding="utf-8")

for element_id in [
    "map", "mapUnavailable", "mapUnavailableMessage", "details", "status", "region", "basemap", "officialFlood", "boundary", "boundaryNote", "shelter",
    "floodOpacity", "floodOpacityValue", "resetView", "regionExportFile", "autoLoad",
    "recordCount", "mappedCount", "missingCoordinateCount", "datasetStatus", "datasetChip"
]:
    require(f'id="{element_id}"' in html, f"missing HTML id: {element_id}")

for code, key in [("13123", "edogawa"), ("15100", "niigata"), ("23100", "nagoya")]:
    require(f'"{code}"' in map_js, f"region code missing: {code}")
    require(f'../../pipeline/data/output/{key}.json' in map_js, f"D output URL missing: {key}")
    require(f'value="{code}"' in html, f"region selector option missing: {code}")

require("01_flood_l2_shinsuishin_data/{z}/{x}/{y}.png" in map_js, "official flood tile URL missing")
require("shelter_location" in adapter_js, "D shelter requirement code missing")
require('SUPPORTED_SCHEMA_VERSION = "0.9"' in adapter_js, "D contract version guard missing")
require("supported_disasters" in adapter_js, "ShelterRecord fields not aligned")
require("record.latitude" in adapter_js and "record.longitude" in adapter_js, "coordinates missing")
require("geocod" not in map_js.lower(), "map implementation must not geocode")
require("risk" not in adapter_js.lower(), "E adapter must not invent risk")
require("missingCoordinateRecords" in map_js, "missing coordinate disclosure missing")
require("setMapAvailability" in map_js, "unknown map extent guard missing")
require('getElementById("mapUnavailable")' in map_js, "map availability overlay id must match HTML")
require('window.location.protocol === "file:"' in map_js, "file:// auto-fetch guard missing")
require("autoLoadSequence" in map_js and "AbortController" in map_js, "stale auto-load guard missing")
require("safeExternalUrl" in map_js and "javascript:" not in map_js, "external detail URL guard missing")
for band in ["0.3m未満", "0.3〜0.5m未満", "0.5〜1.0m未満", "1.0〜3.0m未満", "3.0〜5.0m未満", "5.0〜10.0m未満", "10.0〜20.0m未満", "20.0m以上"]:
    require(band in html, f"official flood legend band missing: {band}")

match = re.search(r"window\.HINANEX_REFERENCE_DATA\s*=\s*(\{.*\});\s*$", ref_js, flags=re.S)
require(match, "reference data payload missing")
reference = json.loads(match.group(1))
require(reference["boundary"]["type"] == "FeatureCollection", "boundary must be FeatureCollection")
require(reference["boundary"]["features"], "boundary must contain a feature")
require(reference["boundary"]["features"][0]["properties"]["municipalityCode"] == "13123", "fixture must be scoped to Edogawa")

print("smoke_checks: OK")
