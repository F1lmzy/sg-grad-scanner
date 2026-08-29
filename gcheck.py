import re, sys, subprocess, time
UA = "Mozilla/5.0"
for jid in ["112068666534568646", "121590411461305030"]:
    url = f"https://www.google.com/about/careers/applications/jobs/results/{jid}"
    r = subprocess.run(["curl", "-s", "-L", "-A", UA, url], capture_output=True, text=True, timeout=60)
    h = r.stdout
    m = re.search(r'AF_initDataCallback\(\{key: \'ds:0\'.*?Minimum qualifications:', h, re.S)
    d = m.group(0) if m else ""
    d = re.sub(r'<[^>]+>', ' ', d)
    d = re.sub(r'\s+', ' ', d)
    i = d.find('Minimum qualifications')
    print("===", jid, "===")
    print(d[i:i+500] if i >= 0 else "NO MIN QUAL FOUND")
    time.sleep(0.4)
