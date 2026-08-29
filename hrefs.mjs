import { chromium } from 'playwright';
import fs from 'fs';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const url = process.argv[2];
const out = process.argv[3];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(3000);
for (let i = 0; i < 14; i++) { await page.evaluate(() => window.scrollBy(0, 900)); await page.waitForTimeout(250); }
await page.waitForTimeout(3000);
const hrefs = await page.evaluate(() =>
  Array.from(document.querySelectorAll('a[href]')).map(a => a.href).filter(h => /job-detail/.test(h))
);
fs.writeFileSync(out, JSON.stringify(hrefs, null, 1));
console.log('hrefs:', hrefs.length);
console.log(hrefs.slice(0, 5).join('\n'));
console.log('...');
console.log(hrefs.filter(h => /J02171264|J02171637|J00356043/.test(h)).join('\n'));
await browser.close();