import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
await page.goto('https://lifeattiktok.com/search?keyword='+encodeURIComponent('AI Data')+'&limit=20&offset=0', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept all','Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:2000}).catch(()=>{}); break; } }
await page.waitForTimeout(10000);
const info=await page.evaluate(()=>{
  const anchors=[...document.querySelectorAll('a')].map(a=>({t:(a.innerText||'').trim().replace(/\s+/g,' ').slice(0,120),href:a.getAttribute('href')||''})).filter(x=>x.t&&/ai|data|engineer|graduate|associate|specialist/i.test(x.t));
  const bodySnippet=document.body.innerText.slice(0,800);
  return {url:location.href, anchors, bodySnippet};
});
console.log(JSON.stringify(info,null,1));
await browser.close();