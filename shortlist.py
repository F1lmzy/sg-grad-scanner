import json, re

cands = json.load(open('/home/kavin/jobscan/candidates.json'))
det = json.load(open('/home/kavin/jobscan/details.json'))

AGENCY = re.compile(r'\b(adecco|randstad|manpower|kerry consulting|michael page|persol|sciente|rapsys|unison|sedha|optimum|avance|helius|eteam|ampstek|rhino partners|pivot search|selby jennings|whitecrow|nicoll curtinn?|bah partners|gravitas|ec1|hudson|vouch|ambition|nityo|hcltech|fpt|beyondsoft|first page|tap growth|autonomai|sm2|easpire|tempserv|sartre|meyer|arter|segula|alcami|thakral)\w*', re.I)
SENIOR = re.compile(r'\b(senior|staff|lead|principal|director|vp\b|head of|experienced|manager)\b', re.I)
EXCLUDE_TITLE = re.compile(r'(professor|fellow\b|assistant professor)', re.I)
# clear non-tech / non-relevant
IRRELEV = re.compile(r'(microbiolog|crew|kitchen|clerk|bartender|cosmetolog|barista|waitress|sales associate|retail)', re.I)

cands_sorted = sorted(cands.keys(), key=lambda x: int(x))
out = []
for jid in cands_sorted:
    info = det.get(jid, {})
    t = info.get('title','')
    org = info.get('org','')
    desc = info.get('desc','')
    date = info.get('date','')
    if not t or AGENCY.search(org) or AGENCY.search(t):
        continue
    if SENIOR.search(t):
        continue
    if EXCLUDE_TITLE.search(t) or IRRELEV.search(t.lower()):
        continue
    out.append((jid, org, t, date, desc))

# print compact with desc snippet
for jid, org, t, date, desc in out:
    print(f"### {jid} | {org} | {t} | {date}")
    print(desc[:600].replace('\n',' '))
    print()
