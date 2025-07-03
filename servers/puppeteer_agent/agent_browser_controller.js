const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const RecaptchaPlugin = require('puppeteer-extra-plugin-recaptcha');
const AdblockerPlugin = require('puppeteer-extra-plugin-adblocker');
const AnonymizeUAPlugin = require('puppeteer-extra-plugin-anonymize-ua');
const BlockResourcesPlugin = require('puppeteer-extra-plugin-block-resources');
const UserPrefsPlugin = require('puppeteer-extra-plugin-user-preferences');
const DevtoolsPlugin = require('puppeteer-extra-plugin-devtools');
const REPLPlugin = require('puppeteer-extra-plugin-repl');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');

const DEBUG_PORT = 9222;
const DEBUG_HOST = '127.0.0.1';
const CHROME_PROFILE = '/chrome-profile';
const SCREENSHOT_DIR = '/app/screenshots';
const BROWSER_URL = `http://${DEBUG_HOST}:${DEBUG_PORT}`;

puppeteer.use(StealthPlugin());
puppeteer.use(RecaptchaPlugin({
  provider: { id: '2captcha', token: 'YOUR_2CAPTCHA_API_KEY' },
  visualFeedback: true
}));
puppeteer.use(AdblockerPlugin({ blockTrackers: true }));
puppeteer.use(AnonymizeUAPlugin());
puppeteer.use(BlockResourcesPlugin({ blockedTypes: new Set(['image', 'media', 'font']) }));
puppeteer.use(UserPrefsPlugin({
  userPrefs: {
    homepage: 'https://example.com',
    download: {
      prompt_for_download: false,
      default_directory: '/tmp/downloads'
    }
  }
}));
puppeteer.use(DevtoolsPlugin());
puppeteer.use(REPLPlugin());

function launchChromeVisible() {
  const chromeCmd = [
    'google-chrome',
    `--remote-debugging-port=${DEBUG_PORT}`,
    `--remote-debugging-address=0.0.0.0`,
    `--user-data-dir=${CHROME_PROFILE}`,
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--start-maximized'
  ].join(' ');

  console.log('[+] Launching Chrome...');
  exec(chromeCmd, (err, stdout, stderr) => {
    if (err) console.error(`[!] Chrome launch error: ${err.message}`);
    if (stderr) console.error(`[Chrome STDERR]: ${stderr}`);
  });
}

async function waitForChrome(timeout = 15000) {
  console.log('[*] Waiting for Chrome DevTools endpoint...');
  const start = Date.now();

  return new Promise((resolve, reject) => {
    const check = () => {
      http.get(`${BROWSER_URL}/json/version`, res => {
        if (res.statusCode === 200) {
          console.log('[✓] Chrome DevTools is ready.');
          resolve();
        } else retry();
      }).on('error', retry);
    };

    const retry = () => {
      if (Date.now() - start > timeout) {
        return reject(new Error('[X] Timed out waiting for Chrome DevTools'));
      }
      setTimeout(check, 500);
    };

    check();
  });
}

async function runAgentInteraction(task = 'search-google') {
  await waitForChrome();

  const browser = await puppeteer.connect({
    browserURL: BROWSER_URL,
    defaultViewport: null
  });

  const page = await browser.newPage();

  if (task === 'search-google') {
    await page.goto('https://www.google.com');
    await page.waitForSelector('input[name="q"]');
    await page.type('input[name="q"]', 'puppeteer extra browser agent', { delay: 100 });
    await page.keyboard.press('Enter');
    await page.waitForNavigation({ waitUntil: 'domcontentloaded' });
    const firstLink = await page.$('h3');
    if (firstLink) await firstLink.click();
    await page.waitForTimeout(3000);
  }

  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  const screenshotPath = path.join(SCREENSHOT_DIR, `shot-${Date.now()}.png`);
  await page.screenshot({ path: screenshotPath });

  console.log(`[✓] Task complete. Screenshot: ${screenshotPath}`);
  console.log(`[✓] Final URL: ${page.url()}`);
  console.log(`[✓] Page title: ${await page.title()}`);
}

(async () => {
  try {
    launchChromeVisible();
    await runAgentInteraction();
  } catch (err) {
    console.error('[!] Agent failure:', err);
  }
})();
