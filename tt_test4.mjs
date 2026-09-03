import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
await page.goto('https://lifeattiktok.com/search', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
await page.waitForTimeout(5000);
const E='https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts';
const H={'content-type':'application/json','website-path':'tiktok','referer':'https://lifeattiktok.com/'};
const res = await page.evaluate(async ({E,H})=>{
  const out=[];
  const call=async(url)=>{
    try{ const r=await fetch(url,{method:'POST',headers:H}); const t=await r.text(); let j;try{j=JSON.parse(t)}catch(e){return {errt:t.slice(0,60)}}; const posts=(j.data?.job_post_list)||[]; return {code:j.code,msg:j.msg,n:posts.length,hits:posts.filter(p=>/AI Data|Model Operation|Data Strategy/i.test(p.title)).map(p=>p.title)}; }catch(e){return {err:String(e)};}
  };
  out.push({label:'empty', ...(await call(E))});
  out.push({label:'qs kw', ...(await call(E+'?keyword=AI%20Data%20Strategy'))});
  out.push({label:'qs loc kw', ...(await call(E+'?keyword=AI&location=Singapore&limit=30'))});
  return out;
},{E,H});
const fs=await import('fs');
fs.writeFileSync('/tmp/tt_test4.json', JSON.stringify(res,null,1));
console.log(JSON.stringify(res,null,1).slice(0,2500));
await browser.close();