import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US' });
const page = await ctx.newPage();
await page.goto('https://careers.ey.com/', { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(4000);
for (const label of ['Accept All Cookies','Accept All','Accept','Continue']) {
  const btns = page.locator(`button:has-text("${label}"), a:has-text("${label}")`);
  const n = await btns.count();
  if (n) { await btns.first().click({ timeout: 4000 }).catch(()=>{}); await page.waitForTimeout(2000); break; }
}
// browse to jobs page and search Singapore
await page.goto('https://careers.ey.com/ey-global/en/jobs?keywords=Singapore', { waitUntil: 'networkidle', timeout: 60000 }).catch(()=>{});
await page.waitForTimeout(12000);
for (let i=0;i<20;i++){ await page.evaluate(()=>window.scrollBy(0,900)); await page.waitForTimeout(300); }
await page.waitForTimeout(5000);
const text = await page.evaluate(()=>document.body?document.body.innerText:'');
const links = await page.evaluate(()=>Array.from(document.querySelectorAll('a')).map(a=>({t:(a.innerText||'').trim().replace(/\s+/g,' '),h:a.href})).filter(l=>l.h.includes('careers.ey.com')&&/requisition|job/i.test(l.h)).slice(0,60));
const fs = await import('fs');
fs.writeFileSync('/tmp/ey_sg.txt', text);
fs.writeFileSync('/tmp/ey_sg.json', JSON.stringify(links,null,1));
console.log('TEXT', text.length, 'LINKS', links.length);
// print the relevant portion
const lines = text.split('\n').map(x=>x.trim()).filter(x=>/Junior|Associate|Software|Developer|AI|Quant|Engineer|Analyst|Graduate/i.test(x));
console.log(lines.slice(0,40));
await browser.close();