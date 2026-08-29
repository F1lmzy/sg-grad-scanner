import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US', viewport:{width:1400,height:900} });
const page = await ctx.newPage();
await page.goto('https://careers.ey.com/', { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(5000);
for (const label of ['Accept All Cookies','Accept All','Accept']) {
  const btns = page.locator(`button:has-text("${label}"), a:has-text("${label}")`);
  const n = await btns.count();
  if (n) { await btns.first().click({ timeout: 4000 }).catch(()=>{}); await page.waitForTimeout(2000); break; }
}
await page.goto('https://careers.ey.com/ey-global/en/search-results', { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(()=>{});
await page.waitForTimeout(8000);
// Find and fill keyword search input
for (const sel of ['input[type="search"]','input[aria-label*="keyword" i]','input[aria-label*="search" i]','input[placeholder*="search" i]','input[placeholder*="keyword" i]']) {
  const inp = page.locator(sel).first();
  const n = await inp.count().catch(()=>0);
  if (n>0) {
    await inp.click().catch(()=>{});
    await inp.fill('AI Solutions Developer').catch(()=>{});
    await page.keyboard.press('Enter').catch(()=>{});
    console.log('filled via', sel);
    break;
  }
}
await page.waitForTimeout(10000);
for (let i=0;i<15;i++){ await page.evaluate(()=>window.scrollBy(0,900)); await page.waitForTimeout(300); }
await page.waitForTimeout(5000);
const text = await page.evaluate(()=>document.body?document.body.innerText:'');
const links = await page.evaluate(()=>Array.from(document.querySelectorAll('a')).map(a=>({t:(a.innerText||'').trim().replace(/\s+/g,' '),h:a.href})).filter(l=>l.h.includes('careers.ey.com')&&/requisition|job/i.test(l.h)).slice(0,60));
const fs = await import('fs');
fs.writeFileSync('/tmp/ey_search.txt', text);
fs.writeFileSync('/tmp/ey_search.json', JSON.stringify(links,null,1));
const lines = text.split('\n').map(x=>x.trim()).filter(x=>/Junior|Associate|Software|Developer|AI|Quant|Engineer|Analyst|Graduate|Solution/i.test(x));
console.log('TEXT', text.length, 'LINKS', links.length);
console.log(lines.slice(0,40));
console.log('LINKS', JSON.stringify(links.slice(0,10),null,1));
await browser.close();