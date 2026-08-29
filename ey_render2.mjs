import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US' });
const page = await ctx.newPage();
async function go(u){
  await page.goto('https://careers.ey.com/ey-global/en/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(3000);
  for (const label of ['Accept All Cookies','Accept All','Accept','Continue']) {
    const btns = page.locator(`button:has-text("${label}"), a:has-text("${label}")`);
    const n = await btns.count();
    if (n) { await btns.first().click({ timeout: 4000 }).catch(()=>{}); await page.waitForTimeout(2000); break; }
  }
  await page.goto(u, { waitUntil: 'networkidle', timeout: 45000 }).catch(()=>{});
  await page.waitForTimeout(8000);
  for (let i=0;i<12;i++){ await page.evaluate(()=>window.scrollBy(0,900)); await page.waitForTimeout(250); }
  await page.waitForTimeout(4000);
  return await page.evaluate(()=>document.body?document.body.innerText:'');
}
const opt = process.argv[2] || 'AI';
const queries = {
  AI: 'https://careers.ey.com/ey-global/en/search-results?keywords=AI%20Solutions%20Developer&locationcountry=Singapore',
  FAAS: 'https://careers.ey.com/ey-global/en/search-results?keywords=Quantitative%20Analytics&locationcountry=Singapore'
};
const text = await go(queries[opt] || queries.AI);
const fs = await import('fs');
fs.writeFileSync(`/tmp/ey_${opt}.txt`, text);
// extract requisition links
const reqs = await page.evaluate(()=>Array.from(document.querySelectorAll('a')).map(a=>({t:(a.innerText||'').trim().replace(/\s+/g,' '),h:a.href})).filter(l=>/requisition/i.test(l.h)).slice(0,40));
fs.writeFileSync(`/tmp/ey_${opt}.json`, JSON.stringify(reqs,null,1));
console.log('TEXT', text.length, 'REQS', reqs.length);
await browser.close();