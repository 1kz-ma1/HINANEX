"""Synthetic GSI CSV inspection: no actual downloaded official CSV imported."""
import importlib.util
from pathlib import Path
import unittest

TOOL=Path(__file__).resolve().parents[1]/"tools"/"inspect_gsi_emergency_csv_archive.py"
spec=importlib.util.spec_from_file_location("a_gsi_csv",TOOL)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample(scope="municipality",common_id="000012345",landslide="1",name="SYNTHETIC PARK"):
    # Municipality 16 fields; national contains jurisdiction before facility name.
    row=["1",common_id]
    if scope=="national":
        row.append("千葉県市川市")
    row += [name,"千葉県市川市SYNTHETIC"]
    row += ["",landslide,"","","","","",""]  # eight disaster markers
    row += ["","35.700000","139.900000","synthetic only"]
    assert len(row)==(17 if scope=="national" else 16)
    return (",".join(row)+"\r\n").encode("utf-8")


class GsiCSVTests(unittest.TestCase):
    def test_city_id_is_raw_and_never_joined(self):
        r=mod.inspect_emergency_place_csv(sample(),"municipality")
        self.assertEqual(r["scope"],"municipality")
        self.assertEqual(r["archive_rows_count"],1)
        self.assertEqual(r["landslide_designated_rows_count"],1)
        self.assertEqual(r["rows"][0]["common_id_raw"],"000012345")
        self.assertEqual(r["rows"][0]["latitude_raw"],"35.700000")
        self.assertFalse(r["cross_source_geojson_identity_approved"])
        self.assertFalse(r["rows"][0]["geojson_feature_identity_verified"])
        self.assertFalse(r["for_disaster_use"])
        self.assertEqual(r["approved_safe_destinations"],0)

    def test_national_has_extra_municipality_column(self):
        r=mod.inspect_emergency_place_csv(sample("national"),"national")
        self.assertEqual(r["rows"][0]["municipality_name_raw"],"千葉県市川市")
        with self.assertRaisesRegex(ValueError,"COLUMNS"):
            mod.inspect_emergency_place_csv(sample("national"),"municipality")

    def test_missing_id_is_explicit_unknown(self):
        r=mod.inspect_emergency_place_csv(sample(common_id=""),"municipality")
        self.assertIsNone(r["rows"][0]["common_id_raw"])
        self.assertEqual(r["common_id_present_count"],0)

    def test_missing_hazard_marker_is_not_landlslide_designated(self):
        r=mod.inspect_emergency_place_csv(sample(landslide=""),"municipality")
        self.assertEqual(r["landslide_designated_rows_count"],0)

    def test_malformed_marker_and_coordinates_rejected(self):
        for bad in ("2","○","true"):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                mod.inspect_emergency_place_csv(sample(landslide=bad),"municipality")
        for change in ("nan","1000"):
            with self.subTest(change=change),self.assertRaises(ValueError):
                mod.inspect_emergency_place_csv(
                    sample().replace(b"35.700000",change.encode()),"municipality"
                )

    def test_wrong_scope_cannot_guess_columns(self):
        with self.assertRaisesRegex(ValueError,"COLUMNS"):
            mod.inspect_emergency_place_csv(sample(),"national")

    def test_utf8_bom_and_header_when_explicit(self):
        header=["NO","共通ID"]+["任意"]*14
        raw=("\ufeff"+",".join(header)+"\r\n").encode()+sample()
        r=mod.inspect_emergency_place_csv(raw,"municipality")
        self.assertEqual(r["archive_rows_count"],1)

    def test_duplicate_common_id_stays_unreviewed(self):
        raw=sample()+sample().replace(b"1,000012345",b"2,000012345")
        r=mod.inspect_emergency_place_csv(raw,"municipality")
        self.assertEqual(r["duplicate_common_id_values_unresolved"],["000012345"])
        self.assertFalse(r["cross_source_geojson_identity_approved"])

    def test_does_not_guess_encoding_or_wrong_type(self):
        with self.assertRaises(ValueError):
            mod.inspect_emergency_place_csv(sample(),"unknown")
        with self.assertRaises(ValueError):
            mod.inspect_emergency_place_csv(sample(), "municipality",encoding="auto")
        with self.assertRaises(ValueError):
            mod.inspect_emergency_place_csv(b"", "municipality")
        with self.assertRaises(ValueError):
            mod.inspect_emergency_place_csv(sample(landslide="2")[:-2], "municipality")
