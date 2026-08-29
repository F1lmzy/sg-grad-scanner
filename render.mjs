import { chromium } from 'playwright';
import fs from 'fs';

const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36';

export async function renderLinks(url, waitMs = 6000, scroll = true) {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US' });
  const page = await ctx.newPage();
  let text = '', links = [];
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForTimeout(2500);
    for (let i = 0; i < 14; i++) {
      await page.evaluate(() => window.scrollBy(0, 900));
      await page.waitForTimeout(250);
    }
    await page.waitForTimeout(waitMs);
    text = await page.evaluate(() => document.body ? document.body.innerText : '');
    links = await page.evaluate(() =>
      Array.from(document.querySelectorAll('a')).map(a => ({ text: (a.innerText||'').trim(), href: a.href }))
        .filter(l => /job-detail|job|position|detail/i.test(l.href))
    );
  } catch (e) { text = 'RENDER_ERROR: ' + e.message; }
  finally { await browser.close(); }
  return { text, links };
}

if (process.argv[1] && process.argv[1].endsWith('render.mjs')) {
  const mode = process.argv[2];
  const url = process.argv[3];
  const out = process.argv[4];
  const waitMs = process.argv[5] ? parseInt(process.argv[5]) : 6000;
  if (mode === 'links') {
    const { text, links } = await renderLinks(url, waitMs);
    if (out) { fs.writeFileSync(out + '.txt', text); fs.writeFileSync(out + '.links.json', JSON.stringify(links, null, 1)); console.log('WROTE', out + '.txt', text.length, '+', out + '.links.json', links.length); }
    else console.log(JSON.stringify(links, null, 1));
  } else {
    const text = await renderLinks(url, waitMs).then(r => r.text);
    if (out) { fs.writeFileSync(out, text); console.log('WROTE ' + out + ' bytes=' + text.length); }
    else console.log(text);
  }
}