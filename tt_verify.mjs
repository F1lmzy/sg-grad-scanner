import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
await page.goto('https://careers.tiktok.com/position/7678993627393296693/detail', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
for(const lbl of ['Accept all','Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:2500}).catch(()=>{}); break; } }
await page.waitForTimeout(12000);
const info=await page.evaluate(()=>{
  const txt=document.body.innerText;
  const has=re=>re.test(txt);
  const line=(re)=>{ const m=txt.match(re); return m?m[0].trim().slice(0,160):null; };
  return { url:location.href,
    titleLine: line(/AI Data Strategy[^\n]*/i),
    hasSingapore: has(/Singapore/),
    locLine: line(/(?:Singapore|Location)[^\n]{0,60}/i),
    hasGraduate2027: has(/2027 Start|Graduate/i),
    bodyFirst: txt.slice(0,250) };
});
console.log(JSON.stringify(info,null,1));
await browser.close();