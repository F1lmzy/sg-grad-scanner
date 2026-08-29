import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
const api=[];
page.on('response', async r=>{
  const u=r.url();
  if(/position|job|search|api|sug/i.test(u)&&!/\.(png|jpg|css|js|woff|svg)/.test(u)){
    api.push(u);
    try{ if(/json/.test(r.headers()['content-type']||'')){ const b=await r.text(); api.push('  BODY'+b.length+': '+b.slice(0,250)); } }catch(e){}
  }
});
await page.goto('https://careers.tiktok.com/search?location=Singapore', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
await page.waitForTimeout(10000);
const fs=await import('fs');
fs.writeFileSync('/tmp/tt_api.json', JSON.stringify(api,null,1));
console.log(api.join('\n'));
await browser.close();