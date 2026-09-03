import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
await page.goto('https://careers.tiktok.com/search?location=Singapore', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
await page.waitForTimeout(12000);
// collect job links from DOM
const items = await page.evaluate(()=>{
  const out=[];
  const anchors=document.querySelectorAll('a[href*="/position/"]');
  for(const a of anchors){
    const t=(a.innerText||'').trim();
    const href=a.getAttribute('href')||'';
    if(t && /graduate|graduate|AI|data|model|associate/i.test(t)) out.push({t, href});
  }
  return out;
});
const fs = await import('fs');
fs.writeFileSync('/tmp/tt_dom.json', JSON.stringify(items,null,1));
const uniq=[...new Map(items.map(x=>[x.href,x])).values()];
console.log('dom items', items.length, 'uniq', uniq.length);
for(const u of uniq) console.log('-', u.t.slice(0,120), '|', u.href.slice(0,140));
await browser.close();