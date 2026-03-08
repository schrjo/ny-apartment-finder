// ==UserScript==
// @name         Airtable Form Apartment Collector (Reside)
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Collects Airtable form dropdown options and posts them to a local receiver.
// @match        https://airtable.com/appsseXTOVx59HC0W/pagcVengefPFQvMZC/form
// @grant        GM_xmlhttpRequest
// ==/UserScript==

(function() {
  'use strict';

  const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  const RECEIVER_URL = 'http://127.0.0.1:8765/airtable-form';
  const RECEIVER_TOKEN = ''; // optional: set to match AIRTABLE_FORM_RECEIVER_TOKEN

  function postSnapshot(items) {
    const payload = {
      items,
      sourceUrl: location.href,
      collectedAt: new Date().toISOString()
    };

    const headers = {
      'Content-Type': 'application/json'
    };
    if (RECEIVER_TOKEN) headers['X-Token'] = RECEIVER_TOKEN;

    if (typeof GM_xmlhttpRequest === 'function') {
      GM_xmlhttpRequest({
        method: 'POST',
        url: RECEIVER_URL,
        headers,
        data: JSON.stringify(payload),
        onload: () => console.log('✅ Snapshot posted to receiver'),
        onerror: () => console.warn('⚠️ Failed posting snapshot')
      });
      return;
    }

    fetch(RECEIVER_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    }).then(() => console.log('✅ Snapshot posted to receiver'))
      .catch(() => console.warn('⚠️ Failed posting snapshot'));
  }

  async function collectApartments() {
    console.log('🚀 Collecting Airtable form dropdown options...');

    const addButton = document.querySelector('button[aria-label*="Add unit"]');
    if (!addButton) {
      console.error('❌ Add unit button not found.');
      return;
    }
    addButton.click();
    await wait(1000);

    const dropdown = document.querySelector('div[role="dialog"] [role="region"]');
    if (!dropdown) {
      console.error('❌ Dropdown region not found.');
      return;
    }

    const scrollContainer = dropdown;
    const scrollStep = 200;
    const seenTexts = new Set();

    scrollContainer.scrollTop = 0;
    await wait(700);

    let previousCount = 0;
    let attemptsWithoutNew = 0;

    while (attemptsWithoutNew < 3) {
      const items = scrollContainer.querySelectorAll('div[data-rowid] div.flex-auto.truncate');
      items.forEach(item => {
        const text = item.textContent.trim();
        if (text) seenTexts.add(text);
      });

      if (seenTexts.size === previousCount) {
        attemptsWithoutNew++;
      } else {
        attemptsWithoutNew = 0;
        previousCount = seenTexts.size;
      }

      scrollContainer.scrollTop = scrollContainer.scrollTop + scrollStep;
      await wait(700);
    }

    const currentList = Array.from(seenTexts);
    console.log(`✅ Collected ${currentList.length} options.`);

    postSnapshot(currentList);
  }

  window.addEventListener('load', async () => {
    await wait(3000);
    await collectApartments();
  });
})();
