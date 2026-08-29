import json, re

cands = json.load(open('/home/kavin/jobscan/candidates.json'))
det = json.load(open('/home/kavin/jobscan/details.json'))

AGENCY = re.compile(r'\b(adecco|randstad|manpower|kerry|michael page|persol|sciente|rapsys|unison|sedha|optimum|avance|helius|eteam|ampstek|rhino|pivot|selby|whitecrow|nicoll|bah partners|gravitas|ec1|hudson|vouch|ambition|nityo|hcltech|fpt|beyondsoft|first page|tap growth|autonomai|sm2|easpire|tempserv|sartre|avance|zodiac|nextgen|kelly|astra|insight|innoquest|cylindo)\w*', re.I)
SENIOR = re.compile(r'\b(senior|staff|lead|principal|director|\bvp\b|head of|experienced|manager|architect)\b', re.I)
ENTRY_DESC = re.compile(r'(fresh graduate|fresh grad|entry[- ]level|graduate |junior |no experience|without experience|0[-–]?\s*[0-3] years?|recent graduate|new graduate|early[- ]career|welcome to apply|are welcome|internship experience|newly graduated|trainee|apprentice)', re.I)
ENTRY_TITLE = re.compile(r'(graduate|junior|associate|assistant|trainee|entry)', re.I)

cands_sorted = sorted(cands.keys(), key=lambda x: int(x))
keep = []
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
    score = 0
    if ENTRY_TITLE.search(t): score += 2
    if ENTRY_DESC.search(desc.lower()): score += 1
    if not score:
        continue
    # require at least one entry signal
    keep.append((jid, org, t, date, score))

for jid, org, t, date, score in sorted(keep, key=lambda x:(int(x[0]))):
    print(f"[{score}] {jid} | {org[:28]} | {t[:95]} | {date}")
print("\ncount:", len(keep))
