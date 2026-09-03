import careers_registry as cr, json
d = json.load(open(cr.PATH))
d['singtel']['last_verified'] = '2026-08-30'
d['singtel']['roles_seen'] = [
 "Associate Engineer",
 "Associate Engineer, Satellite",
 "Associate Engineer, Mobile Voice",
 "Associate Engineer, Fibre Network #GRIT",
 "Associate Engineer, Telecommunications Infrastructure #GRIT"
]
json.dump(d, open(cr.PATH,'w'), indent=1)
print("singtel updated")