import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
await page.goto('https://lifeattiktok.com/search', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
await page.waitForTimeout(10000);
const info = await page.evaluate(()=>{
  const inputs=[...document.querySelectorAll('input,textarea,select')].map(i=>({tag:i.tagName,type:i.type,ph:i.placeholder,id:i.id,cls:i.className.slice(0,40)}));
  const buttons=[...document.querySelectorAll('button')].map(b=>b.innerText.trim().slice(0,30)).filter(Boolean).slice(0,30);
  return {inputs, buttons, url:location.href, h2:[...document.querySelectorAll('a h2,a div.font, h2')].slice(0,20).map(e=>e.innerText.trim().slice(0,80))};
});
console.log(JSON.stringify(info,null,1));
await browser.close();