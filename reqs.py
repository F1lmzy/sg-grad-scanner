import json, re

d = json.load(open("/home/kavin/jobscan/details.json"))

SHORT = [
    "4448140700", "4448537064",  # ByteDance Network Eng Grad, TikTok G&E Assoc Grad
    "4403365908", "4403916134", "4403917076",  # Binance Pioneer x3
    "4404787424",  # Vitol Network Engineer
    "4449231706",  # Hartree Trading Assistant
    "4447918037",  # GLDB FX Trader
    "4446262815",  # DBS Trader
    "4439883204",  # Citi Officer Markets Ops Control
    "4450084171", "4450931868",  # Silicon Box x2
    "4105613163",  # DSTA Robotics
    "4422677107",  # Thales SWE Embedded
    "4282102214",  # Seatrium AI Developer
    "4299791751",  # SIAEC Training Programme
    "4312636535",  # BorgWarner Eng Assistant
    "4330144053",  # GoerTek Control Algorithm
    "4408001392",  # Sonar AI Research
    "4382835839", "4382849159",  # Broadcom Facilities/Equipment Assoc Eng
    "4448974790",  # ST Eng Cloud
    "4448939410",  # Capgemini DevOps
    "4412244110",  # CAAS Engineer IDTS
    "4412387902",  # Digital Realty Site Engineer I
    "4413522998",  # Mercedes-Benz Cyber Analyst
    "4413880064",  # GovTech SWE DevOps
    "4414158598",  # Adyen CDD Risk
    "4414585691",  # Aon Full Stack
    "4414656280",  # Aurecon Electrical
    "4420979883",  # ExxonMobil Quant Analyst LNG
    "4440545440",  # Santander Analyst/Associate
    "4441664530",  # JPMorgan Client Onboarding
    "4443466465", "4445499714",  # CA CIB Junior Java x2
    "4448031758",  # Airwallex Associate Credit Risk
    "4448092017",  # Amplify Health Associate
    "4448416137",  # Sanmina Engineering Assistant I
    "4448804477",  # Kris Infotech Junior Cloud
    "4448808608",  # Thermo Fisher Early Talent Finance
    "4448817638",  # Cushman & Wakefield Asst Eng
    "4449204701",  # Nomura Associate Stress Testing
    "4440701013",  # Accenture Pega Fresh Analyst
    "4449259398",  # TUV SUD Assoc Eng E&E
    "4450033833",  # EY CCaSS 2027
    "4448151932",  # NTU RA Math
    "4450225262",  # NUS RA IC Design
    "4448852082",  # NUS RA Statistical
    "4431701285",  # KPMG Junior Specialist IT Security
    "4329954656",  # SHIELD Risk Analyst
    "4273550564",  # StarHub Data Scientist
    "4337812620",  # Viridien MLE
    "4343751321", "4343622120", "4343562331",  # Thales x3
    "4350738171",  # Molex Product Design
    "4354311901",  # Barnes Aerospace QA
    "4380248753",  # Anotech T&C
    "4381423126",  # Klook Data Analyst
    "4381479706",  # Anchorage Digital Risk
    "4391532575",  # MPA Engineer
    "4404002266",  # YouTrip SWE
    "4408493350",  # Seatrium Electrical HV
    "4411533823",  # Vanderlande PLC
    "4411500545",  # Keppel C&I
    "4411534401",  # KLA Mfg Design Eng
    "4438720579",  # KLA System Eng
    "4439240471",  # KLA Algorithm Eng
    "4420402043",  # AlphaSense Cloud Support
    "4422675198",  # Wesco Network
    "4422398433",  # STMicro WETS
    "3785474085",  # IMDA SW QA
    "4402722781", "4039762137", "4053732901",  # AvePoint x3
    "4429785607", "4439777986",  # KPMG Grad Assoc x2
    "4441444992",  # Element Materials Assoc Eng
    "4422653919",  # OCBC Cyber Threat Analyst
    "4371899515", "4372109321",  # Singtel Assoc Eng x2
    "4404095711", "4441974546",  # STMicro Asst Process Eng x2
    "4448822612",  # Boilermaster Tender
]

for jid in SHORT:
    info = d.get(jid)
    if not info:
        continue
    desc = info.get("desc", "")
    # find experience-related sentences
    hits = re.findall(r'[^.]*?(?:year|yr|experience|Experience|graduate|Graduate|degree|Degree|diploma|Diploma)[^.]*\.', desc)
    interesting = [h.strip() for h in hits if re.search(r'(year|yr|experience|graduate|degree|diploma|entry)', h)]
    print(f"== {jid} | {info['org'][:28]} | {info['title'][:60]}")
    for h in interesting[:4]:
        print("   *", h[:220])
    print()
