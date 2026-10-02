// Isolated template UI check; no live orders, payments, or database writes.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    for (const width of [320, 390, 768, 1440]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      let html = fs.readFileSync('templates/orders/checkout.html', 'utf8');
      html = html.slice(html.indexOf('<noscript>'), html.indexOf('{{ checkout_addresses|json_script'));
      html = html.replace(/{{\s*form\.(\w+)\s*}}/g, (_, name) =>
        `<input id="id_${name}" ${['first_name', 'mobile'].includes(name) ? 'required' : ''}>`);
      html = html.replace('{{ cart.items.count }}', '1');
      html = html.replace(/{%[\s\S]*?%}/g, '').replace(/{{[\s\S]*?}}/g, '');
      await page.route('http://checkout.test/**', route => route.fulfill({
        body: '<body class="commerce-app commerce-checkout"><a data-mobile-back>Back</a>' + html,
        contentType: 'text/html',
      }));
      await page.goto('http://checkout.test/');
      // Include shared rules: storefront's ID selectors previously crushed the header.
      for (const stylesheet of ['users.css', 'account_pages.css', 'storefront.css', 'shopping.css', 'commerce_mobile.css', 'checkout.css']) {
        await page.addStyleTag({ content: fs.readFileSync('static/css/' + stylesheet, 'utf8') });
      }
      await page.evaluate(() => {
        document.querySelector('#checkoutForm').dataset.quoteState = 'ready';
        document.querySelector('#placeOrderBtn').disabled = false;
        document.querySelectorAll('.checkout-error').forEach(error => error.remove());
        document.querySelector('#cashOnDelivery').checked = true;
        document.querySelector('#shipDelivery').checked = true;
      });
      await page.addScriptTag({ content: fs.readFileSync('static/js/commerce_mobile.js', 'utf8') });
      await page.evaluate(() => document.dispatchEvent(new Event('DOMContentLoaded')));
      assert(await page.locator('.commerce-steps').isVisible());
      const hero = await page.locator('.checkout-hero').boundingBox();
      const heroTitle = await page.locator('.checkout-title-block h1').boundingBox();
      const itemCount = await page.locator('.checkout-pill').boundingBox();
      assert(heroTitle.width > 180, 'Checkout heading must have enough room for whole words');
      assert(heroTitle.height < 90, 'Checkout heading must not wrap into a tall column');
      assert(itemCount.x + itemCount.width <= hero.x + hero.width + 1, 'Item count must stay within the header');
      if (width <= 575) {
        assert(itemCount.y >= heroTitle.y + heroTitle.height, 'Small screens should put the item count below the title');
        assert(heroTitle.width >= hero.width - 1, 'Small-screen title must use the full header width');
      }
      const header = await page.locator('.checkout-contact-header').boundingBox();
      const title = await page.locator('#contactHeading').boundingBox();
      const description = await page.locator('#contactSummaryText').boundingBox();
      assert(title.width >= header.width - 140, 'Contact title should use the available header width');
      assert(header.height < 200, 'Contact header should stay compact');
      assert(description.x + description.width <= header.x + header.width, 'Description should fit inside the card');
      await page.locator('#mobileCheckoutAction').click();
      assert.equal(await page.locator('#checkoutForm').getAttribute('data-mobile-step'), '0');
      await page.locator('#id_first_name').fill('Buyer');
      await page.locator('#id_mobile').fill('0701234567');
      await page.locator('#mobileCheckoutAction').click();
      assert(await page.locator('#shippingSection').isVisible());
      await page.locator('#shipPickup').check();
      assert(!await page.locator('#addressSection').isVisible());
      await page.locator('#id_pickup_station').fill('1');
      await page.locator('#mobileCheckoutAction').click();
      assert(await page.locator('#paymentSection').isVisible());
      await page.locator('#mobileCheckoutAction').click();
      assert(await page.locator('#orderSummary').isVisible());
      assert((await page.locator('#checkoutReviewContact').textContent()).includes('Buyer'));
      await page.locator('#checkoutPrevious').click();
      assert(await page.locator('#paymentSection').isVisible());
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      assert.deepEqual(errors, []);
      console.log(`Checkout layout and step navigation passed at ${width}px`);
      await page.close();
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
