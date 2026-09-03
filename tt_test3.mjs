import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
await page.goto('https://lifeattiktok.com/search', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
await page.waitForTimeout(6000);
const E='https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts';
const res = await page.evaluate(async (E)=>{
  const out=[];
  const tryUrl = async (qs)=>{
    try{ const r=await fetch(E+'?'+qs); return await r.json(); }catch(e){ return {err:String(e)}; }
  };
  // empty body first
  for(const qs of ['location=Singapore&limit=30','keyword=AI%20Data%20Strategy&location=Singapore','keyword=Model%20Operations&location=Singapore']){
    const j=await tryUrl(qs);
    if(j.err){ out.push({qs,err:j.err}); continue; }
    const posts=(j.data?.job_post_list)||[];
    out.push({qs, code:j.code, n:posts.length, sample:posts.slice(0,8).map(p=>({t:p.title, loc:p.work_location||p.location, c:p.rect_country}))});
  }
  return out;
}, E);
const fs=await import('fs');
fs.writeFileSync('/tmp/tt_api3.json', JSON.stringify(res,null,1));
console.log(JSON.stringify(res,null,1).slice(0,3000));
await browser.close();