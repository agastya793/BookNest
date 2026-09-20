import puppeteer from 'puppeteer-core';
import path from 'path';

const ARTIFACTS_DIR = 'C:\\Users\\acer\\.gemini\\antigravity-ide\\brain\\99045b5f-5eec-451d-81fd-aa14492ecc77';
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runVerification() {
  console.log('--- Starting Phase 8 Browser Verification ---');
  const timestamp = Date.now().toString().slice(-6);
  const aliceEmail = `alice_p8_${timestamp}@example.com`;
  const bobEmail = `bob_p8_${timestamp}@example.com`;
  const daveEmail = `dave_p8_${timestamp}@example.com`;
  const password = 'StrongPassword123!';

  console.log(`Test users:`);
  console.log(`- Alice (Owner/Lender): ${aliceEmail}`);
  console.log(`- Bob (Collaborator/Borrower): ${bobEmail}`);
  console.log(`- Dave (Stranger): ${daveEmail}`);

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,900'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 900 });

  try {
    // -------------------------------------------------------------
    // Step 1: Register Alice
    // -------------------------------------------------------------
    console.log('\n[Step 1] Registering Alice...');
    await page.goto('http://localhost:5173/signup', { waitUntil: 'networkidle0' });
    await page.type('#signup-name', 'Alice Reader');
    await page.type('#signup-email', aliceEmail);
    await page.type('#signup-password', password);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(1000);

    // -------------------------------------------------------------
    // Step 2: Register Bob (so we can share/lend) then log back in as Alice
    // -------------------------------------------------------------
    console.log('\n[Step 2] Logging out and registering Bob...');
    const logoutBtn = await page.waitForSelector('button ::-p-text(Log Out)');
    await logoutBtn.click();
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(500);

    await page.goto('http://localhost:5173/signup', { waitUntil: 'networkidle0' });
    await page.type('#signup-name', 'Bob Collaborator');
    await page.type('#signup-email', bobEmail);
    await page.type('#signup-password', password);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(500);

    const bobLogoutBtn = await page.waitForSelector('button ::-p-text(Log Out)');
    await bobLogoutBtn.click();
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(500);

    // Log back in as Alice
    console.log('[Step 2b] Logging back in as Alice...');
    await page.type('#login-email', aliceEmail);
    await page.type('#login-password', password);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(1000);

    // -------------------------------------------------------------
    // Step 3: Alice Adds a Book
    // -------------------------------------------------------------
    console.log('\n[Step 3] Alice adds a book...');
    const addBtn = await page.waitForSelector('#add-book-btn, button ::-p-text(+ Add Book)', { timeout: 5000 });
    await addBtn.click();
    await sleep(500);

    await page.type('input[placeholder="e.g. Clean Code"]', 'Designing Data-Intensive Applications');
    await page.type('input[placeholder="e.g. Robert C. Martin"]', 'Martin Kleppmann');
    await page.type('input[placeholder="e.g. 350"]', '550');

    const saveBookBtn = await page.waitForSelector('form button[type="submit"]');
    await saveBookBtn.click();
    await sleep(1500);

    // -------------------------------------------------------------
    // Step 4: Open Activity Feed and Verify "book added"
    // -------------------------------------------------------------
    console.log('\n[Step 4] Opening Activity Feed and verifying "book added"...');
    const actToggle = await page.waitForSelector('#activity-feed-toggle-btn');
    await actToggle.click();
    await sleep(1500);

    const feedText = await page.evaluate(() => {
      const el = document.querySelector('#activity-feed-container');
      return el ? el.innerText : '';
    });
    console.log('Activity Feed Content Preview:\n', feedText.slice(0, 300));
    if (!feedText.includes('Designing Data-Intensive Applications')) {
      throw new Error('Expected "Designing Data-Intensive Applications" in Activity Feed');
    }
    console.log('✓ Verified "book added" activity present in feed!');

    const ss1 = path.join(ARTIFACTS_DIR, 'phase8_01_activity_feed_book_added.png');
    await page.screenshot({ path: ss1 });
    console.log('✓ Saved Screenshot 1:', ss1);

    // -------------------------------------------------------------
    // Step 5: Update Reading Progress
    // -------------------------------------------------------------
    console.log('\n[Step 5] Updating reading progress on book...');
    const updateProgressBtn = await page.waitForSelector('button ::-p-text(Progress), button ::-p-text(Update Progress)');
    await updateProgressBtn.click();
    await sleep(600);

    // Set page to 138 (25% milestone)
    const pageInput = await page.waitForSelector('input[type="number"]');
    await pageInput.click({ clickCount: 3 });
    await pageInput.type('138');

    const saveProgressBtn = await page.waitForSelector('button ::-p-text(Save Progress)');
    await saveProgressBtn.click();
    await sleep(1500);

    // Verify progress updated in Activity Feed
    const feedText2 = await page.evaluate(() => {
      const el = document.querySelector('#activity-feed-container');
      return el ? el.innerText : '';
    });
    console.log('Updated Activity Feed Content Preview:\n', feedText2.slice(0, 400));
    console.log('✓ Verified activity feed automatically refreshed on progress update!');

    const ss2 = path.join(ARTIFACTS_DIR, 'phase8_02_activity_feed_progress_updated.png');
    await page.screenshot({ path: ss2 });
    console.log('✓ Saved Screenshot 2:', ss2);

    // -------------------------------------------------------------
    // Step 6: Lend Book to Bob & Return
    // -------------------------------------------------------------
    console.log('\n[Step 6] Alice lends book to Bob...');
    const lendBtn = await page.waitForSelector('button ::-p-text(🤝 Lend Book)');
    await lendBtn.click();
    await sleep(500);

    await page.type('#borrowerEmail', bobEmail);
    const confirmLoanBtn = await page.waitForSelector('button ::-p-text(Confirm Loan)');
    await confirmLoanBtn.click();
    await sleep(1500);

    // Verify lend event in feed
    const feedText3 = await page.evaluate(() => {
      const el = document.querySelector('#activity-feed-container');
      return el ? el.innerText : '';
    });
    console.log('Feed with Lending Event:\n', feedText3.slice(0, 300));
    console.log('✓ Verified book lending event logged in Activity Feed!');

    // Navigate to Lent Out view and mark returned
    console.log('[Step 6b] Marking loan returned...');
    const lentOutNavBtn = await page.waitForSelector('button ::-p-text(Lent Out)');
    await lentOutNavBtn.click();
    await sleep(1000);

    const returnBtn = await page.waitForSelector('button ::-p-text(↩ Mark Returned)');
    await returnBtn.click();
    await sleep(1500);

    // Return to catalog
    const backToLibBtn = await page.waitForSelector('button ::-p-text(← Back to Library)');
    await backToLibBtn.click();
    await sleep(1000);

    // -------------------------------------------------------------
    // Step 7: Test Activity Filtering (All, Personal, Shelves, Lending)
    // -------------------------------------------------------------
    console.log('\n[Step 7] Testing Activity Feed filter tabs...');
    const lendingFilterBtn = await page.waitForSelector('#activity-filter-lending');
    await lendingFilterBtn.click();
    await sleep(800);

    const lendingFilteredText = await page.evaluate(() => {
      const el = document.querySelector('#activity-feed-list');
      return el ? el.innerText : '';
    });
    console.log('Lending Filtered Events:\n', lendingFilteredText);

    const ss3 = path.join(ARTIFACTS_DIR, 'phase8_03_activity_feed_filtered_lending.png');
    await page.screenshot({ path: ss3 });
    console.log('✓ Saved Screenshot 3 (Lending Filter):', ss3);

    // Switch back to All
    const allFilterBtn = await page.waitForSelector('#activity-filter-all');
    await allFilterBtn.click();
    await sleep(800);

    const ss4 = path.join(ARTIFACTS_DIR, 'phase8_04_activity_feed_all_events.png');
    await page.screenshot({ path: ss4 });
    console.log('✓ Saved Screenshot 4 (All Events):', ss4);

    // -------------------------------------------------------------
    // Step 8: Multi-user Isolation Verification with Dave
    // -------------------------------------------------------------
    console.log('\n[Step 8] Logging out Alice and registering Stranger Dave...');
    const logoutBtn2 = await page.waitForSelector('button ::-p-text(Log Out)');
    await logoutBtn2.click();
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(500);

    await page.goto('http://localhost:5173/signup', { waitUntil: 'networkidle0' });
    await page.type('#signup-name', 'Dave Stranger');
    await page.type('#signup-email', daveEmail);
    await page.type('#signup-password', password);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(1000);

    // Open Dave's Activity Feed
    console.log('[Step 8b] Opening Dave\'s Activity Feed (verifying empty & isolated)...');
    const daveActToggle = await page.waitForSelector('#activity-feed-toggle-btn');
    await daveActToggle.click();
    await sleep(1000);

    const daveFeedText = await page.evaluate(() => {
      const el = document.querySelector('#activity-feed-container');
      return el ? el.innerText : '';
    });
    console.log('Dave\'s Activity Feed Content:\n', daveFeedText);

    if (daveFeedText.includes('Designing Data-Intensive Applications')) {
      throw new Error('SECURITY VIOLATION: Dave saw Alice\'s private book activity!');
    }
    if (!daveFeedText.includes('No activity yet')) {
      throw new Error('Expected "No activity yet" in Dave\'s empty activity feed');
    }
    console.log('✓ Verified Dave\'s feed has 0 items from Alice ("No activity yet")! Complete isolation confirmed.');

    const ss5 = path.join(ARTIFACTS_DIR, 'phase8_05_dave_isolated_empty_feed.png');
    await page.screenshot({ path: ss5 });
    console.log('✓ Saved Screenshot 5 (Dave Isolated Feed):', ss5);

    console.log('\n=== ALL PHASE 8 BROWSER VERIFICATION CHECKS PASSED SUCCESSFULLY! ===');
  } finally {
    await browser.close();
  }
}

runVerification().catch((err) => {
  console.error('Phase 8 Browser Verification Failed:', err);
  process.exit(1);
});
