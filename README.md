# SG Grad Job Scanner

Automated scanner for Singapore graduate/full-time SWE, ML/AI, Robotics, Embedded
and Quant roles. Runs as a Hermes cron job (every 4h).

## Lead engines
- Direct ATS APIs (Workday, Greenhouse, Lever, SmartRecruiters, etc.)
- MyCareersFuture (MCF) and LinkedIn guest-job feeds

All engines are LEAD ENGINES ONLY: they never emit MCF/LinkedIn/aggregate links.
Every result is resolved to the company's OWN career portal before reporting.

## Main entrypoint
`sg_ats_fetch.py` — direct ATS APIs + MCF + LinkedIn, dedup via `seen_ids.json`.

## Operational rules
- User is a foreigner in SG: never report MCF/LinkedIn/aggregate links;
  always resolve to the company's own portal.
- Exit contract: script must indicate `found_via=mcf|linkedin` or a resolved
  company-portal result.