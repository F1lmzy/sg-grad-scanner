import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US' });
const page = await ctx.newPage();
const api = [];
page.on('response', async r => {
  const u = r.url();
  if (/api|jobs|search|graphql|json|bang|sf/gi.test(u) && !/\.(png|jpg|css|js|woff)/.test(u)) {
    api.push(u);
    try { const ctype = r.headers()['content-type']||''; if (/json/.test(ctype)) { const b = await r.text(); api.push('  BODY['+b.length+']: '+b.slice(0,300)); } } catch(e){}
  }
});
await page.goto('https://careers.ey.com/ey-global/en/jobs?keywords=Singapore', { waitUntil: 'networkidle', timeout: 60000 }).catch(()=>{});
await page.waitForTimeout(12000);
const fs = await import('fs');
fs.writeFileSync('/tmp/ey_api.json', JSON.stringify(api, null, 1));
console.log('API CALLS', api.length);
console.log(api.slice(0,40).join('\n'));
await browser.close();