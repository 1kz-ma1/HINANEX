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
require('window.location.protocol === "file:"' in map_js, "file:// origin guard missing")
require("shortLabel" in map_js and "resetView" in map_js, "dynamic reset label missing")

match = re.search(r"window\.HINANEX_REFERENCE_DATA\s*=\s*(\{.*\});\s*$", ref_js, flags=re.S)
require(match, "reference data payload missing")
reference = json.loads(match.group(1))
require(reference["boundary"]["type"] == "FeatureCollection", "boundary must be FeatureCollection")
require(reference["boundary"]["features"], "boundary must contain a feature")
require(reference["boundary"]["features"][0]["properties"]["municipalityCode"] == "13123", "fixture must be scoped to Edogawa")

print("smoke_checks: OK")
