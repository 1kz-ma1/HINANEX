"""Offline C review-only GSI emergency CSV to skhb02 GeoJSON comparison.

Exact names/addresses/coordinates do not authenticate source versions, approve
common-ID binding, prove an entrance or authorize emergency navigation.
"""
import argparse
import csv
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import io
import json
from pathlib import Path
import sys

URL="https://cyberjapandata.gsi.go.jp/xyz/skhb02/10/909/403.geojson"
CITY="千葉県市川市"
SCOPES={"national":17,"municipality":16,"prefecture":16}
MAX_CSV=24_000_000
MAX_GSI=12_000_000

def _hash(raw, expected, label, limit):
    if type(raw) is not bytes or not 0 < len(raw) <= limit:
        raise ValueError(label+"_RAW_INVALID")
    digest=sha256(raw).hexdigest()
    if type(expected) is not str or digest!=expected:
        raise ValueError(label+"_HASH_MISMATCH")
    return digest

def _decimal(raw, lower, upper):
    if raw == "":
        return None
    try:
        n=Decimal(raw)
    except (InvalidOperation, TypeError) as e:
        raise ValueError("CSV_COORD_INVALID") from e
    if not n.is_finite() or not lower<=n<=upper:
        raise ValueError("CSV_COORD_INVALID")
    return n

def _csv_city_candidates(raw, scope, encoding):
    if scope not in SCOPES or encoding not in ("utf-8-sig","cp932"):
        raise ValueError("CSV_SCOPE_OR_ENCODING_INVALID")
    try:
        lines=list(csv.reader(io.StringIO(raw.decode(encoding),newline=""),strict=True))
    except (UnicodeError,csv.Error) as e:
        raise ValueError("CSV_UNREADABLE") from e
    ncol=SCOPES[scope]
    if lines and lines[0][0].strip().upper()=="NO":
        if len(lines[0]) != ncol or "共通ID" not in lines[0][1]:
            raise ValueError("CSV_WRONG_HEADER")
        lines=lines[1:]
    if not 0 < len(lines) <= 200000:
        raise ValueError("CSV_ROW_COUNT_INVALID")
    candidates=[]
    for index,line in enumerate(lines):
        if len(line)!=ncol:
            raise ValueError("CSV_COLUMN_COUNT_INVALID")
        shift=1 if scope=="national" else 0
        if not line[0].strip().isascii() or not line[0].strip().isdigit():
            raise ValueError("CSV_NO_INVALID")
        marker=line[5+shift]
        if any(c not in ("","1") for c in line[4+shift:12+shift]):
            raise ValueError("CSV_HAZARD_MARKER_INVALID")
        if len(line[1])>128 or any(c in line[1] for c in ("\n","\r","\x00")):
            raise ValueError("CSV_COMMON_ID_INVALID")
        name,address=line[2+shift],line[3+shift]
        if not name.strip() or len(address)>2000:
            raise ValueError("CSV_NAME_OR_ADDRESS_INVALID")
        lat=_decimal(line[13+shift],-90,90)
        lon=_decimal(line[14+shift],-180,180)
        if (lat is None)!=(lon is None):
            raise ValueError("CSV_PARTIAL_COORDINATES")
        if scope=="national":
            if line[2]!=CITY:
                continue
        elif not address.startswith(CITY):
            continue
        candidates.append({
            "row_index":index,"name":name,"address":address,
            "common_id_raw":line[1] or None,
            "landslide_marker":marker,
            "latitude":lat,"longitude":lon,
        })
    return candidates,len(lines)

