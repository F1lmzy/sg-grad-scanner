const { chromium } = require('/home/kavin/.npm/_npx/e41f203b7505f1fb/node_modules/playwright');
const url = process.argv[2];
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: '/home/kavin/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome', args: ['--no-sandbox'] });
  const page = await browser.newPage({ userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36', viewport: { width: 1280, height: 900 } });
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  } catch (e) { console.error('nav', e.message); }
  await page.waitForTimeout(6000);
  await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 800) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 250)); } });
  await page.waitForTimeout(3000);
  const text = await page.evaluate(() => document.body ? document.body.innerText : '');
  const urls = await page.evaluate(() => Array.from(document.querySelectorAll('a')).map(a => a.href).filter(h => h && /job|requisition|posting/i.test(h)).slice(0, 300));
  console.log('======PAGE-TEXT======');
  console.log(text);
  console.log('======JOB-URLS======');
  console.log([...new Set(urls.map(u => u.split('#')[0].replace(/\/$/, '')))].join('\n'));
  await browser.close();
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });