import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
await page.goto('https://careers.tiktok.com/search?location=Singapore', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
await page.waitForTimeout(8000);
const res = await page.evaluate(async ()=>{
  const kws=['AI Data Strategy','Model Operations','AI Data Service','Graduate 2027','AI Associate'];
  const out=[]; const seen=new Set();
  for(const kw of kws){
    try{
      const r = await fetch('https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts', {
        method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({keyword:kw, location:'Singapore', limit:50, page:1})
      });
      const j = await r.json();
      const posts = (j?.data?.job_post_list)||[];
      for(const p of posts){
        const key=p.code;
        if(seen.has(key)) continue; seen.add(key);
        out.push({kw, title:p.title, country:p.rect_country||'', region:p.rect_region||'', loc:p.location||p.work_location||'', grad:/graduate|2027|freshgrad/i.test(p.title)?'Y':'N', code:p.code, link:`https://careers.tiktok.com/position/${p.code}/detail`});
      }
    }catch(e){ out.push({kw, err:String(e)}); }
  }
  return out;
});
const fs = await import('fs');
fs.writeFileSync('/tmp/tt_check_grads.json', JSON.stringify(res,null,1));
console.log('total', res.length);
for(const j of res){
  if(j.err) { console.log('ERR', j.kw, j.err); continue; }
  console.log('-', j.title, '| grad:', j.grad, '| country:', j.country, '| loc:', j.loc, '|', j.link);
}
await browser.close();