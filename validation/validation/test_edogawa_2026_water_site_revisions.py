"""C regression: official edition provenance and approval boundaries stay closed."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from verify_edogawa_2026_water_site_revisions import FILES, AuditError, verify


def sample(directory):
    path=Path(directory)/"2026-flood"
    path.mkdir()
    items=[]
    for key,(file,url) in FILES.items():
        if file.endswith(".pdf"):
            raw=b"%PDF-1.7\n"+b"% placeholder PDF for mocked text stage\n"*7+b"%%EOF\n"
        else:
            raw=("<html><body>"+"統廃合後の学校後利用 旧下鎌田小学校 "*5+
                 "</body></html>").encode()
        (path/file).write_bytes(raw)
        items.append({
            "source_key":key, "filename":file,"format":"pdf" if file.endswith(".pdf") else "html",
            "requested_url":url,"final_url":url,"date_scope_independent_review_required":True,
            "size":len(raw),"sha256":sha256(raw).hexdigest()
        })
    manifest={
        "purpose":"A_EDOGAWA_2026_EXTERNAL_INTERNAL_WATER_SITE_ORIGINALS_UNAPPROVED",
        "captured_at_utc":datetime(2026,10,13,tzinfo=timezone.utc).isoformat(),
        "pdf_content_manually_signed_off":False,
        "as_of_date_never_proves_current_opening":True,
        "pdf_originals_are_distinct_from_prior_water_html":True,
        "school_building_or_premises_identity_human_approved":False,
        "official_document_effective_date_human_approved":False,
        "external_vs_internal_flood_semantics_human_approved":False,
        "campus_to_d_identity_human_approved":False,
        "human_c_site_pairs_approved":0,
        "new_flood_scenario_classifications":0,
        "source_items":items
    }
    (path/"site_revisions_manifest_UNAPPROVED.json").write_text(json.dumps(manifest))
    return path,manifest


class OfficialFloodSiteVersionCTests(unittest.TestCase):
    def run_with_mocked_pdf_content(self,p):
        with patch("verify_edogawa_2026_water_site_revisions.pdf_context",
                   return_value={"source_content_for_human":True}):
            return verify(p)

    def test_three_official_sources_never_accept_facility(self):
        with TemporaryDirectory() as temp:
            p,_=sample(temp)
            a=self.run_with_mocked_pdf_content(p)
            self.assertEqual(a["original_sources_independently_reviewed"],3)
            self.assertEqual(a["C_approved_physical_site_pairs"],0)
            self.assertEqual(a["D_flood_classifications_added"],0)

    def test_mutated_pdf_sha_rejected(self):
        with TemporaryDirectory() as temp:
            p,_=sample(temp)
            path=p/"2026_disaster_plan_external_internal_water.pdf"
            path.write_bytes(path.read_bytes()+b"tampered")
            with self.assertRaisesRegex(AuditError,"SHA256 changed"):
                self.run_with_mocked_pdf_content(p)

    def test_false_human_approval_rejected(self):
        with TemporaryDirectory() as temp:
            p,m=sample(temp)
            m["campus_to_d_identity_human_approved"]=True
            (p/"site_revisions_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(AuditError,"unsanctioned human approval"):
                self.run_with_mocked_pdf_content(p)

    def test_false_flood_promotion_rejected(self):
        with TemporaryDirectory() as temp:
            p,m=sample(temp)
            m["new_flood_scenario_classifications"]=1
            (p/"site_revisions_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaises(AuditError):
                self.run_with_mocked_pdf_content(p)

    def test_redirect_to_unapproved_city_subpage_rejected(self):
        with TemporaryDirectory() as temp:
            p,m=sample(temp)
            m["source_items"][0]["final_url"]=m["source_items"][2]["final_url"]
            (p/"site_revisions_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(AuditError,"source URI or edition substitution|URL or edition substitution"):
                self.run_with_mocked_pdf_content(p)

    def test_missing_source_document_rejected(self):
        with TemporaryDirectory() as temp:
            p,_=sample(temp)
            (p/"2025_old_shimokamata_afteruse.pdf").unlink()
            with self.assertRaisesRegex(AuditError,"set differs"):
                self.run_with_mocked_pdf_content(p)

    def test_duplicate_source_key_rejected(self):
        with TemporaryDirectory() as temp:
            p,m=sample(temp)
            m["source_items"][1]["source_key"]=m["source_items"][0]["source_key"]
            (p/"site_revisions_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaises(AuditError):
                self.run_with_mocked_pdf_content(p)


if __name__=="__main__":
    unittest.main()
