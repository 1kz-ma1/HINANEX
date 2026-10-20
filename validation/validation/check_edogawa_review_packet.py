"""C-only structural checkpoint for HUMAN review records on Edogawa snapshots.

This NEVER verifies reviewer identity, performs physical-site joins, or grants D
promotion. The original comparator, archive verifier, and C->D acceptance
process remain separate. No network access; all original raw data stays private.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

SOURCE_KEYS = frozenset({
    'water_facilities', 'municipal_locations', 'municipal_school_list',
    'municipal_primary_school_list', 'municipal_2025_school_relocation',
    'tokyo_kasaikoka_school_access', 'kanto_ichiko_school_overview',
})
REVIEW_IDS = (
    'C-SITE-OLD-NEW', 'C-MUNICIPAL-CROSSSOURCE', 'C-GSI-FLOOD-SEPARATION',
)
STATUS = frozenset({'PENDING', 'DOCUMENTED', 'NEEDS_FOLLOWUP'})
SHA = re.compile(r'^[0-9a-f]{64}$')
REPO_SHA = re.compile(r'^[0-9a-f]{40}$')


class ReviewPacketError(ValueError):
    """Inconsistent provenance or incomplete review documentation."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ReviewPacketError(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def json_file(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    data = json.loads(raw)
    require(type(data) is dict, f'{path.name}: root must be an object')
    return data, sha(raw)


def snapshot_and_receipt(report_path: Path, receipt_path: Path) -> tuple[dict, dict, str, str]:
    report, rhash = json_file(report_path)
    receipt, ehash = json_file(receipt_path)
    require(report.get('status') == 'SOURCE_BYTES_CHANGED_REVIEW_REQUIRED', 'unexpected formal C status')
    rows = report.get('sources')
    require(type(rows) is list and len(rows) == 7, 'formal C source count must be seven')
    require({x.get('source_key') for x in rows if isinstance(x, dict)} == SOURCE_KEYS,
            'formal C source keys/duplicates incorrect')
    require(type(report.get('official_source_count')) is int and report['official_source_count'] == 7,
            'formal source count invalid')
    changed = [x['source_key'] for x in rows if x.get('raw_bytes_changed') is True]
    require(report.get('changed_source_count') == len(changed)
            and report.get('changed_source_keys') == changed,
            'formal source delta inconsistent')
    require(report.get('source_revision_human_review_completed') is False
            and report.get('physical_site_identity_human_review_completed') is False
            and report.get('approved_cross_source_pairs') == 0
            and report.get('flood_scenario_classifications_added') == 0,
            'formal C input incorrectly asserts human acceptance')
    for item in rows:
        key = item['source_key']
        for field in ('previous_sha256', 'current_sha256'):
            require(type(item.get(field)) is str and SHA.fullmatch(item[field]) is not None,
                    f'bad hash {key}:{field}')
        actual_change = item['previous_sha256'] != item['current_sha256']
        require(item.get('raw_bytes_changed') is actual_change, f'delta/hash mismatch for {key}')
        require(item.get('human_source_revision_review_required') is actual_change,
                f'revision review flag inconsistent for {key}')
        require(item.get('same_physical_facility_approved') is False
                and item.get('official_publication_or_effective_date') is None,
                f'unsupported human/source-date approval {key}')
        url = item.get('requested_url')
        require(type(url) is str and urlsplit(url).scheme == 'https'
                and bool(urlsplit(url).netloc), f'expected official HTTPS URL for {key}')
    require(receipt.get('comparison_report_sha256') == rhash,
            'operator receipt does not hash-match the actual formal report bytes')
    require(receipt.get('cli_relative_path') == 'validation/validation/compare_edogawa_source_snapshots.py',
            'unexpected C CLI path')
    require(type(receipt.get('pinned_git_head')) is str
            and REPO_SHA.fullmatch(receipt['pinned_git_head']) is not None,
            'missing pinned Git commit SHA')
    require(receipt.get('old_run') == 38505232094 and receipt.get('new_run') == 38857462945,
            'unexpected source run IDs')
    require(receipt.get('human_source_revision_approved') is False
            and receipt.get('human_physical_site_identity_approved') is False,
            'operator receipt asserts unsupported human approval')
    for field in ('old_artifact_sha256', 'new_artifact_sha256'):
        require(type(receipt.get(field)) is str and SHA.fullmatch(receipt[field]) is not None,
                f'{field} malformed')
    require(receipt.get('raw_archive_inputs_outside_git') is True,
            'receipt lacks original input separation')
    return report, receipt, rhash, ehash


def decision_template(identifier: str) -> dict:
    return {
        'id': identifier,
        'disposition': 'PENDING',
        'reviewer': None,
        'reviewed_at_utc': None,
        'finding': None,
        'evidence_urls': [],
        'limitations': [],
    }


def make_packet(report: dict, receipt: dict, report_sha: str, receipt_sha: str) -> dict:
    """Create a PENDING record tied to the exact formal JSON and receipt bytes."""
    source_reviews = []
    for item in report['sources']:
        row = decision_template(item['source_key'])
        row.update({
            'requested_url': item['requested_url'],
            'previous_sha256': item['previous_sha256'],
            'current_sha256': item['current_sha256'],
            'raw_bytes_changed': item['raw_bytes_changed'],
        })
        source_reviews.append(row)
    return {
        'schema_version': 1,
        'scope': 'C_REVIEW_DOCUMENTATION_ONLY_NO_D_AUTHORITY',
        'formal_c_report_sha256': report_sha,
        'operator_receipt_sha256': receipt_sha,
        'git_source_head_sha': receipt['pinned_git_head'],
        'source_runs': [receipt['old_run'], receipt['new_run']],
        'source_reviews': source_reviews,
        'cross_source_reviews': [decision_template(x) for x in REVIEW_IDS],
        'd_source_promotion_authorized': False,
        'approved_cross_source_pairs': 0,
        'new_flood_classifications': 0,
    }


