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
  // POST empty object body (same as site)
  const call = async (body)=>{
    const r=await fetch(E, {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(body)});
    return r.json();
  };
  const j = await call({});   // empty body object
  const posts=(j.data?.job_post_list)||[];
  out.push({code:j.code, msg:j.msg, n:posts.length, has_more:j.data?.has_more, total:j.data?.total});
  for(const p of posts){
    out.push({title:p.title, loc:p.work_location||p.location||'', country:p.rect_country||p.country||'', grad:/graduate|2027|fresh/i.test(p.title), code:p.code});
  }
  return out;
}, E);
const fs=await import('fs');
fs.writeFileSync('/tmp/tt_all.json', JSON.stringify(res,null,1));
console.log('meta', JSON.stringify(res.find(x=>x.code!==undefined&&x.n!==undefined)));
const hits=res.filter(x=>x.title && /AI Data|Model Operation|AI Data Service|Data Strategy|AI Service/i.test(x.title));
console.log('HITS count', hits.length);
for(const h of hits) console.log('-', h.title, '| loc:', h.loc, '| grad:', h.grad, '| code:', h.code);
await browser.close();