import json, re, sys

d = json.load(open("/home/kavin/jobscan/details.json"))

WATCH = [
    "4448140700",  # ByteDance Network Engineer Graduate 2027
    "4448537064",  # TikTok Governance & Experience Associate Graduate
    "4403365908",  # Binance Pioneer AI Engineer Dev Tools
    "4403916134",  # Binance Pioneer Applied Data Scientist
    "4403917076",  # Binance Pioneer Research Data Scientist
    "4404787424",  # Vitol Network Engineer
    "4449231706",  # Hartree Trading Assistant Base Metals
    "4447918037",  # GLDB FX Trader
    "4448283110",  # Grey Tree Lithium Trader
    "4446262815",  # DBS Trader Equity Derivatives
    "4439883204",  # Citi Officer Markets Ops Control
    "4450084171",  # Silicon Box Associate Engineer Process
    "4450931868",  # Silicon Box Associate Process Engineer
    "4105613163",  # DSTA Engineer Robotics
    "4422677107",  # Thales SWE Embedded
    "4282102214",  # Seatrium AI Developer
    "4299791751",  # SIAEC Technical Planner Training
    "4312636535",  # BorgWarner Engineering Assistant
    "4330144053",  # GoerTek Control Algorithm Engineer
    "4408001392",  # Sonar AI Research Scientist
    "4382835839",  # Broadcom Facilities Assoc Eng
    "4382849159",  # Broadcom Equipment Assoc Eng
    "4448974790",  # ST Eng Cloud Engineer
    "4448939410",  # Capgemini DevOps
    "4449069988",  # HP Mfg Test SWE
    "4412244110",  # CAAS Engineer IDTS
    "4412387902",  # Digital Realty Site Engineer I
    "4413522998",  # Mercedes-Benz Cyber Defensive Ops Analyst
    "4413880064",  # GovTech SWE DevOps TIC
    "4414158598",  # Adyen CDD Risk Analyst
    "4414585691",  # Aon Full Stack SWE
    "4414656280",  # Aurecon Electrical Engineer
    "4420979883",  # ExxonMobil Quant Analyst V&S LNG
    "4440545440",  # Santander Analyst/Associate
    "4441664530",  # JPMorgan Client Onboarding Associate
    "4443466465",  # CA CIB Junior Java Dev
    "4445499714",  # CA CIB Junior Java SWE
    "4448031758",  # Airwallex Associate Credit Risk Ops
    "4448092017",  # Amplify Health Associate
    "4448416137",  # Sanmina Engineering Assistant I
    "4448804477",  # Kris Infotech Junior TA Cloud
    "4448808608",  # Thermo Fisher Early Talent Finance
    "4448817638",  # Cushman & Wakefield Asst Eng
    "4449204701",  # Nomura Associate Stress Testing
    "4449941867",  # Liminal Embedded Apprentice
    "4440701013",  # Accenture Pega Developer Fresh Analyst
    "4423195559",  # Canon Asst Eng Industrial
    "4449259398",  # TUV SUD Assoc Eng E&E
    "4450033833",  # EY Associate CCaSS 2027
    "4448151932",  # NTU RA Mathematics
    "4450225262",  # NUS RA/Eng IC Design
    "4448852082",  # NUS RA Statistical Programming
    "4431701285",  # KPMG Junior Specialist IT Security
    "4329954656",  # SHIELD Risk Analyst
    "4273550564",  # StarHub Data Scientist
    "4337812620",  # Viridien MLE
    "4343751321",  # Thales System Engineer
    "4343622120",  # Thales System Solution Engineer
    "4343562331",  # Thales Cybersecurity System Engineer
    "4350738171",  # Molex Product Design Engineer
    "4354311901",  # Barnes Aerospace Quality Engineer
    "4380248753",  # Anotech T&C Engineer
    "4381423126",  # Klook Data Analyst
    "4381479706",  # Anchorage Digital Risk
    "4391532575",  # MPA Engineer
    "4404002266",  # YouTrip SWE
    "4408493350",  # Seatrium Electrical HV
    "4411533823",  # Vanderlande PLC Engineer
    "4411500545",  # Keppel C&I Engineer
    "4411534401",  # KLA Manufacturing Design Engineer
    "4438720579",  # KLA System Engineer
    "4439240471",  # KLA Algorithm Engineer R&D
    "4420402043",  # AlphaSense Cloud Support
    "4422675198",  # Wesco Network Engineer
    "4422398433",  # STMicro WETS Quality Champion
    "3785474085",  # IMDA Software QA Engineer
    "4402722781",  # AvePoint SW Quality
    "4039762137",  # AvePoint DevOps
    "4053732901",  # AvePoint Python Dev & Tester
    "4446614265",  # SearchAsia TA Executive (skip - agency)
    "4280697734",  # Deloitte T&L Associate 2026
    "4429785607",  # KPMG Consulting G&R Grad Assoc 2026
    "4439777986",  # KPMG Econ & Reg Grad Assoc 2026
    "4450031989",  # EY-Parthenon T&CF Modelling (2026)
    "4450045814",  # EY-Parthenon Strategy & Execution (2026)
    "4441444992",  # Element Materials Assoc Eng
    "4410844333",  # Micron Process & Equipment
    "4410834723",  # Micron Smart Systems
    "4410835503",  # Micron Shift Engineer Metro RDA
    "4410845191",  # Micron SSD Customer Validation
    "4410846288",  # Micron Product QA
    "4410842278",  # Micron Facilities Electrical
    "4410846244",  # Micron Facilities Control
    "4422653919",  # OCBC Cyber Threat Analyst
    "4448822612",  # Boilermaster Tender & Estimation
    "4371899515",  # Singtel Associate Engineer
    "4372109321",  # Singtel Associate Engineer 2
    "4404095711",  # STMicro Assistant Process Engineer
    "4441974546",  # STMicro Shift Process Assistant Engineer
    "4448915596",  # (unknown - check)
]

for jid in WATCH:
    info = d.get(jid)
    if not info:
        print(f"== {jid} NOT FETCHED ==")
        continue
    t = info.get("title", "")
    org = info.get("org", "")
    desc = info.get("desc", "")[:420]
    print(f"== {jid} | {org} | {t}")
    print(f"   {desc}")
    print()
