import re, sys, subprocess, time
UA = "Mozilla/5.0"
for jid in ["112068666534568646", "121590411461305030", "110236336849330886", "83447784010588870"]:
    url = f"https://www.google.com/about/careers/applications/jobs/results/{jid}"
    r = subprocess.run(["curl", "-s", "-L", "-A", UA, url], capture_output=True, text=True, timeout=60)
    h = r.stdout
    locs = set(re.findall(r'\["([A-Za-z ]+)",\["([A-Za-z ]+)"\],null,null,null,"SG"\]', h))
    print(jid, "->", locs if locs else "NO SG MATCH", "| SG count:", h.count('"SG"'))
    time.sleep(0.4)
