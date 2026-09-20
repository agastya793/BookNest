import puppeteer from 'puppeteer-core';
import path from 'path';

const ARTIFACTS_DIR = 'C:\\Users\\acer\\.gemini\\antigravity-ide\\brain\\01381e64-5a8f-4e8f-accb-b1a084ea5a84';
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runMultiBrowserVerification() {
  console.log('===============================================================');
  console.log('--- STARTING MULTI-BROWSER REAL-TIME VERIFICATION (PHASE 9) ---');
  console.log('===============================================================');

  const timestamp = Date.now().toString().slice(-6);
  const aliceEmail = `alice_live_${timestamp}@example.com`;
  const bobEmail = `bob_live_${timestamp}@example.com`;
  const password = 'StrongPassword123!';

  console.log(`Test Sessions:`);
  console.log(`- Chrome A (User A / Owner / Lender): Alice Reader (${aliceEmail})`);
  console.log(`- Chrome B (User B / Collaborator / Borrower): Bob Collaborator (${bobEmail})`);

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--window-size=1400,950',
      '--disable-dev-shm-usage',
    ],
  });

  // Create two completely isolated browser contexts (Chrome A & Chrome B)
  const contextA = await browser.createBrowserContext();
  const contextB = await browser.createBrowserContext();

  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();

  await pageA.setViewport({ width: 1400, height: 950 });
  await pageB.setViewport({ width: 1400, height: 950 });

  // Auto-accept any confirm dialogs on both pages
  pageA.on('dialog', async (dialog) => {
    console.log(`[Chrome A Dialog] Auto-accepting: "${dialog.message()}"`);
    await dialog.accept();
  });

  pageB.on('dialog', async (dialog) => {
    console.log(`[Chrome B Dialog] Auto-accepting: "${dialog.message()}"`);
    await dialog.accept();
  });

  try {
    // -----------------------------------------------------------------
    // SETUP: Register Alice (Chrome A) and Bob (Chrome B)
    // -----------------------------------------------------------------
    console.log('\n[Setup 1] Registering Alice on Chrome A...');
    await pageA.goto('http://localhost:5173/signup', { waitUntil: 'networkidle0' });
    await pageA.type('#signup-name', 'Alice Reader');
    await pageA.type('#signup-email', aliceEmail);
    await pageA.type('#signup-password', password);
    await pageA.click('button[type="submit"]');
    await pageA.waitForNavigation({ waitUntil: 'networkidle0' });

    console.log('[Setup 2] Registering Bob on Chrome B...');
    await pageB.goto('http://localhost:5173/signup', { waitUntil: 'networkidle0' });
    await pageB.type('#signup-name', 'Bob Collaborator');
    await pageB.type('#signup-email', bobEmail);
    await pageB.type('#signup-password', password);
    await pageB.click('button[type="submit"]');
    await pageB.waitForNavigation({ waitUntil: 'networkidle0' });

    await sleep(1500);

    // Verify both sockets show "Live" connection badge
    console.log('[Setup 3] Verifying real-time status badges on both browser sessions...');
    const badgeA = await pageA.waitForSelector('#realtime-status-badge', { timeout: 5000 });
    const badgeAText = await pageA.evaluate((el) => el.innerText, badgeA);
    console.log(`- Chrome A status badge: "${badgeAText.trim()}"`);
    if (!badgeAText.includes('Live')) {
      throw new Error(`Expected Chrome A badge to be "Live", got "${badgeAText}"`);
    }

    const badgeB = await pageB.waitForSelector('#realtime-status-badge', { timeout: 5000 });
    const badgeBText = await pageB.evaluate((el) => el.innerText, badgeB);
    console.log(`- Chrome B status badge: "${badgeBText.trim()}"`);
    if (!badgeBText.includes('Live')) {
      throw new Error(`Expected Chrome B badge to be "Live", got "${badgeBText}"`);
    }
    console.log('✓ Both Chrome A & Chrome B connected to Socket.IO successfully!');

    // =================================================================
    // SCENARIO 1: A lends book to B -> B sees it without refresh
    // =================================================================
    console.log('\n===============================================================');
    console.log('>>> SCENARIO 1: A lends book to B -> B sees it without refresh');
    console.log('===============================================================');

    // 1a. On Chrome B, navigate to "Borrowed" tab
    console.log('[Scenario 1a] Bob (Chrome B) navigates to "Borrowed" view...');
    const bobBorrowedNavBtn = await pageB.waitForSelector('button ::-p-text(Borrowed)');
    await bobBorrowedNavBtn.click();
    await sleep(1000);

    const bInitialContent = await pageB.evaluate(() => document.body.innerText);
    if (!bInitialContent.includes('No Borrowed Books') && !bInitialContent.includes("You haven't borrowed any books")) {
      throw new Error('Expected Bob to initially have 0 borrowed books');
    }
    console.log('✓ Bob is on Borrowed view with 0 books ("No Borrowed Books").');

    // 1b. On Chrome A, add a book "Cloud Native Go"
    console.log('[Scenario 1b] Alice (Chrome A) adds book "Cloud Native Go"...');
    const addBookBtn = await pageA.waitForSelector('#add-book-btn, button ::-p-text(+ Add Book)');
    await addBookBtn.click();
    await sleep(600);

    await pageA.type('input[placeholder="e.g. Clean Code"]', 'Cloud Native Go');
    await pageA.type('input[placeholder="e.g. Robert C. Martin"]', 'Matthew Titmus');
    await pageA.type('input[placeholder="e.g. 350"]', '420');
    const saveBookBtn = await pageA.waitForSelector('form button[type="submit"]');
    await saveBookBtn.click();
    await sleep(1200);

    // 1c. Alice lends "Cloud Native Go" to Bob
    console.log(`[Scenario 1c] Alice lends "Cloud Native Go" to Bob (${bobEmail})...`);
    const lendBtn = await pageA.waitForSelector('button ::-p-text(🤝 Lend Book)');
    await lendBtn.click();
    await sleep(600);

    await pageA.type('#borrowerEmail', bobEmail);
    const confirmLoanBtn = await pageA.waitForSelector('button ::-p-text(Confirm Loan)');
    await confirmLoanBtn.click();
    await sleep(1000);
    console.log('✓ Alice submitted lend form successfully.');

    // 1d. Bob (Chrome B) MUST see the book appear LIVE WITHOUT REFRESH!
    console.log('[Scenario 1d] Checking Bob (Chrome B) WITHOUT ANY REFRESH...');
    let bookAppeared = false;
    for (let i = 0; i < 15; i++) {
      await sleep(500);
      const bText = await pageB.evaluate(() => document.body.innerText);
      if (bText.includes('Cloud Native Go') && bText.includes('Matthew Titmus')) {
        bookAppeared = true;
        console.log(`✓ LIVE SYNC CONFIRMED in Bob's browser after ${(i + 1) * 0.5}s!`);
        break;
      }
    }

    if (!bookAppeared) {
      throw new Error('FAIL: Bob did not see the borrowed book appear in real time without refresh!');
    }

    const ss1 = path.join(ARTIFACTS_DIR, 'phase9_01_user_b_live_borrowed_sync.png');
    await pageB.screenshot({ path: ss1 });
    console.log('✓ Saved Screenshot 1 (Bob live borrowed view):', ss1);

    // =================================================================
    // SCENARIO 2: A returns book -> B updates without refresh
    // =================================================================
    console.log('\n===============================================================');
    console.log('>>> SCENARIO 2: A returns book -> B updates without refresh');
    console.log('===============================================================');

    // 2a. Alice (Chrome A) navigates to "Lent Out" view and clicks "Mark Returned"
    console.log('[Scenario 2a] Alice navigates to "Lent Out" view and marks book as returned...');
    const lentOutNavBtn = await pageA.waitForSelector('button ::-p-text(Lent Out)');
    await lentOutNavBtn.click();
    await sleep(1000);

    const markReturnedBtn = await pageA.waitForSelector('button ::-p-text(↩ Mark Returned)');
    await markReturnedBtn.click();
    await sleep(1000);
    console.log('✓ Alice clicked "Mark Returned" successfully.');

    // 2b. Bob (Chrome B) MUST update to 0 borrowed books LIVE WITHOUT REFRESH!
    console.log('[Scenario 2b] Checking Bob (Chrome B) updates WITHOUT ANY REFRESH...');
    let bookDisappeared = false;
    for (let i = 0; i < 15; i++) {
      await sleep(500);
      const bText = await pageB.evaluate(() => document.body.innerText);
      if (bText.includes('No Borrowed Books') || !bText.includes('Cloud Native Go')) {
        bookDisappeared = true;
        console.log(`✓ LIVE RETURN CONFIRMED in Bob's browser after ${(i + 1) * 0.5}s!`);
        break;
      }
    }

    if (!bookDisappeared) {
      throw new Error('FAIL: Bob did not see the borrowed book disappear in real time without refresh!');
    }

    const ss2 = path.join(ARTIFACTS_DIR, 'phase9_02_user_b_live_return_sync.png');
    await pageB.screenshot({ path: ss2 });
    console.log('✓ Saved Screenshot 2 (Bob live return view):', ss2);

    // Reset Alice back to library catalog
    const backToLibBtn = await pageA.waitForSelector('button ::-p-text(← Back to Library)');
    await backToLibBtn.click();
    await sleep(800);

    // Reset Bob to All Books
    const bAllBooksBtn = await pageB.waitForSelector('button ::-p-text(All Books)');
    await bAllBooksBtn.click();
    await sleep(800);

    // =================================================================
    // SCENARIO 3: A adds book to shared shelf -> B sees shelf change without refresh
    // =================================================================
    console.log('\n===============================================================');
    console.log('>>> SCENARIO 3: A adds book to shared shelf -> B sees shelf change without refresh');
    console.log('===============================================================');

    // 3a. Alice creates shelf "Architecture Classics"
    console.log('[Scenario 3a] Alice creates shelf "Architecture Classics"...');
    const newShelfBtn = await pageA.waitForSelector('button ::-p-text(+ New Shelf)');
    await newShelfBtn.click();
    await sleep(500);

    const shelfInput = await pageA.waitForSelector('#shelf-name-input');
    await shelfInput.type('Architecture Classics');
    const saveShelfBtn = await pageA.waitForSelector('form button[type="submit"]');
    await saveShelfBtn.click();
    await sleep(1000);

    // 3b. Alice shares "Architecture Classics" with Bob as Editor
    console.log(`[Scenario 3b] Alice shares "Architecture Classics" with Bob (${bobEmail}) as Editor...`);
    const shareShelfBtn = await pageA.waitForSelector('button[title*="Manage collaborators"]');
    await shareShelfBtn.click();
    await sleep(600);

    const collabEmailInput = await pageA.waitForSelector('input[placeholder="registered.user@example.com"]');
    await collabEmailInput.type(bobEmail);
    const inviteBtn = await pageA.waitForSelector('button ::-p-text(+ Invite)');
    await inviteBtn.click();
    await sleep(1200);

    // Close share modal on Alice
    const closeShareModalBtn = await pageA.waitForSelector('button ::-p-text(Done)');
    await closeShareModalBtn.click();
    await sleep(600);
    console.log('✓ Shelf shared with Bob successfully.');

    // 3c. Bob (Chrome B) sees "Architecture Classics" under "Shared with me" WITHOUT REFRESH
    console.log('[Scenario 3c] Checking Bob (Chrome B) sees shared shelf WITHOUT REFRESH...');
    let shelfAppearedForBob = false;
    for (let i = 0; i < 15; i++) {
      await sleep(500);
      const bText = await pageB.evaluate(() => document.body.innerText);
      const bLower = bText.toLowerCase();
      if (bText.includes('Architecture Classics') && bLower.includes('shared with me')) {
        shelfAppearedForBob = true;
        console.log(`✓ Shared shelf appeared in Bob's sidebar after ${(i + 1) * 0.5}s!`);
        break;
      }
    }

    if (!shelfAppearedForBob) {
      throw new Error('FAIL: Bob did not see the shared shelf in sidebar without refresh!');
    }

    // 3d. Bob clicks "Architecture Classics" to select it and join room shelf_{shelf_id}
    console.log('[Scenario 3d] Bob selects "Architecture Classics" shelf (subscribing to room)...');
    const bobShelfRowBtn = await pageB.waitForSelector('button ::-p-text(Architecture Classics)');
    await bobShelfRowBtn.click();
    await sleep(1000);

    const bShelfText = await pageB.evaluate(() => document.body.innerText);
    console.log('Bob shelf initial view contains "No books on this shelf yet":', bShelfText.includes('No books on this shelf yet'));

    // 3e. Alice adds "Cloud Native Go" to "Architecture Classics"
    console.log('[Scenario 3e] Alice switches to "All Books" and assigns "Cloud Native Go" to "Architecture Classics"...');
    const aliceAllBooksBtn = await pageA.waitForSelector('button ::-p-text(All Books)');
    await aliceAllBooksBtn.click();
    await sleep(800);

    const manageShelvesBtn = await pageA.waitForSelector('button[title="Assign book to custom shelves"], button ::-p-text(📁 Shelves)');
    await manageShelvesBtn.click();
    await sleep(600);

    // Toggle the checkbox for Architecture Classics
    const archCheckbox = await pageA.waitForSelector('input[type="checkbox"]');
    await archCheckbox.click();
    await sleep(1000);

    // Close assign modal on Alice with "Done"
    const closeAssignBtn = await pageA.waitForSelector('button ::-p-text(Done)');
    await closeAssignBtn.click();
    await sleep(800);
    console.log('✓ Alice assigned book to shelf.');

    // 3f. Bob (Chrome B) MUST see the book appear on the shelf WITHOUT REFRESH!
    console.log('[Scenario 3f] Checking Bob (Chrome B) sees book on shelf WITHOUT ANY REFRESH...');
    let bookOnShelfAppeared = false;
    for (let i = 0; i < 15; i++) {
      await sleep(500);
      const bText = await pageB.evaluate(() => document.body.innerText);
      if (bText.includes('Cloud Native Go') && bText.includes('Architecture Classics')) {
        bookOnShelfAppeared = true;
        console.log(`✓ LIVE SHELF CHANGE CONFIRMED on Bob's screen after ${(i + 1) * 0.5}s!`);
        break;
      }
    }

    if (!bookOnShelfAppeared) {
      throw new Error('FAIL: Bob did not see the book appear on the shared shelf without refresh!');
    }

    const ss3 = path.join(ARTIFACTS_DIR, 'phase9_03_user_b_live_shared_shelf_sync.png');
    await pageB.screenshot({ path: ss3 });
    console.log('✓ Saved Screenshot 3 (Bob live shared shelf sync):', ss3);

    // =================================================================
    // SCENARIO 4: A removes B from shelf -> B loses access & stops receiving updates
    // =================================================================
    console.log('\n===============================================================');
    console.log('>>> SCENARIO 4: A removes B from shelf -> B loses access and stops receiving updates');
    console.log('===============================================================');

    // 4a. Alice opens Share modal on "Architecture Classics" and removes Bob
    console.log('[Scenario 4a] Alice removes Bob from "Architecture Classics"...');
    const shareShelfBtn2 = await pageA.waitForSelector('button[title*="Manage collaborators"]');
    await shareShelfBtn2.click();
    await sleep(800);

    const removeCollabBtn = await pageA.waitForSelector('button.btn-danger[title="Remove collaborator"], button.btn-danger ::-p-text(✕)');
    await removeCollabBtn.click();
    await sleep(1500);

    // Close modal on Alice
    const closeShareModalBtn2 = await pageA.waitForSelector('button ::-p-text(Done)');
    await closeShareModalBtn2.click();
    await sleep(800);
    console.log('✓ Alice removed Bob and confirmed dialog.');

    // 4b. Bob (Chrome B) MUST lose access immediately WITHOUT REFRESH
    // (selectedShelfId reset to null, shelf removed from sidebar)
    console.log('[Scenario 4b] Checking Bob (Chrome B) loses access WITHOUT ANY REFRESH...');
    let accessRevokedForBob = false;
    for (let i = 0; i < 15; i++) {
      await sleep(500);
      const bText = await pageB.evaluate(() => document.body.innerText);
      if (!bText.includes('Architecture Classics')) {
        accessRevokedForBob = true;
        console.log(`✓ LIVE ACCESS REVOCATION CONFIRMED on Bob's screen after ${(i + 1) * 0.5}s!`);
        break;
      }
    }

    if (!accessRevokedForBob) {
      throw new Error('FAIL: Bob did not lose access to the shelf in real time without refresh!');
    }

    // 4c. Verify Bob stops receiving future updates: Alice adds a new book to the shelf
    console.log('[Scenario 4c] Alice adds another book to "Architecture Classics" to test socket detachment...');
    const addBookBtn2 = await pageA.waitForSelector('#add-book-btn, button ::-p-text(+ Add Book)');
    await addBookBtn2.click();
    await sleep(600);

    await pageA.type('input[placeholder="e.g. Clean Code"]', 'Domain-Driven Design');
    await pageA.type('input[placeholder="e.g. Robert C. Martin"]', 'Eric Evans');
    await pageA.type('input[placeholder="e.g. 350"]', '560');
    const saveBookBtn2 = await pageA.waitForSelector('form button[type="submit"]');
    await saveBookBtn2.click();
    await sleep(1000);

    // Assign to Architecture Classics
    const manageShelvesBtns = await pageA.$$('button[title="Assign book to custom shelves"], button ::-p-text(📁 Shelves)');
    if (manageShelvesBtns.length > 0) {
      await manageShelvesBtns[0].click();
      await sleep(600);
      const chk = await pageA.waitForSelector('input[type="checkbox"]');
      await chk.click();
      await sleep(800);
      const cls = await pageA.waitForSelector('button ::-p-text(Done)');
      await cls.click();
      await sleep(600);
    }

    // Wait 2 seconds and ensure Bob still does NOT see "Architecture Classics" or "Domain-Driven Design"
    await sleep(2000);
    const bAfterText = await pageB.evaluate(() => document.body.innerText);
    if (bAfterText.includes('Architecture Classics') || bAfterText.includes('Domain-Driven Design')) {
      throw new Error('FAIL: Bob received updates for a revoked shelf!');
    }
    console.log('✓ Confirmed Bob received 0 future updates and remains completely detached!');

    const ss4 = path.join(ARTIFACTS_DIR, 'phase9_04_user_b_live_shelf_revocation_sync.png');
    await pageB.screenshot({ path: ss4 });
    console.log('✓ Saved Screenshot 4 (Bob revoked and detached):', ss4);

    // =================================================================
    // SCENARIO 5: A opens Activity Feed -> new activity appears without refresh
    // =================================================================
    console.log('\n===============================================================');
    console.log('>>> SCENARIO 5: A opens Activity Feed -> new activity appears without refresh');
    console.log('===============================================================');

    // 5a. Alice opens Activity Feed drawer
    console.log('[Scenario 5a] Alice opens Activity Feed...');
    const actToggleBtn = await pageA.waitForSelector('#activity-feed-toggle-btn');
    await actToggleBtn.click();
    await sleep(1200);

    const initialFeedText = await pageA.evaluate(() => {
      const el = document.querySelector('#activity-feed-container');
      return el ? el.innerText : '';
    });
    console.log('Alice initial Activity Feed snapshot:\n', initialFeedText.slice(0, 200));

    // 5b. Alice adds a new book "Building Microservices" while Activity Feed is open
    console.log('[Scenario 5b] Alice adds a new book "Building Microservices" while Activity Feed is open...');
    const addBookBtn3 = await pageA.waitForSelector('#add-book-btn, button ::-p-text(+ Add Book)');
    await addBookBtn3.click();
    await sleep(600);

    await pageA.type('input[placeholder="e.g. Clean Code"]', 'Building Microservices');
    await pageA.type('input[placeholder="e.g. Robert C. Martin"]', 'Sam Newman');
    await pageA.type('input[placeholder="e.g. 350"]', '280');
    const saveBookBtn3 = await pageA.waitForSelector('form button[type="submit"]');
    await saveBookBtn3.click();
    await sleep(1000);

    // 5c. Check that the Activity Feed on Chrome A updates LIVE WITHOUT REFRESH!
    console.log('[Scenario 5c] Checking Activity Feed on Chrome A WITHOUT ANY REFRESH...');
    let feedUpdatedLive = false;
    for (let i = 0; i < 15; i++) {
      await sleep(500);
      const currentFeedText = await pageA.evaluate(() => {
        const el = document.querySelector('#activity-feed-container');
        return el ? el.innerText : '';
      });
      if (currentFeedText.includes('Building Microservices')) {
        feedUpdatedLive = true;
        console.log(`✓ LIVE ACTIVITY SYNC CONFIRMED in feed after ${(i + 1) * 0.5}s!`);
        console.log('Feed content:\n', currentFeedText.slice(0, 300));
        break;
      }
    }

    if (!feedUpdatedLive) {
      throw new Error('FAIL: Activity Feed did not display the new activity without refresh!');
    }

    const ss5 = path.join(ARTIFACTS_DIR, 'phase9_05_user_a_live_activity_feed_sync.png');
    await pageA.screenshot({ path: ss5 });
    console.log('✓ Saved Screenshot 5 (Alice live activity feed sync):', ss5);

    console.log('\n===============================================================');
    console.log('🎉 ALL 5 REAL-TIME ZERO-REFRESH SCENARIOS VERIFIED SUCCESSFULLY!');
    console.log('===============================================================');
    console.log('1. A lends book to B → B sees it without refresh [PASSED]');
    console.log('2. A returns book → B updates without refresh [PASSED]');
    console.log('3. A adds book to shared shelf → B sees shelf change without refresh [PASSED]');
    console.log('4. A removes B from shelf → B loses access and stops receiving updates [PASSED]');
    console.log('5. A opens Activity Feed → new activity appears without refresh [PASSED]');

  } finally {
    await browser.close();
  }
}

runMultiBrowserVerification().catch((err) => {
  console.error('\n❌ MULTI-BROWSER VERIFICATION FAILED:', err);
  process.exit(1);
});