def compare_gsi_origins(gsi_raw,csv_raw,*,expected_gsi_sha256,expected_csv_sha256,
                        scope="national",encoding="utf-8-sig"):
    ghash=_hash(gsi_raw,expected_gsi_sha256,"GSI",MAX_GSI)
    chash=_hash(csv_raw,expected_csv_sha256,"CSV",MAX_CSV)
    try:
        gsi=json.loads(gsi_raw.decode("utf-8-sig"))
    except (UnicodeError,ValueError) as e:
        raise ValueError("GSI_JSON_INVALID") from e
    if not isinstance(gsi,dict) or gsi.get("type")!="FeatureCollection" or not isinstance(gsi.get("features"),list):
        raise ValueError("GSI_FEATURE_COLLECTION_INVALID")
    options,all_count=_csv_city_candidates(csv_raw,scope,encoding)
    by_name={}
    for c in options:
        by_name.setdefault(c["name"],[]).append(c)
    rows=[]
    counts={}
    for idx,feat in enumerate(gsi["features"]):
        if not isinstance(feat,dict) or feat.get("type")!="Feature":
            raise ValueError("GSI_FEATURE_INVALID")
        p,g=feat.get("properties"),feat.get("geometry")
        if not isinstance(p,dict) or not isinstance(g,dict) or g.get("type")!="Point":
            raise ValueError("GSI_POINT_INVALID")
        address=p.get("address")
        if not isinstance(address,str) or not address.startswith(CITY):
            continue
        if type(p.get("disaster2")) is not int or p["disaster2"]!=1:
            raise ValueError("GSI_LANDSLIDE_MARKER_INVALID")
        name=p.get("name")
        xy=g.get("coordinates")
        if not isinstance(name,str) or not name.strip() or not isinstance(xy,list) or len(xy) not in (2,3):
            raise ValueError("GSI_NAME_OR_COORD_INVALID")
        try:
            lon,lat=Decimal(str(xy[0])),Decimal(str(xy[1]))
        except InvalidOperation as e:
            raise ValueError("GSI_COORD_INVALID") from e
        if not lon.is_finite() or not lat.is_finite() or not -180<=lon<=180 or not -90<=lat<=90:
            raise ValueError("GSI_COORD_INVALID")
        cand=by_name.get(name,[])
        if not cand:
            decision="NO_SAME_NAME_CSV_RECORD_UNKNOWN"
        elif len(cand)!=1:
            decision="MULTIPLE_SAME_NAME_CSV_RECORDS"
        elif cand[0]["landslide_marker"]!="1":
            decision="CSV_LANDSLIDE_MARKER_DISAGREES"
        elif cand[0]["address"]!=address:
            decision="NAME_AGREES_ADDRESS_DIFFERS"
        elif cand[0]["longitude"] is None:
            decision="CSV_COORDINATES_UNKNOWN"
        elif cand[0]["longitude"]!=lon or cand[0]["latitude"]!=lat:
            decision="NAME_ADDRESS_AGREE_COORDINATES_DIFFER"
        else:
            decision="TEXT_AND_COORDINATES_AGREE_UNAPPROVED"
        counts[decision]=counts.get(decision,0)+1
        rows.append({
            "gsi_feature_index":idx,"gsi_name_raw":name,
            "gsi_address_raw":address,"gsi_point_raw":xy[:2],
            "classification":decision,"csv_same_name_candidate_count":len(cand),
            "csv_candidates":[{
                "csv_row_index":x["row_index"],"common_id_raw_unbound":x["common_id_raw"],
                "name":x["name"],"address":x["address"],
                "landslide_marker":x["landslide_marker"],
                "latitude_raw":str(x["latitude"]) if x["latitude"] is not None else None,
                "longitude_raw":str(x["longitude"]) if x["longitude"] is not None else None,
            } for x in cand],
            "common_id_bound_to_gsi_geojson":False,
            "facility_identity_approved":False,
            "navigation_endpoint":None,"navigation_allowed":False,
        })
    return {
        "status":"C_GSI_CSV_GEOJSON_CANDIDATES_UNAPPROVED",
        "gsi_sha256":ghash,"csv_sha256":chash,
        "gsi_tile_feature_count":len(gsi["features"]),
        "gsi_city_address_prefix_count":len(rows),
        "csv_scope":scope,"csv_total_rows":all_count,"csv_city_rows":len(options),
        "classifications":counts,
        "official_csv_acquisition_authenticated":False,
        "same_source_version_proven":False,
        "municipality_boundary_verified":False,
        "common_id_to_geojson_verified":False,
        "human_c_approved":False,
        "navigation_allowed_count":0,"safe_destinations_approved":0,
        "rows":rows,
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gsi-raw",required=True,type=Path)
    ap.add_argument("--csv-raw",required=True,type=Path)
    ap.add_argument("--expected-gsi-sha256",required=True)
    ap.add_argument("--expected-csv-sha256",required=True)
    ap.add_argument("--csv-scope",choices=sorted(SCOPES),required=True)
    ap.add_argument("--csv-encoding",choices=["utf-8-sig","cp932"],default="utf-8-sig")
    ap.add_argument("--out",required=True,type=Path)
    args=ap.parse_args()
    try:
        if args.out.exists() or args.out.is_symlink():
            raise ValueError("OUTPUT_ALREADY_EXISTS")
        if args.gsi_raw.stat().st_size>MAX_GSI or args.csv_raw.stat().st_size>MAX_CSV:
            raise ValueError("INPUT_TOO_LARGE")
        result=compare_gsi_origins(
            args.gsi_raw.read_bytes(),args.csv_raw.read_bytes(),
            expected_gsi_sha256=args.expected_gsi_sha256,
            expected_csv_sha256=args.expected_csv_sha256,
            scope=args.csv_scope,encoding=args.csv_encoding,
        )
        args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"status":result["status"],"classifications":result["classifications"],
                          "human_c_approved":False,"navigation_allowed_count":0},ensure_ascii=False))
        return 0
    except (ValueError,OSError,TypeError) as e:
        print("C CSV REPLAY BLOCKED: "+str(e),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
