import json
d = json.load(open("/home/kavin/jobscan/details.json"))
for jid in ["4448192824", "4432080938"]:
    info = d.get(jid, {})
    print(f"== {jid} | {info.get('org','')} | {info.get('title','')}")
    print(info.get("desc", "")[:900])
    print()
