import { chromium } from 'playwright';
import fs from 'fs';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const url = process.argv[2];
const out = process.argv[3];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
const navs = [];
page.on('framenavigated', f => { if (f === page.mainFrame()) navs.push(f.url()); });
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(5000);
// find and click the "Module Associate Engineer (Equipment)" link
try {
  const el = await page.getByText('Module Associate Engineer (Equipment)').first();
  await el.click();
  await page.waitForTimeout(5000);
} catch(e){ console.log('click err', e.message); }
console.log('navs:', JSON.stringify(navs, null, 1));
const text = await page.evaluate(()=>document.body.innerText);
fs.writeFileSync(out + '.txt', text);
console.log('text has Module:', /Module Associate/.test(text));
await browser.close();