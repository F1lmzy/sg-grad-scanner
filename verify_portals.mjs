import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';
const target = process.argv[2] || 'tiktok';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US', viewport:{width:1400,height:900} });
const page = await ctx.newPage();
const fs = await import('fs');
async function dump(label, wait=9000){
  await page.waitForTimeout(wait);
  for(let i=0;i<15;i++){ await page.evaluate(()=>window.scrollBy(0,800)); await page.waitForTimeout(250); }
  await page.waitForTimeout(3000);
  const text = await page.evaluate(()=>document.body?document.body.innerText:'');
  fs.writeFileSync(`/tmp/${label}.txt`, text);
  const lines = text.split('\n').map(x=>x.trim()).filter(Boolean);
  return lines;
}
if(target==='tiktok'){
  await page.goto('https://careers.tiktok.com/search?location=Singapore', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
  for(const lbl of ['Accept All','Accept','Agree','Yes']){ const b=page.locator(`button:has-text("${lbl}"),a:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); await page.waitForTimeout(1500); break; } }
  const l = await dump('tt_sg');
  const grad = l.filter(x=>/Graduate|Backend.*Engineer.*2027|AI.*Graduate|LIVE|Revenue/i.test(x));
  console.log('TT lines', l.length);
  console.log(grad.slice(0,30).join('\n'));
}
if(target==='avetics'){
  await page.goto('https://www.avetics.com/careers', { waitUntil:'domcontentloaded', timeout:45000 }).catch(()=>{});
  const l = await dump('avetics',7000);
  const rel = l.filter(x=>/Program Manager|Robotics|Junior|Engineer|Project/i.test(x));
  console.log('AVETICS total', l.length);
  console.log(rel.slice(0,25).join('\n'));
}
if(target==='gf'){
  await page.goto('https://careers.gf.com/careers?location=Singapore', { waitUntil:'domcontentloaded', timeout:60000 }).catch(()=>{});
  for(const lbl of ['Accept All','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); break; } }
  const l = await dump('gf',9000);
  const rel = l.filter(x=>/Associate Engineer|Equipment|Lithography|Clean/i.test(x));
  console.log('GF total', l.length);
  console.log(rel.slice(0,20).join('\n'));
}
await browser.close();