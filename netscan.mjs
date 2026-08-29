import { chromium } from 'playwright';
import fs from 'fs';

const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';

const url = process.argv[2];
const out = process.argv[3];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US' });
const page = await ctx.newPage();
const apiHits = [];
page.on('response', async (r) => {
  const ct = (r.headers()['content-type'] || '');
  if (/json/.test(ct)) {
    try {
      const body = await r.text();
      if (body && body.length > 50) apiHits.push({ url: r.url(), len: body.length });
    } catch (e) {}
  }
});
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(3000);
for (let i = 0; i < 14; i++) { await page.evaluate(() => window.scrollBy(0, 900)); await page.waitForTimeout(250); }
await page.waitForTimeout(4000);
fs.writeFileSync(out + '.api.json', JSON.stringify(apiHits, null, 1));
console.log('API HITS:', apiHits.length);
apiHits.forEach(h => console.log(h.len, h.url));
await browser.close();