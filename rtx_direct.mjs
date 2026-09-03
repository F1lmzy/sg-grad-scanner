import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
await page.goto('https://careers.rtx.com/global/en/job/01847809/Operations-Engineering-Associate', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept All','Accept all','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:2500}).catch(()=>{}); break; } }
await page.waitForTimeout(11000);
const info=await page.evaluate(()=>{
  const t=document.body.innerText;
  return { url:location.href, title:(t.match(/Operations Engineering Associate[^\n]*/i)||[null])[0]?.slice(0,120)||null,
    hasSingapore:/Singapore/.test(t), sample:t.slice(0,300) };
}).catch(e=>({err:String(e)}));
console.log(JSON.stringify(info,null,1));
await browser.close();