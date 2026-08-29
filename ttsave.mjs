import { chromium } from 'playwright';
import fs from 'fs';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const url = process.argv[2];
const out = process.argv[3];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
page.on('response', async (r) => {
  if (r.url().includes('search/job/posts')) {
    try { fs.writeFileSync(out + '.posts.json', await r.text()); console.log('SAVED POSTS JSON', out+'.posts.json', r.url()); } catch(e){}
  }
  if (r.url().includes('job/filters')) {
    try { fs.writeFileSync(out + '.filters.json', await r.text()); } catch(e){}
  }
});
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(6000);
await browser.close();
console.log('done');