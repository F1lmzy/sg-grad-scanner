import { chromium } from 'playwright';
import fs from 'fs';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const url = process.argv[2];
const out = process.argv[3];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
page.on('response', async (r) => {
  const u = r.url();
  if (/query|search|requisition|position/i.test(u) && /json/i.test((r.headers()['content-type']||''))) {
    try { fs.writeFileSync(out + '.job.json', await r.text()); console.log('SAVED', u); } catch(e){}
  }
});
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(6000);
await browser.close();
console.log('done');