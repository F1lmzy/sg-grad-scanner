import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US' });
const page = await ctx.newPage();
await page.goto('https://careers.ey.com/ey-global/en/', { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(3000);
for (const label of ['Accept All Cookies','Accept All','Accept']) {
  const btns = page.locator(`button:has-text("${label}"), a:has-text("${label}")`);
  const n = await btns.count();
  if (n) { await btns.first().click({ timeout: 4000 }).catch(()=>{}); await page.waitForTimeout(2000); break; }
}
// now go to job search
await page.goto('https://careers.ey.com/ey-global/en/search-results?keywords=AI%20Solutions%20Developer&locationcountry=Singapore', { waitUntil: 'networkidle', timeout: 45000 }).catch(()=>{});
await page.waitForTimeout(8000);
for (let i=0;i<12;i++){ await page.evaluate(()=>window.scrollBy(0,900)); await page.waitForTimeout(250); }
await page.waitForTimeout(4000);
const text = await page.evaluate(()=>document.body?document.body.innerText:'');
const reqs = await page.evaluate(()=>Array.from(document.querySelectorAll('a')).map(a=>({t:(a.innerText||'').trim(),h:a.href})).filter(l=>/requisition/i.test(l.h)||/AI|associate/i.test(l.t)).slice(0,40));
const fs = await import('fs');
fs.writeFileSync('/tmp/ey6.txt', text);
fs.writeFileSync('/tmp/ey6.json', JSON.stringify(reqs,null,1));
console.log('TEXT', text.length, 'REQS', reqs.length);
await browser.close();