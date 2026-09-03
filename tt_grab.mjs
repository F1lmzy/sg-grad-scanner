import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
async function grab(keyword){
  await page.goto('https://lifeattiktok.com/search?keyword='+encodeURIComponent(keyword)+'&location_code_list='+encodeURIComponent(encodeURIComponent('Singapore'))+'&limit=20&offset=0', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
  for(const lbl of ['Accept all','Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:2000}).catch(()=>{}); break; } }
  await page.waitForTimeout(9000);
  const items=await page.evaluate(()=>{
    const out=[];
    for(const a of document.querySelectorAll('a[href*="/search/"]')){
      const href=a.getAttribute('href')||'';
      const t=(a.innerText||'').trim().replace(/\s+/g,' ').slice(0,140);
      if(t && /[A-Za-z]/.test(t)) out.push({t,href});
    }
    return out;
  });
  console.log('== '+keyword+' ==');
  const seen=new Set();
  for(const it of items){ if(seen.has(it.href))continue; seen.add(it.href); console.log('-',it.t,'|',it.href); }
  return items;
}
await grab('AI Data Strategy');
await grab('Model Operations');
await browser.close();