import re, sys, subprocess, time, json
UA = "Mozilla/5.0"
out = {}
for jid in ["112068666534568646", "121590411461305030", "110236336849330886", "83447784010588870"]:
    url = f"https://www.google.com/about/careers/applications/jobs/results/{jid}"
    r = subprocess.run(["curl", "-s", "-L", "-A", UA, url], capture_output=True, text=True, timeout=60)
    h = r.stdout
    m = re.search(r'AF_initDataCallback\(\{key: \'ds:0\'.*?\]\)', h, re.S)
    d = m.group(0) if m else ""
    d = re.sub(r'<[^>]+>', ' ', d)
    d = re.sub(r'\\u003c', '<', d)
    d = re.sub(r'\\u003e', '>', d)
    d = re.sub(r'\\u0026', '&', d)
    d = re.sub(r'<[^>]+>', ' ', d)
    d = re.sub(r'\s+', ' ', d)
    i = d.find('Minimum qualifications')
    j = d.find('Preferred qualifications')
    seg = d[i:j] if i >= 0 else "NO MIN QUAL"
    out[jid] = seg[:600]
    time.sleep(0.4)
json.dump(out, open("/home/kavin/jobscan/google_mq.json", "w"), indent=1)
for k, v in out.items():
    print("===", k, "===")
    print(v)