def _check_decision(entry: dict, required_id: str, *, immutable: dict) -> bool:
    require(type(entry) is dict, f'{required_id}: review entry not an object')
    require(entry.get('id') == required_id, f'{required_id}: unexpected id')
    for k, v in immutable.items():
        require(type(entry.get(k)) is type(v) and entry.get(k) == v,
                f'{required_id}: immutable {k} changed')
    disposition = entry.get('disposition')
    require(type(disposition) is str and disposition in STATUS,
            f'{required_id}: invalid review disposition')
    reviewer, timestamp, finding = (entry.get(k) for k in ('reviewer', 'reviewed_at_utc', 'finding'))
    urls, limits = entry.get('evidence_urls'), entry.get('limitations')
    require(type(urls) is list and type(limits) is list and all(type(x) is str for x in limits),
            f'{required_id}: evidence/limitations malformed')
    if disposition == 'PENDING':
        require(reviewer is None and timestamp is None and finding is None
                and urls == [] and limits == [],
                f'{required_id}: pending entry claims filled human review')
        return False
    require(type(reviewer) is str and bool(reviewer.strip()) and reviewer not in {'AI', 'ChatGPT'},
            f'{required_id}: missing identified human reviewer')
    require(type(finding) is str and bool(finding.strip()),
            f'{required_id}: missing human finding')
    require(type(timestamp) is str, f'{required_id}: missing human review UTC time')
    try:
        moment = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ReviewPacketError(f'{required_id}: invalid review timestamp') from exc
    require(moment.tzinfo is not None and moment.utcoffset().total_seconds() == 0,
            f'{required_id}: timestamp must be UTC')
    require(len(urls) >= 1 and all(type(u) is str and urlsplit(u).scheme == 'https'
                                   and urlsplit(u).netloc for u in urls),
            f'{required_id}: evidence URLs must be HTTPS source references')
    return True


def inspect_packet(report: dict, receipt: dict, rsha: str, esha: str, packet: dict) -> dict:
    required = make_packet(report, receipt, rsha, esha)
    for key in ('schema_version', 'scope', 'formal_c_report_sha256',
                'operator_receipt_sha256', 'git_source_head_sha', 'source_runs',
                'd_source_promotion_authorized', 'approved_cross_source_pairs',
                'new_flood_classifications'):
        value = required[key]
        require(type(packet.get(key)) is type(value) and packet.get(key) == value,
                f'packet immutable field {key} does not match pinned evidence')
    rows = packet.get('source_reviews')
    other = packet.get('cross_source_reviews')
    require(type(rows) is list and len(rows) == len(required['source_reviews']),
            'source review list invalid')
    require(type(other) is list and len(other) == len(required['cross_source_reviews']),
            'cross-source review list invalid')
    completed = 0
    needs_followup = 0
    for proposed, actual in zip(required['source_reviews'], rows):
        immutable = {k: v for k, v in proposed.items() if k not in
                     {'id', 'disposition', 'reviewer', 'reviewed_at_utc',
                      'finding', 'evidence_urls', 'limitations'}}
        if _check_decision(actual, proposed['id'], immutable=immutable):
            completed += 1
            needs_followup += actual['disposition'] == 'NEEDS_FOLLOWUP'
    for proposed, actual in zip(required['cross_source_reviews'], other):
        if _check_decision(actual, proposed['id'], immutable={}):
            completed += 1
            needs_followup += actual['disposition'] == 'NEEDS_FOLLOWUP'
    return {
        'status': 'HOLD_PENDING_EXTERNAL_HUMAN_SIGNOFF',
        'review_entries_total': len(rows) + len(other),
        'review_entries_documented': completed,
        'review_entries_pending': len(rows) + len(other) - completed,
        'review_entries_need_followup': needs_followup,
        'documentation_integrity_passed': True,
        'human_identity_verified_by_software': False,
        'd_source_promotion_authorized': False,
        'new_flood_classifications': 0,
        'warning': 'Fields are unsigned assertions; structure checks never certify a human decision or permit D release.',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--formal-report', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--create-template', type=Path)
    action.add_argument('--check', type=Path)
    args = parser.parse_args()
    try:
        report, receipt, rhash, ehash = snapshot_and_receipt(args.formal_report, args.receipt)
        if args.create_template is not None:
            path = args.create_template
            repo_root = Path(__file__).resolve().parents[2]
            target = path.resolve()
            require(repo_root != target and repo_root not in target.parents,
                    'review record must be stored outside the Git checkout')
            require(not path.exists() and not path.is_symlink(), 'refusing to overwrite review record')
            packet = make_packet(report, receipt, rhash, ehash)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            result = inspect_packet(report, receipt, rhash, ehash, packet)
        else:
            packet, _ = json_file(args.check)
            result = inspect_packet(report, receipt, rhash, ehash, packet)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f'C human review document INTEGRITY FAILURE (NO APPROVAL): {exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())