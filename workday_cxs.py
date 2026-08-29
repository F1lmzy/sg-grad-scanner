#!/usr/bin/env python3
"""Query Workday career-site JSON API (CXS). Auto-finds Singapore facets (nested-aware).
Usage: workday_cxs.py <tenant> <site> [searchText] [--debug]"""
import json, sys, urllib.request

tenant, site = sys.argv[1], sys.argv[2]
search = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else ""
debug = '--debug' in sys.argv
base = f"https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
HDRS = {"Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Referer": f"https://{tenant}.wd1.myworkdayjobs.com/en-US/{site}"}

def post(payload):
    req = urllib.request.Request(base + "/jobs", data=json.dumps(payload).encode(), headers=HDRS)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=40).read().decode())
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_body": e.read().decode(errors='ignore')[:300]}

d0 = post({"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
if "_http_error" in d0:
    print(f"ERR {d0['_http_error']}: {d0['_body']}"); sys.exit(1)

sg_ids, sg_loc_ids = [], []

def walk(facets):
    for f in facets:
        fp = f.get("facetParameter")
        vals = f.get("values", [])
        if fp == "Location_Country":
            for v in vals:
                if "Singapore" in v.get("descriptor", ""):
                    sg_ids.append(v["id"])
        if fp == "primaryLocation":
            for v in vals:
                if v.get("descriptor", "").startswith("Singapore"):
                    sg_loc_ids.append(v["id"])
        # recurse into nested facet groups (e.g. locationMainGroup)
        for v in vals:
            if isinstance(v, dict) and "values" in v:
                walk([v])

walk(d0.get("facets", []))
if debug:
    print(f"sg country ids: {sg_ids}; sg location ids: {sg_loc_ids}")

d = None
if sg_loc_ids:
    d = post({"appliedFacets": {"locations": sg_loc_ids}, "limit": 100, "offset": 0, "searchText": search})
if (d is None or "_http_error" in d) and sg_ids:
    d = post({"appliedFacets": {"Location_Country": sg_ids}, "limit": 100, "offset": 0, "searchText": search})
if d is None:
    print(f"NO-SG-FACET; total={d0.get('total')}"); sys.exit(2)
if "_http_error" in d:
    print(f"APPLY ERR {d['_http_error']}: {d['_body']}"); sys.exit(1)

print(f"TOTAL_SG={d.get('total')} (searchText={search!r})")
for j in d.get("jobPostings", []):
    print(f"{j.get('title')} | {j.get('locationsText')} | {j.get('externalPath')} | {j.get('postedOn','')}")
