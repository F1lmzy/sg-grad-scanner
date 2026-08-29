import { chromium } from 'playwright';
import fs from 'fs';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const url = process.argv[2];
const out = process.argv[3];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
const acc = {};
page.on('response', async (r) => {
  if (r.url().includes('job/posts') || r.url().includes('job/filters')) {
    try {
      const body = await r.text();
      // keep the largest posts payload
      if (!acc.posts || body.length > acc.posts.len) acc.posts = { url: r.url(), len: body.length, body };
    } catch(e){}
  }
});
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(4000);
for (let i = 0; i < 30; i++) {
  await page.evaluate(() => window.scrollBy(0, 1400));
  await page.waitForTimeout(400);
}
await page.waitForTimeout(4000);
if (acc.posts) fs.writeFileSync(out + '.posts.json', acc.posts.body);
console.log('saved posts len', acc.posts ? acc.posts.len : 0, 'url', acc.posts ? acc.posts.url : '-');
await browser.close();