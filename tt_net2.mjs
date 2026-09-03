import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
const api=[];
page.on('request', r=>{
  const u=r.url();
  if(/supplier\/search\/job\/posts/.test(u)){
    api.push('REQ '+r.method()+' '+u+' BODY='+ (r.postData()||''));
  }
});
page.on('response', async r=>{
  const u=r.url();
  if(/supplier\/search\/job\/posts/.test(u)){
    try{ const b=await r.text(); api.push('RESP len='+b.length+' '+b.slice(0,2500)); }catch(e){ api.push('RESPERR '+e); }
  }
});
await page.goto('https://careers.tiktok.com/search?location=Singapore', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
await page.waitForTimeout(12000);
const fs=await import('fs');
fs.writeFileSync('/tmp/tt_api2.json', JSON.stringify(api,null,1));
console.log('calls', api.length); console.log(api.join('\n---\n').slice(0,4000));
await browser.close();