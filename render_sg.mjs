import { chromium } from 'playwright';
import fs from 'fs';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US' });
const page = await ctx.newPage();
const url = process.argv[2];
const out = process.argv[3] || '/tmp/render.txt';
const waitMs = parseInt(process.argv[4] || '10000', 10);
try {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(waitMs);
  for (const label of ['Accept All Cookies','Accept All','Accept','Continue','Agree']) {
    const btns = page.locator(`button:has-text("${label}"), a:has-text("${label}")`);
    const n = await btns.count();
    if (n) { await btns.first().click({ timeout: 4000 }).catch(()=>{}); await page.waitForTimeout(2000); break; }
  }
  for (let i=0;i<25;i++){ await page.evaluate(()=>window.scrollBy(0,800)); await page.waitForTimeout(250); }
  await page.waitForTimeout(3000);
  const text = await page.evaluate(()=>document.body?document.body.innerText:'');
  const links = await page.evaluate(()=>Array.from(document.querySelectorAll('a')).map(a=>({t:(a.innerText||'').trim().replace(/\s+/g,' '),h:a.href})).filter(l=>l.h && /job|requisition|position|vacanc/i.test(l.h)).slice(0,120));
  fs.writeFileSync(out, text);
  fs.writeFileSync(out + '.json', JSON.stringify(links,null,1));
  console.log('TEXT', text.length, 'LINKS', links.length);
  const lines = text.split('\n').map(x=>x.trim()).filter(x=>/Junior|Associate|Graduate|Software|Developer|AI|Quant|Engineer|Analyst|Fresh/i.test(x));
  console.log(lines.slice(0,50).join('\n'));
} catch (e) { console.log('ERR', e.message); }
await browser.close();
