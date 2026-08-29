import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const which = process.argv[2] || 'all';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
const fs = await import('fs');
async function get(url, label, wait=9000){
  await page.goto(url, { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
  for(const lbl of ['Accept All Cookies','Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); await page.waitForTimeout(1500); break; } }
  await page.waitForTimeout(wait);
  for(let i=0;i<12;i++){ await page.evaluate(()=>window.scrollBy(0,700)); await page.waitForTimeout(250); }
  await page.waitForTimeout(3000);
  const text = await page.evaluate(()=>document.body?document.body.innerText:'');
  fs.writeFileSync(`/tmp/${label}.txt`, text);
  console.log(`=== ${label} lines=${text.split('\n').length}`);
}
if(which==='gf'||which==='all') await get('https://careers.gf.com/careers?location=Singapore','gf',9000);
if(which==='keppel'||which==='all') await get('https://keppel.wd3.myworkdayjobs.com/en-US/KeppelCareers','keppel',12000);
await browser.close();