import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US', viewport:{width:1400,height:900} });
const page = await ctx.newPage();
await page.goto('https://careers.tiktok.com/search?location=Singapore', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept','Agree','Yes']){ const b=page.locator(`button:has-text("${lbl}"),a:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); await page.waitForTimeout(1500); break; } }
await page.waitForTimeout(8000);
for(let i=0;i<15;i++){ await page.evaluate(()=>window.scrollBy(0,800)); await page.waitForTimeout(250); }
await page.waitForTimeout(3000);
const links = await page.evaluate(()=>Array.from(document.querySelectorAll('a')).map(a=>({t:(a.innerText||'').trim().replace(/\s+/g,' '),h:a.href})).filter(l=>/position|job/i.test(l.h)&&!/javascript/i.test(l.h)).slice(0,80));
const fs = await import('fs');
fs.writeFileSync('/tmp/tt_links.json', JSON.stringify(links,null,1));
console.log('links', links.length);
for(const l of links) if(/Graduate/i.test(l.t)||/dropdown|location/i.test(l.t)) console.log('-',l.t,'|',l.h);
await browser.close();