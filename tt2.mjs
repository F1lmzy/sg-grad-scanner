import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 Chrome/125.0', viewport:{width:1400,height:900} });
const page = await ctx.newPage();
await page.goto('https://careers.tiktok.com/search?location=Singapore', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
await page.waitForTimeout(10000);
const hrefs = await page.evaluate(()=>{
  const all=[];
  for(const el of document.querySelectorAll('a[href*="position/"], div[data-id], div[data-position-id], [id^="position"]')){
    all.push({tag:el.tagName, t:(el.innerText||el.textContent||'').trim().slice(0,60), h:el.getAttribute('href')||'', d:el.getAttribute('data-id')||el.getAttribute('data-position-id')||''});
  }
  return all.slice(0,80);
});
const fs = await import('fs');
fs.writeFileSync('/tmp/tt2.json', JSON.stringify(hrefs,null,1));
console.log('n', hrefs.length);
for(const x of hrefs) if(/Graduate|Engineer/i.test(x.t)||x.d) console.log('-',x.t,'|',x.h,'|',x.d);
await browser.close();
