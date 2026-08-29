import { chromium } from 'playwright';
import fs from 'fs';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const url = process.argv[2];
const out = process.argv[3];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
page.on('response', async (r) => {
  if (/query|search|job|position|requisition/i.test(r.url()) && /json|application/i.test((r.headers()['content-type']||''))) {
    try { const b = await r.text(); if (/associate|engineer/i.test(b) && b.length>80) {
      fs.appendFileSync(out + '.api.log', 'URL: '+r.url()+'\nLEN:'+b.length+'\n'); fs.writeFileSync(out + '.last.json', b);
    } } catch(e){}
  }
});
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(5000);
// type in search
try {
  const input = page.locator('input').first();
  await input.click(); await input.fill('Associate Engineer');
  await page.keyboard.press('Enter');
  await page.waitForTimeout(6000);
  for (let i=0;i<10;i++){ await page.evaluate(()=>window.scrollBy(0,800)); await page.waitForTimeout(250);}
  await page.waitForTimeout(3000);
} catch(e){ console.log('search err', e.message); }
const text = await page.evaluate(()=>document.body.innerText);
fs.writeFileSync(out + '.txt', text);
console.log('text len', text.length, 'matches associate:', (text.match(/associate/gi)||[]).length);
await browser.close();