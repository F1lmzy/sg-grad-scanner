import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: 'Mozilla/5.0 Chrome/125.0', viewport:{width:1400,height:1000} });
const page = await ctx.newPage();
const url='https://careers.gf.com/search/?q=Associate%20Engineer&locationsearch=Singapore&searchResultView=LIST&facetFilters=%7B%22custCountryRegion%22%3A%5B%22Singapore%22%5D%7D';
await page.goto(url,{waitUntil:'domcontentloaded',timeout:60000}).catch(()=>{});
for(const lbl of ['Accept All Cookies','Accept All']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:3000}).catch(()=>{}); await page.waitForTimeout(1500); break; } }
await page.waitForTimeout(10000);
for(let i=0;i<12;i++){ await page.evaluate(()=>window.scrollBy(0,700)); await page.waitForTimeout(250); }
await page.waitForTimeout(3000);
const text=await page.evaluate(()=>document.body?document.body.innerText:'');
const links=await page.evaluate(()=>Array.from(document.querySelectorAll('a')).filter(a=>/jobs\/|job|requisition/i.test(a.href)).map(a=>({t:(a.innerText||'').trim().replace(/\s+/g,' '),h:a.href})).slice(0,40));
const fs=await import('fs');
fs.writeFileSync('/tmp/gf_assoc.txt',text);
fs.writeFileSync('/tmp/gf_assoc.json',JSON.stringify(links,null,1));
const lines=text.split('\n').map(x=>x.trim()).filter(Boolean);
console.log('LINES',lines.length);
for(const l of lines.filter(x=>/Associate|Equipment|Engineer|Lithography|Clean/i.test(x)).slice(0,20)) console.log('-',l);
console.log('LINKS', JSON.stringify(links.filter(l=>/Associate|Engineer/i.test(l.t)).slice(0,10),null,1));
await browser.close();