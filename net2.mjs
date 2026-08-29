import { chromium } from 'playwright';
import fs from 'fs';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const url = process.argv[2];
const out = process.argv[3];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
let hits = [];
page.on('response', async (r) => {
  const ct = r.headers()['content-type'] || '';
  if (/json/.test(ct)) {
    try { const b = await r.text(); if (b.length > 40) hits.push({ url: r.url(), len: b.length }); } catch(e){}
  }
});
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
await page.waitForTimeout(4000);
// extract positions from DOM
const cards = await page.evaluate(() =>
  Array.from(document.querySelectorAll('*')).filter(e => {
    const H = e.attributes ? e.attributes.getNamedItem('data-code') : null;
    return H;
  }).slice(0,3).map(e => e.outerHTML.slice(0,200))
);
fs.writeFileSync(out + '.api.json', JSON.stringify(hits, null, 1));
fs.writeFileSync(out + '.cards.json', JSON.stringify(cards, null, 1));
console.log('API HITS:', hits.length);
hits.forEach(h => console.log(h.len, h.url));
console.log('cards sample:', JSON.stringify(cards));
await browser.close();