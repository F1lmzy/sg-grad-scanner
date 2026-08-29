import re, glob
ids = set()
pat = re.compile(r'jobs/view/(\d+)')
files = ['/home/kavin/obsidian-vault/Master_List.md'] + glob.glob('/home/kavin/obsidian-vault/Scans/*.md')
for f in files:
    try:
        t = open(f, encoding='utf-8', errors='ignore').read()
    except Exception as e:
        continue
    for m in pat.finditer(t):
        ids.add(m.group(1))
out = '\n'.join(sorted(ids, key=lambda x: int(x))) + '\n'
open('/home/kavin/jobscan/tracked_ids.txt', 'w').write(out)
print("total nums from /jobs/view/:", len(ids))
