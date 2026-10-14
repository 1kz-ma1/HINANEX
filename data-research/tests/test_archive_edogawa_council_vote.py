"""A offline tests: vote is on bill #64 row, never evidence of an open site."""
import importlib.util
from datetime import datetime,timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

path=Path(__file__).resolve().parents[1]/"tools"/"archive_edogawa_council_vote.py"
sp=importlib.util.spec_from_file_location("council_vote",path)
a=importlib.util.module_from_spec(sp)
sp.loader.exec_module(a)


def fixture(*, wrong_decision=False, other_bill_approved=False):
    row64=("<tr><td>議案第64号</td><td>旧下鎌田小学校校舎等解体工事請負契約</td>"
           "<td>令和8年7月1日 "+("否決" if wrong_decision else "可決")+" 全会一致</td></tr>")
    if other_bill_approved:
        row64=row64.replace(" 可決 全会一致"," 否決 賛成少数")
    html=("<html><body><table><tr><td>議案第63号</td><td>可決 全会一致</td></tr>"
          + row64 +
          "<tr><td>議案第65号</td><td>可決 全会一致</td></tr></table></body></html>")
    return html.encode("utf-8")


def capture(folder,raw=None):
    return a.capture(folder,fetch=lambda:(raw or fixture(),a.OFFICIAL_URL,{"content_type":"text/html"}),
                     now=datetime(2026,10,13,tzinfo=timezone.utc))


class VoteTests(unittest.TestCase):
    def test_exact_bill_row_and_unknown_site(self):
        with TemporaryDirectory() as root:
            p=Path(root)/"source"
            m=capture(p)
            z=a.verify(p)
            self.assertEqual(z["official_vote_result_from_row"],"可決")
            self.assertEqual(z["site_current_opening"],"UNKNOWN")
            self.assertFalse(m["vote_is_a_demolition_completion_record"])

    def test_previous_bill_vote_cannot_be_transferred(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(a.SourceError,"attribute official approved vote"):
                capture(Path(root)/"source",fixture(wrong_decision=True))

    def test_tampering_original_fails_digest(self):
        with TemporaryDirectory() as root:
            p=Path(root)/"source"
            capture(p)
            f=p/a.FILENAME
            f.write_bytes(f.read_bytes()+b" ")
            with self.assertRaisesRegex(a.SourceError,"SHA256 changed"):
                a.verify(p)

    def test_fake_demolition_completion_fails(self):
        with TemporaryDirectory() as root:
            p=Path(root)/"source"
            m=capture(p)
            m["vote_is_a_demolition_completion_record"]=True
            (p/"vote_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaisesRegex(a.SourceError,"no-approval"):
                a.verify(p)

    def test_fake_flood_promotions_fail(self):
        with TemporaryDirectory() as root:
            p=Path(root)/"source"
            m=capture(p)
            m["flood_classifications_added"]=1
            (p/"vote_manifest_UNAPPROVED.json").write_text(json.dumps(m))
            with self.assertRaises(a.SourceError):
                a.verify(p)

    def test_source_redirected_off_host_fail(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(a.SourceError,"Council origin"):
                a.capture(Path(root)/"source",
                          fetch=lambda:(fixture(),"https://example.org/g07_giketsu.asp",{}))

    def test_cannot_overwrite_source(self):
        with TemporaryDirectory() as root:
            p=Path(root)/"source"
            capture(p)
            with self.assertRaisesRegex(a.SourceError,"new/empty"):
                capture(p)


if __name__=="__main__":
    unittest.main()
