#!/usr/bin/env python3
import json, urllib.request

SG = "80938777cac5440fab50d729f9634969"

def cxs(tenant, site, key, search):
    url = f"https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    req = urllib.request.Request(url, data=json.dumps({
        "appliedFacets": {key: [SG]}, "limit": 20, "offset": 0, "searchText": search}).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "Mozilla/5.0 Chrome/120",
                 "Referer": f"https://{tenant}.wd1.myworkdayjobs.com/en-US/{site}"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=40).read().decode())
    except urllib.error.HTTPError as e:
        return f"HTTP{e.code}", []
    return d.get("total"), d.get("jobPostings", [])

for tenant, site, key, label in [("flextronics", "Careers", "Location_Country", "FLEX SG"),
                                 ("dxctechnology", "DXCJobs", "locationCountry", "DXC SG")]:
    total, jobs = cxs(tenant, site, key, "")
    print(f"\n########## {label} ALL ({total}) ##########")
    for j in jobs:
        print(f"{j['title']} | {j['locationsText']} | {j['externalPath']} | {j.get('postedOn','')}")
    for search in ["Graduate", "Trainee", "Fresher"]:
        t, js = cxs(tenant, site, key, search)
        titles = ", ".join(j['title'] for j in js) if isinstance(t, int) else str(t)
        print(f"[{label}] search={search!r} -> total={t}: {titles}")
