import json
d = json.load(open("/home/kavin/jobscan/details.json"))
FINAL = {
    "4448140700": "ByteDance Network Engineer Graduate",
    "4448537064": "TikTok G&E Associate Graduate",
    "4443466465": "CA CIB Junior Java Developer",
    "4445499714": "CA CIB Junior Java SWE",
    "4440701013": "Accenture Pega Fresh Analyst",
    "4448804477": "Kris Infotech Junior Cloud",
    "4403365908": "Binance Pioneer AI DevTools",
    "4403916134": "Binance Pioneer Applied DS",
    "4403917076": "Binance Pioneer Research DS",
    "4105613163": "DSTA Robotics",
    "4382835839": "Broadcom Facilities AE",
    "4382849159": "Broadcom Equipment AE",
    "4312636535": "BorgWarner Eng Assistant",
    "4448416137": "Sanmina Eng Assistant I",
    "4449259398": "TUV SUD Assoc E&E",
    "4448822612": "Boilermaster Tender",
    "4448151932": "NTU RA Math",
    "4448852082": "NUS RA Statistical",
    "4450225262": "NUS RA IC Design",
    "4299791751": "SIAEC Technical Planner",
    "4448808608": "Thermo Fisher Early Talent",
    "4450033833": "EY CCaSS 2027",
    "4429785607": "KPMG G&R Grad Assoc",
    "4439777986": "KPMG Econ&Reg Grad Assoc",
    "4431701285": "KPMG Junior IT Security",
    "4449204701": "Nomura Stress Testing",
}
for jid, label in FINAL.items():
    info = d.get(jid, {})
    desc = info.get("desc", "")
    sg = "Singapore" in desc
    print(f"{jid} | {label} | SG-in-desc: {sg}")
