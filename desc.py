import re, sys
h = open(sys.argv[1]).read()
m = re.search(r'(<div class="job__description[^>]*>.*?)(<div class="job__footer|$)', h, re.S)
d = m.group(1) if m else h
d = re.sub(r'<script.*?</script>', ' ', d, flags=re.S)
d = re.sub(r'<[^>]+>', ' ', d)
d = re.sub(r'\s+', ' ', d)
i = d.lower().find('experience')
print(d[max(0, i-800):i+500])
