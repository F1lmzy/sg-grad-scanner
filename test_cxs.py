#!/usr/bin/env python3
import json, urllib.request

def cxs(tenant, site, payload):
    url = f"https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "Accept": "application/json",
                                          "User-Agent": "Mozilla/5.0 Chrome/120",
                                          "Referer": f"https://{tenant}.wd1.myworkdayjobs.com/en-US/{site}"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=40).read().decode())
        return d.get("total"), d.get("jobPostings", [])[:3]
    except urllib.error.HTTPError as e:
        return f"HTTP{e.code}", e.read().decode(errors='ignore')[:120]

SG_COUNTRY = "80938777cac5440fab50d729f9634969"
SG_LOCS = ["a92f97387254013243646cbc8b53cec1", "5860280b1fe201fa9cd40abfce5293d4"]
variants = [
    ("Location_Country", {"appliedFacets": {"Location_Country": [SG_COUNTRY]}, "limit": 20, "offset": 0, "searchText": ""}),
    ("locationCountry", {"appliedFacets": {"locationCountry": [SG_COUNTRY]}, "limit": 20, "offset": 0, "searchText": ""}),
    ("locations", {"appliedFacets": {"locations": SG_LOCS}, "limit": 20, "offset": 0, "searchText": ""}),
    ("countries", {"appliedFacets": {"countries": [SG_COUNTRY]}, "limit": 20, "offset": 0, "searchText": ""}),
    ("leftFacet_locationCountry", {"appliedFacets": {"locationCountry": [SG_COUNTRY]}, "limit": 20, "offset": 0, "searchText": ""}),
]
for name, payload in variants:
    t, j = cxs("flextronics", "Careers", payload)
    print(f"{name}: total={t}")
    if isinstance(t, int):
        for x in j:
            print(f"    {x.get('title')} | {x.get('locationsText')}")

# DXC variants
print("--- DXC ---")
for name, payload in variants:
    t, j = cxs("dxctechnology", "DXCJobs", payload)
    print(f"{name}: total={t}")
    if isinstance(t, int):
        for x in j[:2]:
            print(f"    {x.get('title')} | {x.get('locationsText')}")
