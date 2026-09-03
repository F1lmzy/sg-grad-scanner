import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
async function grab(keyword, limit){
  await page.goto('https://lifeattiktok.com/search?keyword='+encodeURIComponent(keyword)+'&limit='+limit+'&offset=0', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
  for(const lbl of ['Accept all','Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:2500}).catch(()=>{}); break; } }
  await page.waitForTimeout(9000);
  const items=await page.evaluate(()=>{
    const out=[];
    for(const a of document.querySelectorAll('a[href*="/search/"]')){
      const href=a.getAttribute('href')||'';
      const full=(a.innerText||'').trim().replace(/\s+/g,' ');
      if(full && /[A-Za-z]{3}/.test(full)) out.push({full,href});
    }
    return out;
  });
  const seen=new Set();
  console.log('== '+keyword+' limit='+limit+' == n='+items.length);
  for(const it of items){ if(seen.has(it.href))continue; seen.add(it.href); console.log('-',it.full.slice(0,170),'|',it.href.slice(-22)); }
}
await grab('AI Data Strategy', 30);
await grab('Model Operations Specialist', 30);
await browser.close();