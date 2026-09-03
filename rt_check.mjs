import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 Chrome/125.0';
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, viewport:{width:1400,height:900} });
const page = await ctx.newPage();
const out=[];

// Collins / RTX phenom - search SG graduate
async function rtx(){
  const urls = [
    'https://careers.rtx.com/global/en/search-results?keywords=associate&locationsearch=Singapore',
    'https://careers.rtx.com/global/en/search-results?locationsearch=Singapore'
  ];
  for(const u of urls){
    await page.goto(u,{waitUntil:'domcontentloaded',timeout:60000}).catch(()=>{});
    for(const lbl of ['Accept All','Accept all','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:2000}).catch(()=>{}); break; } }
    await page.waitForTimeout(10000);
    const items=await page.evaluate(()=>{
      const hits=[];
      for(const a of document.querySelectorAll('a[href*="/job/"]')){
        const t=(a.innerText||'').trim().replace(/\s+/g,' ');
        if(t && /[A-Za-z]{3}/.test(t)) hits.push({t:hits.length>60?null:t.slice(0,90), href:(a.getAttribute('href')||'').slice(-25)});
      }
      return hits.filter(x=>x.t);
    });
    if(items.length){ out.push({portal:'RTX', u, items:items.slice(0,60)}); break; }
  }
}
await rtx();

// Keppel workday - grad/associate SG
async function keppel(){
  await page.goto('https://keppel.wd3.myworkdayjobs.com/en-US/KeppelCareers',{waitUntil:'domcontentloaded',timeout:60000}).catch(()=>{});
  await page.waitForTimeout(8000);
  const items=await page.evaluate(()=>{
    const txt=document.body.innerText;
    const lines=txt.split('\n').map(s=>s.trim()).filter(s=>/associate|graduate|engineer|junior/i.test(s));
    return {hasAhrefs:document.querySelectorAll('a[href*="/job/"]').length, bodyLen:txt.length, sample:lines.slice(0,25)};
  }).catch(e=>({err:String(e)}));
  out.push({portal:'Keppel/workday', items});
}

await keppel();

// AbbVie smartrecruiters maintenance engineer trainee page (status)
async function abbvie(){
  await page.goto('https://careers.abbvie.com/en/job/maintenance-engineer-trainee-attach-and-train-program-in-singapore-sg-jid-32373',{waitUntil:'domcontentloaded',timeout:60000}).catch(()=>{});
  for(const lbl of ['Accept All','Accept all','Accept']){ const b=page.locator(`button:has-text("${lbl}")`); if(await b.count()){ await b.first().click({timeout:2000}).catch(()=>{}); break; } }
  await page.waitForTimeout(9000);
  const txt=await page.evaluate(()=>{ const t=document.body.innerText; return {len:t.length, titleMatch:t.match(/Maintenance Engineer Trainee[^\n]*/i)?t.match(/Maintenance Engineer Trainee[^\n]*/i)[0].slice(0,120):null, expireMatch:(t.match(/expire[^\n]*/i)||[null])[0]}; }).catch(e=>({err:String(e)}));
  out.push({portal:'AbbVie/smartrecruiters', txt});
}
await abbvie();

const fs=await import('fs');
fs.writeFileSync('/tmp/rt_check.json', JSON.stringify(out,null,1));
console.log(JSON.stringify(out,null,1).slice(0,3000));
await browser.close();