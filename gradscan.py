import json, re
d = json.load(open("/home/kavin/jobscan/details.json"))
pat = re.compile(r'\b(graduate|trainee|apprentice|graduate trainee|grad)\b', re.I)
for jid, info in sorted(d.items(), key=lambda x: int(x[0])):
    t = info.get("title", "")
    if pat.search(t) and int(jid) > 4440000000:
        print(jid, "|", info.get("org", "")[:30], "|", t[:80])
