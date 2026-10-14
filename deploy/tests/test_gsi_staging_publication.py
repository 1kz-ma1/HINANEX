"""Offline tests for source-verified Render GSI publication. All data synthetic."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from deploy.build_staging import build_bundle
from deploy.publish_gsi_staging import GsiPublicationBlocked, build_official_reference_tile, official_source_url
from deploy.tests.test_build_staging import StagingBuildTests

SOURCE=official_source_url(10,909,403)
SAMPLE={
 "type":"FeatureCollection",
 "features":[{"type":"Feature",
   "geometry":{"type":"Point","coordinates":[139.89,35.705]},
   "properties":{"name":"SYNTHETIC ONLY","address":"test value, not official",
                 "remarks":None,"disaster1":1}}]
}
RAW=json.dumps(SAMPLE,separators=(",",":")).encode("utf-8")
class Response:
 def __init__(self,url,data,status=200,final=None):
  self.url=url;self.data=data;self.status=status;self.final=final or url
  self.headers={"Content-Type":"application/geo+json"}
 def __enter__(self):return self
 def __exit__(self,*args):return False
 def getcode(self):return self.status
 def geturl(self):return self.final
 def read(self,n=None):return self.data[:n]
class Opener:
 def __init__(self,samples=(RAW,RAW),status=200,final=None):
  self.samples=samples;self.status=status;self.final=final;self.calls=[]
 def __call__(self,request,timeout):
  self.calls.append(request.full_url)
  idx=min(len(self.calls)-1,len(self.samples)-1)
  return Response(request.full_url,self.samples[idx],self.status,self.final)

class VerifiedGsiStagingTests(unittest.TestCase):
 def test_two_independent_downloads_and_c_d_e_checks_before_publication(self):
  with tempfile.TemporaryDirectory() as tmp:
   opener=Opener();out=Path(tmp)/"gsi"
   result=build_official_reference_tile(out,region_code="13123",
                   z=10,x=909,y=403,opener=opener)
   self.assertEqual(opener.calls,[SOURCE,SOURCE])
   self.assertEqual(result["status"],"C_AND_HTTPS_VERIFIED_REFERENCE_ONLY")
   path=out/"13123"/"10-909-403.json"
   catalog=json.loads(path.read_text())
   self.assertEqual(catalog["status"],"REFERENCE_ONLY")
   self.assertEqual(catalog["source_status"],"C_ACCEPTED")
   self.assertEqual(catalog["https_provenance_status"],"MATCH")
   self.assertEqual(catalog["sites"][0]["source_record_trace"],"feature_index=0")
   self.assertEqual(catalog["sites"][0]["disaster1_raw"],1)
   self.assertFalse(list(out.rglob("*.tmp")))
   with self.assertRaisesRegex(GsiPublicationBlocked,"overwrite"):
    build_official_reference_tile(out,region_code="13123",z=10,x=909,y=403,opener=Opener())
 def test_unverified_source_never_creates_publication(self):
  altered=json.loads(json.dumps(SAMPLE))
  altered["features"][0]["properties"]["disaster1"]=0
  broken=json.dumps(altered).encode()
  for opener in (Opener((RAW,RAW+b" ")),Opener((broken,broken)),
                 Opener(final="https://evil.invalid/fake"),Opener(status=404),
                 Opener(samples=(b"",b""))):
   with self.subTest(opener=opener.__dict__),tempfile.TemporaryDirectory() as tmp:
    out=Path(tmp)/"gsi"
    with self.assertRaises(ValueError):
     build_official_reference_tile(out,region_code="13123",z=10,x=909,y=403,opener=opener)
    self.assertFalse(list(out.rglob("*.json")))
 def test_tile_must_be_explicitly_reviewed(self):
  with tempfile.TemporaryDirectory() as tmp:
   opener=Opener()
   for region,z,x,y in (("15100",10,909,403),("13123",10,910,403),
                        ("13123",11,909,403),("99999",10,909,403)):
    with self.assertRaises(GsiPublicationBlocked):
     build_official_reference_tile(Path(tmp),region_code=region,z=z,x=x,y=y,opener=opener)
   self.assertEqual(opener.calls,[])
 def test_build_adds_c_validated_tile_and_manifest(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);StagingBuildTests().make_repo(root);dist=root/"deploy"/"dist"
   build_bundle(root,dist,run_pipeline=False,publish_official_gsi=True,gsi_opener=Opener())
   meta=json.loads((dist/"_staging.json").read_text())
   self.assertEqual(meta["gsi_reference_publication"]["status"],"PARTIAL_VERIFIED_REFERENCE_ONLY")
   self.assertTrue((dist/"pipeline"/"data"/"output"/"gsi_verified_tiles"/"13123"/"10-909-403.json").is_file())
 def test_unsafe_live_source_keeps_d_and_c_but_no_reference_json(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);StagingBuildTests().make_repo(root);dist=root/"deploy"/"dist"
   build_bundle(root,dist,run_pipeline=False,publish_official_gsi=True,
                gsi_opener=Opener((RAW,RAW+b" ")))
   meta=json.loads((dist/"_staging.json").read_text())
   self.assertEqual(meta["gsi_reference_publication"]["status"],"BLOCKED_UNVERIFIED_SOURCE")
   self.assertFalse(list((dist/"pipeline"/"data"/"output").rglob("10-909-403.json")))
   self.assertTrue((dist/"evidence"/"2019_edogawa_evidence_cases.json").is_file())
 def test_offline_without_opt_in_never_requests_official(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);StagingBuildTests().make_repo(root);dist=root/"deploy"/"dist"
   build_bundle(root,dist,run_pipeline=False)
   self.assertEqual(json.loads((dist/"_staging.json").read_text())
                    ["gsi_reference_publication"]["status"],"NOT_REQUESTED")

if __name__=="__main__":unittest.main()
