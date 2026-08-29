import json, re

d = json.load(open("/home/kavin/jobscan/details.json"))

CHECK2 = [
    "4105613163",  # DSTA Robotics
    "4422677107",  # Thales SWE Embedded
    "4312636535",  # BorgWarner Eng Assistant
    "4330144053",  # GoerTek Control Algorithm
    "4408001392",  # Sonar AI Research
    "4412244110",  # CAAS IDTS
    "4413522998",  # Mercedes-Benz Cyber
    "4413880064",  # GovTech DevOps
    "4414585691",  # Aon Full Stack
    "4414656280",  # Aurecon Electrical
    "4420979883",  # ExxonMobil Quant LNG
    "4440545440",  # Santander Analyst
    "4448031758",  # Airwallex Associate
    "4448092017",  # Amplify Health Associate
    "4448416137",  # Sanmina Asst I
    "4449204701",  # Nomura Stress Testing
    "4449259398",  # TUV SUD Assoc E&E
    "4431701285",  # KPMG Junior IT Security
    "4329954656",  # SHIELD Risk Analyst
    "4273550564",  # StarHub DS
    "4337812620",  # Viridien MLE
    "4343751321",  # Thales System Eng
    "4343622120",  # Thales System Solution
    "4343562331",  # Thales Cyber
    "4350738171",  # Molex Product Design
    "4354311901",  # Barnes QA
    "4381423126",  # Klook Data Analyst
    "4381479706",  # Anchorage Risk
    "4391532575",  # MPA Engineer
    "4404002266",  # YouTrip SWE
    "4411533823",  # Vanderlande PLC
    "4411500545",  # Keppel C&I
    "4438720579",  # KLA System Eng
    "4439240471",  # KLA Algorithm Eng
    "4420402043",  # AlphaSense Cloud Support
    "4422675198",  # Wesco Network
    "3785474085",  # IMDA SW QA
    "4402722781",  # AvePoint SW Quality
    "4039762137",  # AvePoint DevOps
    "4053732901",  # AvePoint Python
    "4422653919",  # OCBC Cyber Threat
    "4371899515",  # Singtel AE 1
    "4372109321",  # Singtel AE 2
    "4450084171",  # Silicon Box Assoc Eng Process
    "4439883204",  # Citi Officer
    "4414158598",  # Adyen CDD
    "4441444992",  # Element Materials
    "4441664530",  # JPM Client Onboarding
]

for jid in CHECK2:
    info = d.get(jid)
    if not info:
        continue
    desc = info.get("desc", "")
    # find qualification / requirement / minimum section
    m = re.search(r'(Qualification|Requirement|Minimum|What you.{0,20}(need|bring)|Who you are|About you|Your profile|What we.{0,20}(look|need)|Skills)', desc)
    seg = desc
    if m:
        seg = desc[m.start():]
    seg = seg[:500]
    print(f"== {jid} | {info['org'][:26]} | {info['title'][:58]}")
    print("   ", seg.replace("\n", " "))
    print()
