import puppeteer from 'puppeteer-core';
import path from 'path';

const ARTIFACTS_DIR = 'C:\\Users\\acer\\.gemini\\antigravity-ide\\brain\\3a0eb0b2-22a1-4987-b5c6-afd0ce9537f7';
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runVerification() {
  console.log('--- Starting Phase 7 Browser Verification ---');
  const timestamp = Date.now().toString().slice(-6);
  const aliceEmail = `alice_p7_${timestamp}@example.com`;
  const bobEmail = `bob_p7_${timestamp}@example.com`;
  const password = 'StrongPassword123!';

  console.log(`Test users:`);
  console.log(`- Alice (Owner): ${aliceEmail}`);
  console.log(`- Bob (Borrower): ${bobEmail}`);

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1280,850'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 850 });

  try {
    // -------------------------------------------------------------
    // Step 1: Register Alice
    // -------------------------------------------------------------
    console.log('\n[Step 1] Registering Alice (Book Owner)...');
    await page.goto('http://localhost:5173/signup', { waitUntil: 'networkidle0' });
    await page.type('#signup-name', 'Alice Lender');
    await page.type('#signup-email', aliceEmail);
    await page.type('#signup-password', password);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(1000);

    // -------------------------------------------------------------
    // Step 2: Alice Adds a Book
    // -------------------------------------------------------------
    console.log('[Step 2] Alice adds book "Distributed Systems: Principles and Paradigms"...');
    // Click "+ Add Book"
    const addBtn = await page.waitForSelector('button ::-p-text(+ Add Book)', { timeout: 5000 });
    await addBtn.click();
    await sleep(500);

    // Fill book modal form
    await page.type('input[placeholder="e.g. Clean Code"]', 'Distributed Systems: Principles and Paradigms');
    await page.type('input[placeholder="e.g. Robert C. Martin"]', 'Andrew S. Tanenbaum');
    await page.type('input[placeholder="e.g. 350"]', '600');
    
    // Submit
    const saveBookBtn = await page.waitForSelector('form button[type="submit"]');
    await saveBookBtn.click();
    await sleep(1500);

    // Screenshot 1: Alice's Dashboard with created book
    const ss1 = path.join(ARTIFACTS_DIR, 'phase7_01_alice_dashboard_book_created.png');
    await page.screenshot({ path: ss1 });
    console.log('✓ Saved Screenshot 1:', ss1);

    // -------------------------------------------------------------
    // Step 3: Alice Logs Out & Register Bob
    // -------------------------------------------------------------
    console.log('\n[Step 3] Alice logs out, Bob registers...');
    const logoutBtn = await page.waitForSelector('button ::-p-text(Log Out)');
    await logoutBtn.click();
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(500);

    await page.goto('http://localhost:5173/signup', { waitUntil: 'networkidle0' });
    await page.type('#signup-name', 'Bob Reader');
    await page.type('#signup-email', bobEmail);
    await page.type('#signup-password', password);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(1000);

    console.log('[Step 3b] Bob logs out...');
    const bobLogoutBtn = await page.waitForSelector('button ::-p-text(Log Out)');
    await bobLogoutBtn.click();
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(500);

    // -------------------------------------------------------------
    // Step 4: Alice Logs In and Lends Book to Bob
    // -------------------------------------------------------------
    console.log('\n[Step 4] Alice logs back in to lend book to Bob...');
    await page.type('#login-email', aliceEmail);
    await page.type('#login-password', password);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(1200);

    // Click "🤝 Lend Book"
    console.log('[Step 4b] Opening Lend Modal...');
    const lendBtn = await page.waitForSelector('button ::-p-text(🤝 Lend Book)');
    await lendBtn.click();
    await sleep(500);

    // Screenshot 2: Lend Book Modal
    const ss2 = path.join(ARTIFACTS_DIR, 'phase7_02_lend_book_modal.png');
    await page.screenshot({ path: ss2 });
    console.log('✓ Saved Screenshot 2:', ss2);

    // Enter Bob's email and confirm loan
    console.log(`[Step 4c] Entering Bob's email (${bobEmail}) and confirming loan...`);
    await page.type('#borrowerEmail', bobEmail);
    const confirmLoanBtn = await page.waitForSelector('button ::-p-text(Confirm Loan)');
    await confirmLoanBtn.click();
    await sleep(2000);

    // Screenshot 3: Alice Dashboard showing Active Loan state
    const ss3 = path.join(ARTIFACTS_DIR, 'phase7_03_alice_active_loan_enforced.png');
    await page.screenshot({ path: ss3 });
    console.log('✓ Saved Screenshot 3:', ss3);

    // Click "Lent Out" sidebar view
    console.log('[Step 4d] Navigating to Lent Out view...');
    const lentOutNavBtn = await page.waitForSelector('button ::-p-text(Lent Out)');
    await lentOutNavBtn.click();
    await sleep(1000);

    // Screenshot 4: Lent Out view
    const ss4 = path.join(ARTIFACTS_DIR, 'phase7_04_alice_lent_out_view.png');
    await page.screenshot({ path: ss4 });
    console.log('✓ Saved Screenshot 4:', ss4);

    // -------------------------------------------------------------
    // Step 5: Alice Logs Out, Bob Logs In and Views Borrowed Book
    // -------------------------------------------------------------
    console.log('\n[Step 5] Alice logs out; Bob logs in to inspect Borrowed view...');
    const aliceLogout2 = await page.waitForSelector('button ::-p-text(Log Out)');
    await aliceLogout2.click();
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(500);

    await page.type('#login-email', bobEmail);
    await page.type('#login-password', password);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(1200);

    // Navigate to "Borrowed" view
    console.log('[Step 5b] Bob clicks "Borrowed" in sidebar...');
    const borrowedNavBtn = await page.waitForSelector('button ::-p-text(Borrowed)');
    await borrowedNavBtn.click();
    await sleep(1000);

    // Screenshot 5: Bob's read-only borrowed book card
    const ss5 = path.join(ARTIFACTS_DIR, 'phase7_05_bob_borrowed_view_readonly.png');
    await page.screenshot({ path: ss5 });
    console.log('✓ Saved Screenshot 5:', ss5);

    // -------------------------------------------------------------
    // Step 6: Bob Logs Out, Alice Returns Book & Checks History
    // -------------------------------------------------------------
    console.log('\n[Step 6] Bob logs out; Alice logs in to return book...');
    const bobLogout2 = await page.waitForSelector('button ::-p-text(Log Out)');
    await bobLogout2.click();
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(500);

    await page.type('#login-email', aliceEmail);
    await page.type('#login-password', password);
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    await sleep(1200);

    // Return the book
    console.log('[Step 6b] Alice clicks "Mark Returned"...');
    const returnBtn = await page.waitForSelector('button ::-p-text(↩ Mark Returned)');
    await returnBtn.click();
    await sleep(2000);

    // Open Lending History
    console.log('[Step 6c] Alice opens Lending History modal...');
    const historyBtn = await page.waitForSelector('button ::-p-text(📜 History)');
    await historyBtn.click();
    await sleep(1000);

    // Screenshot 6: Lending History Modal
    const ss6 = path.join(ARTIFACTS_DIR, 'phase7_06_lending_history_modal.png');
    await page.screenshot({ path: ss6 });
    console.log('✓ Saved Screenshot 6:', ss6);

    // Close History Modal
    const closeHistoryBtn = await page.waitForSelector('button ::-p-text(Close)');
    await closeHistoryBtn.click();
    await sleep(500);

    // Screenshot 7: Catalog with Returned Book Available Again
    const ss7 = path.join(ARTIFACTS_DIR, 'phase7_07_alice_book_returned_catalog.png');
    await page.screenshot({ path: ss7 });
    console.log('✓ Saved Screenshot 7:', ss7);

    console.log('\n🎉 ALL 6 BROWSER VERIFICATION STEPS COMPLETED SUCCESSFULLY!');
  } catch (error) {
    console.error('\n❌ Browser verification failed:', error);
    const errSs = path.join(ARTIFACTS_DIR, 'phase7_error_state.png');
    await page.screenshot({ path: errSs });
    console.log('Error screenshot saved to:', errSs);
    throw error;
  } finally {
    await browser.close();
  }
}

runVerification().catch((err) => {
  console.error(err);
  process.exit(1);
});
