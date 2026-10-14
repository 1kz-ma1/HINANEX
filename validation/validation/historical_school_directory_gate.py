#!/usr/bin/env python3
"""C source chronology audit for candidate historical Edogawa school directories.

This is NOT a 2019 school roster join, release-date certification or replay
authorization. A printed month, catalog date or a prior edition is never
automatically upgraded to approved 2019 school/shelter input.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sys

SCHEMA = "hinanex.a.edogawa_historical_school_roster_candidates.v0.1"
EVENT = "2019-typhoon19-edogawa"
EXPECTED_SOURCES = {
    "tokyo-2017-junior-high-open-data": {
        "url": "https://spec.api.metro.tokyo.lg.jp/spec/t000021d1700000002-c0aa9217b65291115b9a588fc71b0c81-0?lang=en",
        "after": False, "precision": "CATALOG_METADATA_DAY_ONLY_NOT_ORIGINAL_RELEASE",
        "start":"2018-03-30","end":"2018-03-30",
    },
    "tokyo-2018-school-directory-print": {
        "url":"https://www.library.metro.tokyo.lg.jp/search/research_guide/tokyo/monthly/202103/index.html",
        "after":False,"precision":"MONTH_ONLY_LIBRARY_BIBLIOGRAPHY",
        "start":"2018-10-01","end":"2018-10-31",
    },
    "tokyo-2019-school-directory-print": {
        "url":"https://www.library.metro.tokyo.lg.jp/search/research_guide/tokyo/monthly/202103/index.html",
        "after":False,"precision":"MONTH_ONLY_LIBRARY_BIBLIOGRAPHY",
        "start":"2019-10-01","end":"2019-10-31",
    },
    "edogawa-2019-nov-school-placement": {
        "url":"https://www.city.edogawa.tokyo.jp/documents/8888/r1gakkoutekiseihaitinokanngaekata.pdf",
        "after":True,"precision":"MONTH_ONLY_PRINTED_IN_SOURCE",
        "start":"2019-11-01","end":"2019-11-30",
    },
}


class SchoolRosterAuditError(ValueError):
    pass


def parse_asof(value):
    if not isinstance(value, str):
        raise SchoolRosterAuditError("missing explicit as-of JST timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SchoolRosterAuditError("invalid as-of time") from exc
    if parsed.utcoffset() != timedelta(hours=9):
        raise SchoolRosterAuditError("as-of must be explicit +09:00 JST")
    if parsed.date().isoformat() != "2019-10-12":
        raise SchoolRosterAuditError("this case only covers 2019-10-12")
    return parsed


def parse_date(s: str) -> date:
    if not isinstance(s, str) or len(s) != 10:
        raise SchoolRosterAuditError("invalid bounded publication day")
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise SchoolRosterAuditError("impossible publication day") from exc


def assess(ledger: dict) -> dict:
    if ledger.get("schema_id") != SCHEMA or ledger.get("case_id") != EVENT:
        raise SchoolRosterAuditError("unknown school roster contract/event")
    if (ledger.get("input_asof_approved_count") != 0 or
        ledger.get("approved_physical_site_pairs") != 0):
        raise SchoolRosterAuditError("unverified source attempts input/site approval")
    cutoff = parse_asof(ledger.get("as_of_jst"))
    candidates = ledger.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != len(EXPECTED_SOURCES):
        raise SchoolRosterAuditError("unexpected candidate count")
    seen=set()
    decisions=[]
    for item in candidates:
        sid=item.get("source_id")
        if sid in seen or sid not in EXPECTED_SOURCES:
            raise SchoolRosterAuditError("duplicate/unexpected official candidate")
        seen.add(sid)
        anchor=EXPECTED_SOURCES[sid]
        if (item.get("catalogue_url")!=anchor["url"] or
            item.get("publication_interval_jst",{}).get("precision")!=anchor["precision"] or
            item.get("publication_interval_jst",{}).get("not_before")!=anchor["start"] or
            item.get("publication_interval_jst",{}).get("not_after")!=anchor["end"]):
            raise SchoolRosterAuditError("independent source identifier/period contradicts catalog evidence")
        lo=parse_date(anchor["start"])
        hi=parse_date(anchor["end"])
        if lo>hi:
            raise SchoolRosterAuditError("publication interval inverted")
        if (item.get("historical_asof_approved") is not False or
            item.get("raw_sha256") is not None or
            item.get("physical_site_ids_approved") != 0 or
            item.get("source_contents_snapshot_verified") is not False or
            item.get("source_2019_temporal_continuity_verified") is not False):
            raise SchoolRosterAuditError("false approval, original digest or site continuity")
        reason=["OFFICIAL_ORIGINAL_BYTES_UNPINNED",
                "C_HUMAN_HISTORICAL_VERSION_REVIEW_REQUIRED",
                "2019_FACILITY_IDENTITY_AND_ADDRESS_NOT_APPROVED"]
        if hi < cutoff.date():
            # A DATE-ONLY or MONTH-ONLY record completely before Oct 12 still
            # does not prove today's bytes match that old published edition.
            temporal="PRIOR_PERIOD_CATALOGUED__VERSION_NOT_VERIFIED"
            reason.append("HISTORICAL_VERSION_AND_2019_CONTINUITY_UNVERIFIED")
            if sid.startswith("tokyo-2017"):
                reason.append("OLDER_2017_SCHOOL_ROSTER_STALENESS")
        elif lo > cutoff.date():
            temporal="AFTER_ASOF__REFERENCE_ONLY"
            reason.append("POST_EVENT_PUBLICATION")
        else:
            temporal="WINDOW_SPANS_ASOF__PUBLICATION_INSTANT_UNKNOWN"
            reason.append("DATE_WINDOW_OVERLAPS_DISASTER")
        decisions.append({
            "source_id":sid,
            "temporal_evidence_state":temporal,
            "replay_input_state":"BLOCKED",
            "reason_codes":reason,
            "approved_physical_site_id":None,
            "2019_asof_source_approved":False,
            "prediction_accuracy_evaluated":False,
        })
    if seen!=set(EXPECTED_SOURCES):
        raise SchoolRosterAuditError("source catalogue incomplete")
    return {
        "schema_id":"hinanex.c.historical_school_directory_temporal_gate.v0.1",
        "case_id":EVENT,"as_of_jst":ledger["as_of_jst"],
        "status":"BLOCKED_ALL__NO_2019_ASOF_INPUT_APPROVED",
        "candidates_checked":len(decisions),
        "eligible_historical_input_source_ids":[],
        "approved_facility_identity_pairs":0,
        "predictive_match_or_mismatch_approved":False,
        "decisions":decisions,
        "human_C_release_version_review_required":True,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ledger",type=Path,required=True)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    try:
        data=assess(json.loads(args.ledger.read_text(encoding="utf-8")))
        if args.out:
            if args.out.exists():
                raise SchoolRosterAuditError("refuse to overwrite independent C report")
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(data,ensure_ascii=False,indent=2))
        return 2  # All real source candidates currently BLOCKED.
    except (SchoolRosterAuditError, OSError, ValueError, AttributeError, TypeError) as exc:
        print("C_SCHOOL_ROSTER_ASOF_ERROR: "+str(exc),file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
