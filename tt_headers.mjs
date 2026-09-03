import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA });
const page = await ctx.newPage();
page.on('request', r=>{
  if(/supplier\/search\/job\/posts/.test(r.url())){
    console.log('URL', r.url());
    console.log('HEADERS', JSON.stringify(r.headers()));
    console.log('BODY', JSON.stringify(r.postData()||''));
    console.log('====');
  }
});
await page.goto('https://lifeattiktok.com/search', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
await page.waitForTimeout(12000);
await browser.close();