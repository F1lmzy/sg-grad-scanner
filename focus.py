import json, re, glob
cands = json.load(open('/home/kavin/jobscan/candidates.json'))
det = json.load(open('/home/kavin/jobscan/details.json'))

master = ''
for f in ['/home/kavin/obsidian-vault/Master_List.md'] + glob.glob('/home/kavin/obsidian-vault/Scans/*.md'):
    master += open(f, encoding='utf-8', errors='ignore').read()
ml = master.lower()

focus = ['4452274115','4455225990','4455241016','4445954457','4445967377','4436086582',
         '4455716025','4455301611','4454710458','4452954743','4454498358','4426301074',
         '4452546632','4451216114','4453239165','4454467073','4452524397','4408747190',
         '4452549590','4435373874','4452911308','4423654100','4437174257','4455702690',
         '4416393544','4433981443','4436096027','4448937473','4453695909','4452565697']

for jid in focus:
    info = det.get(jid, {})
    t = info.get('title','')
    org = info.get('org','')
    desc = info.get('desc','')
    date = info.get('date','')
    # check if referenced in master
    reftok = re.sub(r'[^a-z0-9 ]','', (org+' '+t).lower())
    # presence via company name
    cname = org.lower().split()[0] if org else ''
    print("="*100)
    print(f"{jid} | {org} | {t} | {date}")
    print("MASTER-REF:", cname in ml, "| title-in-master:", t.strip()[:60].lower() in ml)
    print(desc[:900].replace('\n',' '))
    print()
