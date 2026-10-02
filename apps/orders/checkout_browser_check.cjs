const { chromium } = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const [base, cookieName, cookieValue, station, method, width] = process.argv.slice(2);
  const browser = await chromium.launch({headless:true, channel:process.env.CHECKOUT_BROWSER_CHANNEL || 'msedge'});
  try {
    const context = await browser.newContext({viewport:{width:Number(width),height:844}});
    await context.addCookies([{name:cookieName,value:cookieValue,url:base}]);
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const checkWidth = async () => {
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false,
        'Page must fit the viewport without horizontal scrolling');
    };
    await page.goto(base + '/orders/checkout/');
    const mobile = true; // Four-step checkout applies at every viewport width.
    assert.equal(await page.locator('.commerce-steps').isVisible(), true);
    const title = await page.locator('.checkout-title-block h1').boundingBox();
    assert(title.width > 180 && title.height < 90, 'Checkout heading must wrap in whole words');
    const contact = await page.locator('.checkout-contact-header').boundingBox();
    assert(contact.height < 200, 'Contact header must fit its card');
    await checkWidth();
    await page.locator('#id_first_name').fill('Browser buyer');
    await page.locator('#id_mobile').fill('0701234567');
    if (mobile) {
      // Enter should advance, without locking the actual submit button.
      await page.locator('#id_mobile').press('Enter');
      await page.waitForFunction(() => document.getElementById('checkoutForm').dataset.mobileStep === '1');
      await page.goBack();
      await page.waitForFunction(() => document.getElementById('checkoutForm').dataset.mobileStep === '0');
      assert.equal(await page.locator('#id_first_name').inputValue(), 'Browser buyer');
      await page.goForward();
      await page.waitForFunction(() => document.getElementById('checkoutForm').dataset.mobileStep === '1');
    }
    await page.locator('#shipPickup').check();
    await page.locator('#id_pickup_station').selectOption(station);
    await page.waitForFunction(() => document.getElementById('checkoutForm').dataset.quoteState === 'ready');
    assert.equal(await page.locator('#placeOrderBtn').isDisabled(), false);
    if (mobile) await page.locator('#mobileCheckoutAction').click();
    await checkWidth();
    await page.locator('#mobileMoney').check();
    await page.locator('#id_mobile_money_number').fill('123');
    if (method === 'cod') {
      await page.locator('#cashOnDelivery').check();
      assert.equal(await page.locator('#id_mobile_money_number').isDisabled(), true);
    } else {
      if (mobile) {
        await page.locator('#mobileCheckoutAction').click();
        assert.equal(await page.locator('#checkoutForm').getAttribute('data-mobile-step'), '2');
        assert.equal(await page.locator('#placeOrderBtn').isDisabled(), false);
      }
      await page.locator('#id_mobile_money_number').fill('0772000000');
      await page.locator('#id_payment_evidence').fill('TEST-MM-REFERENCE');
    }
    if (mobile) await page.locator('#mobileCheckoutAction').click();
    await checkWidth();
    await Promise.all([
      page.waitForURL(/\/orders\/.*confirmation|\/orders\/order-confirmation/, {timeout:15000}),
      page.locator(mobile ? '#mobileCheckoutAction' : '#placeOrderBtn').click()
    ]);
    await page.locator('#confirmationTitle').waitFor();
    await checkWidth();
    assert.deepEqual(errors, []);
    console.log('Browser checkout passed: ' + method + ' at ' + width + 'px');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
