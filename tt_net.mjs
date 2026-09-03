import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
const api=[];
page.on('response', async r=>{
  const u=r.url();
  if(/position|job|search|api|graphql|supplier/i.test(u)&&!/\.(png|jpg|css|js|woff|svg)/.test(u)){
    try{ const ct=r.headers()['content-type']||''; let body=''; if(/json|text/.test(ct)){ body=(await r.text()).slice(0,400);} api.push(r.method()+' '+u+' ['+ct+'] '+String(body.length)); api.push('  '+body.replace(/\n/g,' ')); }catch(e){ api.push('ERR '+u); }
  }
});
await page.goto('https://careers.tiktok.com/search?location=Singapore', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
await page.waitForTimeout(15000);
const info = await page.evaluate(()=>({url:location.href, bodyLen:document.body.innerText.length, sample:document.body.innerText.slice(0,500)}));
console.log('PAGE', JSON.stringify(info));
const fs=await import('fs');
fs.writeFileSync('/tmp/tt_api.json', JSON.stringify(api,null,1));
console.log('API calls:'); console.log(api.slice(0,40).join('\n'));
await browser.close();