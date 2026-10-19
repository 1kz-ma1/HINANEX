"""Offline fail-closed tests for formal snapshot human review record structure.

Synthetic source refs/hashes only. Neither tests nor validator certify a human
reviewer, natural-hazard meaning, or production release authority.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from check_edogawa_review_packet import (
    SOURCE_KEYS, REVIEW_IDS, ReviewPacketError, snapshot_and_receipt,
    make_packet, inspect_packet,
)


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def synthetic_inputs(tmp):
    sources = []
    for i, key in enumerate(sorted(SOURCE_KEYS)):
        old = f'{i + 1:064x}'
        changed = key == 'tokyo_kasaikoka_school_access'
        new = f'{i + 20:064x}' if changed else old
        sources.append({
            'source_key': key,
            'requested_url': 'https://example.invalid/source/' + key,
            'previous_sha256': old,
            'current_sha256': new,
            'raw_bytes_changed': changed,
            'human_source_revision_review_required': changed,
            'same_physical_facility_approved': False,
            'official_publication_or_effective_date': None,
        })
    changed = [x['source_key'] for x in sources if x['raw_bytes_changed']]
    report = {
        'status': 'SOURCE_BYTES_CHANGED_REVIEW_REQUIRED',
        'official_source_count': 7,
        'sources': sources,
        'changed_source_count': 1,
        'changed_source_keys': changed,
        'source_revision_human_review_completed': False,
        'physical_site_identity_human_review_completed': False,
        'approved_cross_source_pairs': 0,
        'flood_scenario_classifications_added': 0,
    }
    report_file = tmp / 'formal.json'
    report_file.write_bytes(json_bytes(report))
    receipt = {
        'comparison_report_sha256': hashlib.sha256(report_file.read_bytes()).hexdigest(),
        'cli_relative_path': 'validation/validation/compare_edogawa_source_snapshots.py',
        'pinned_git_head': 'a' * 40,
        'old_run': 38505232094, 'new_run': 38857462945,
        'old_artifact_sha256': '1' * 64,
        'new_artifact_sha256': '2' * 64,
        'raw_archive_inputs_outside_git': True,
        'human_source_revision_approved': False,
        'human_physical_site_identity_approved': False,
    }
    receipt_file = tmp / 'receipt.json'
    receipt_file.write_bytes(json_bytes(receipt))
    return report_file, receipt_file


class HumanReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.report_path, self.receipt_path = synthetic_inputs(self.root)
        self.report, self.receipt, self.rsha, self.esha = snapshot_and_receipt(
            self.report_path, self.receipt_path)
        self.packet = make_packet(self.report, self.receipt, self.rsha, self.esha)

    def check(self):
        return inspect_packet(self.report, self.receipt, self.rsha, self.esha,
                              self.packet)

    def test_template_is_locked_and_requires_ten_human_decisions(self):
        status = self.check()
        self.assertEqual(status['status'], 'HOLD_PENDING_EXTERNAL_HUMAN_SIGNOFF')
        self.assertEqual(status['review_entries_total'], 10)
        self.assertEqual(status['review_entries_pending'], 10)
        self.assertFalse(status['d_source_promotion_authorized'])
        self.assertFalse(status['human_identity_verified_by_software'])
        self.assertEqual([x['id'] for x in self.packet['cross_source_reviews']], list(REVIEW_IDS))

    def test_one_well_documented_row_still_never_unlocks_D(self):
        r = self.packet['source_reviews'][0]
        r.update(disposition='DOCUMENTED', reviewer='Human reviewer A',
                 reviewed_at_utc='2026-10-19T12:00:00Z',
                 finding='Source page is not official effective-date evidence',
                 evidence_urls=['https://example.invalid/real-document'],
                 limitations=['Source metadata only'])
        status = self.check()
        self.assertEqual(status['review_entries_documented'], 1)
        self.assertFalse(status['d_source_promotion_authorized'])

    def test_all_documented_rows_still_cannot_auto_approve(self):
        for r in self.packet['source_reviews'] + self.packet['cross_source_reviews']:
            r.update(disposition='DOCUMENTED', reviewer='Human reviewer B',
                     reviewed_at_utc='2026-10-19T12:00:00+00:00',
                     finding='Evidence reviewed but no physical-site join approved',
                     evidence_urls=['https://example.invalid/official-lookup'])
        status = self.check()
        self.assertEqual(status['review_entries_documented'], 10)
        self.assertEqual(status['status'], 'HOLD_PENDING_EXTERNAL_HUMAN_SIGNOFF')

    def test_forged_D_authorization_is_rejected(self):
        for k,v in [('d_source_promotion_authorized', True),
                    ('approved_cross_source_pairs', 1),
                    ('new_flood_classifications', 1)]:
            with self.subTest(field=k):
                self.packet[k] = v
                with self.assertRaisesRegex(ReviewPacketError, 'immutable'):
                    self.check()
                self.packet[k] = make_packet(self.report, self.receipt, self.rsha, self.esha)[k]

    def test_edited_source_sha_or_source_URL_is_rejected(self):
        row = self.packet['source_reviews'][0]
        for field,value in [('previous_sha256','b'*64),('requested_url','https://not-official.invalid')]:
            old=row[field]
            row[field]=value
            with self.subTest(field=field), self.assertRaisesRegex(ReviewPacketError,'immutable'):
                self.check()
            row[field]=old

    def test_swapped_or_missing_source_ids_rejected(self):
        self.packet['source_reviews'][0],self.packet['source_reviews'][1]=(self.packet['source_reviews'][1],self.packet['source_reviews'][0])
        with self.assertRaisesRegex(ReviewPacketError,'unexpected id'):
            self.check()
        self.packet['source_reviews'].pop()
        with self.assertRaisesRegex(ReviewPacketError, 'list invalid'):
            self.check()

    def test_review_status_cannot_be_signed_by_ai_or_without_evidence(self):
        row=self.packet['source_reviews'][0]
        row['disposition']='DOCUMENTED'
        with self.assertRaisesRegex(ReviewPacketError,'missing identified'):
            self.check()
        row.update(reviewer='ChatGPT', reviewed_at_utc='2026-10-19T11:00:00Z',
                   finding='Guessed', evidence_urls=['https://example.invalid/guess'])
        with self.assertRaisesRegex(ReviewPacketError,'missing identified'):
            self.check()
        row['reviewer']='Human A'
        row['evidence_urls']=[]
        with self.assertRaisesRegex(ReviewPacketError,'evidence URLs'):
            self.check()

    def test_bad_timestamp_or_untrusted_url_fails(self):
        row=self.packet['cross_source_reviews'][0]
        row.update(disposition='DOCUMENTED', reviewer='Human C',
                   reviewed_at_utc='2026-10-19T12:00:00',
                   finding='No verified association', evidence_urls=['http://example.invalid'])
        with self.assertRaisesRegex(ReviewPacketError,'timestamp must be UTC'):
            self.check()
        row['reviewed_at_utc']='2026-10-19T12:00:00Z'
        with self.assertRaisesRegex(ReviewPacketError,'evidence URLs'):
            self.check()

    def test_formal_report_mutation_and_bad_receipt_fail(self):
        receipt = json.loads(self.receipt_path.read_text())
        receipt['comparison_report_sha256']='e'*64
        self.receipt_path.write_bytes(json_bytes(receipt))
        with self.assertRaisesRegex(ReviewPacketError,'hash-match'):
            snapshot_and_receipt(self.report_path,self.receipt_path)
        self.receipt_path.write_bytes(json_bytes(self.receipt))
        report = json.loads(self.report_path.read_text())
        report['sources'][0]['raw_bytes_changed']=not report['sources'][0]['raw_bytes_changed']
        self.report_path.write_bytes(json_bytes(report))
        receipt['comparison_report_sha256']=hashlib.sha256(self.report_path.read_bytes()).hexdigest()
        self.receipt_path.write_bytes(json_bytes(receipt))
        with self.assertRaisesRegex(ReviewPacketError,'formal source delta inconsistent|delta/hash mismatch'):
            snapshot_and_receipt(self.report_path,self.receipt_path)

    def test_review_packet_replay_cannot_switch_to_different_formal_bytes(self):
        self.packet['formal_c_report_sha256']='9'*64
        with self.assertRaisesRegex(ReviewPacketError,'immutable'):
            self.check()

    def test_pending_entry_with_ghost_reviewer_fails(self):
        self.packet['source_reviews'][0]['reviewer']='Impersonated'
        with self.assertRaisesRegex(ReviewPacketError,'pending entry'):
            self.check()


if __name__ == '__main__':
    unittest.main()