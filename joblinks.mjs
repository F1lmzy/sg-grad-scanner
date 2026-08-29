import { chromium } from 'playwright';
import fs from 'fs';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const url = process.argv[2];
const out = process.argv[3];
const pat = process.argv[4] || 'job';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(4000);
for (let i = 0; i < 12; i++) { await page.evaluate(() => window.scrollBy(0, 800)); await page.waitForTimeout(250); }
await page.waitForTimeout(3000);
const links = await page.evaluate((pat) =>
  Array.from(document.querySelectorAll('a[href]'))
    .map(a => ({ t: (a.innerText||'').trim().slice(0,90), h: a.href }))
    .filter(l => new RegExp(pat,'i').test(l.h) && l.t)
    .filter((v,i,arr)=>arr.findIndex(x=>x.h===v.h)===i),
  pat);
fs.writeFileSync(out, JSON.stringify(links, null, 1));
console.log('links:', links.length);
links.slice(0,25).forEach(l => console.log(l.t, '|', l.h));
await browser.close();