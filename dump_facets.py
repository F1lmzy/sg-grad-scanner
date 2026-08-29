#!/usr/bin/env python3
"""Dump all facet parameters + Singapore-ish values for a Workday tenant. Usage: dump_facets.py <tenant> <site>"""
import json, sys, urllib.request

tenant, site = sys.argv[1], sys.argv[2]
base = f"https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
req = urllib.request.Request(base + "/jobs", data=json.dumps({"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}).encode(),
                             headers={"Content-Type": "application/json", "Accept": "application/json",
                                      "User-Agent": "Mozilla/5.0 Chrome/120", "Referer": f"https://{tenant}.wd1.myworkdayjobs.com/en-US/{site}"})
d = json.loads(urllib.request.urlopen(req, timeout=40).read().decode())

def walk(facets, depth=0):
    for f in facets:
        fp = f.get("facetParameter")
        vals = f.get("values", [])
        sg = [v for v in vals if isinstance(v, dict) and "Singapore" in v.get("descriptor", "")]
        print(f"{'  '*depth}{fp} ({f.get('descriptor','')}): n={len(vals)} sg={[(v['descriptor'], v['id']) for v in sg]}")
        for v in vals:
            if isinstance(v, dict) and "values" in v:
                walk([v], depth + 1)

walk(d.get("facets", []))
print("TOTAL:", d.get("total"))
