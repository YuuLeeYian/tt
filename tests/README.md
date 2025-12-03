# Test Suite for Table Tennis Tracker

This directory contains end-to-end tests for the Table Tennis Tracker application using [Playwright](https://playwright.dev/), an open-source testing framework.

## Features

- ✅ **Comprehensive sanity tests** covering all main features
- 📸 **Visual regression testing** with screenshot comparisons
- 🎨 **Interactive UI mode** for easy test management and debugging
- 🔄 **Easy screenshot updates** through Playwright's UI tools
- 📊 **Detailed HTML reports** with traces and videos on failures

## Prerequisites

- Node.js (v16 or higher)
- Python 3.x with Flask installed
- The application dependencies installed (`pip install -r requirements.txt`)

## Installation

1. Install Playwright and dependencies:

```bash
npm install --save-dev @playwright/test
npx playwright install
```

Or if you prefer using the package.json:

```bash
npm install
```

## Running Tests

### Run all tests (headless mode)

```bash
npx playwright test
```

### Run tests in UI Mode (Recommended for development)

This is the **easiest way to manage and update tests**:

```bash
npx playwright test --ui
```

In UI mode you can:
- 👁️ Watch tests run in real-time
- 🐛 Debug failing tests step-by-step
- 📸 Review and update screenshots visually
- ⏯️ Pause and inspect at any point
- 🔍 See detailed traces and network requests

### Run tests in headed mode (see the browser)

```bash
npx playwright test --headed
```

### Run specific test file

```bash
npx playwright test sanity.spec.js
```

### Run specific test by name

```bash
npx playwright test -g "homepage loads successfully"
```

## Updating Screenshots

When your UI changes and you need to update the baseline screenshots:

### Method 1: Using UI Mode (Recommended)

1. Run tests in UI mode:
   ```bash
   npx playwright test --ui
   ```

2. Run the tests with screenshots
3. When a screenshot test fails, you'll see a visual diff
4. Click the "Update snapshot" button to accept the new screenshot
5. The baseline screenshots will be automatically updated

### Method 2: Using Command Line

```bash
npx playwright test --update-snapshots
```

Or for specific tests:

```bash
npx playwright test sanity.spec.js --update-snapshots
```

### Method 3: Interactive Update with Headed Browser

```bash
npx playwright test --headed --update-snapshots
```

## Test Reports

After running tests, view the HTML report:

```bash
npx playwright show-report
```

The report includes:
- Test results and duration
- Screenshots and videos of failures
- Full execution traces
- Network activity logs

## Test Structure

### Current Test Coverage

The `sanity.spec.js` file includes tests for:

1. **Navigation & Page Loading**
   - Homepage loads correctly
   - All navigation links work
   - Each page loads with proper content

2. **Player Management**
   - Add new players
   - Validate duplicate prevention
   - Validate empty name prevention
   - Delete players with no games
   - View player history
   - Verify initial 1500 ELO rating

3. **Game Recording**
   - Record games between players
   - Validate same player restriction
   - Verify ELO changes after games
   - View recent games

4. **Data Display**
   - Rankings table structure
   - Statistics page metrics
   - Win/loss records

5. **Visual Regression**
   - Homepage appearance
   - Add player page appearance
   - Statistics page appearance

## Writing New Tests

Add new tests to `sanity.spec.js` or create new `.spec.js` files:

```javascript
test('my new test', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Something')).toBeVisible();
});
```

For visual tests:

```javascript
test('visual test for new page', async ({ page }) => {
  await page.goto('/new-page');
  await expect(page).toHaveScreenshot('new-page.png');
});
```

## Debugging Tests

### Debug mode with Playwright Inspector

```bash
npx playwright test --debug
```

This opens the Playwright Inspector where you can:
- Step through tests line by line
- Inspect the page state
- Try locators in the console
- See console logs

### Generate test code

Use Playwright's codegen to record interactions:

```bash
npx playwright codegen http://localhost:3456
```

This will open a browser and record your actions as test code.

## CI/CD Integration

The tests are configured to work in CI environments. Set the `CI` environment variable:

```bash
CI=true npx playwright test
```

This will:
- Run with 2 retries
- Use a single worker
- Fail if `test.only` is found

## Tips

1. **Use UI Mode for daily development** - It's the fastest way to write and debug tests
2. **Update screenshots regularly** - Keep visual tests in sync with UI changes
3. **Use descriptive test names** - Makes it easy to find failing tests
4. **Group related tests** - Use `test.describe()` blocks
5. **Clean up test data** - Use unique timestamps in test player names to avoid conflicts

## Troubleshooting

### Tests fail because app isn't running

The `webServer` configuration in `playwright.config.js` should auto-start the Flask app. If it doesn't:

1. Start the app manually in another terminal:
   ```bash
   python app.py
   ```

2. Run tests:
   ```bash
   npx playwright test
   ```

### Screenshot tests fail unexpectedly

Screenshots can be sensitive to:
- Font rendering differences
- Browser version updates
- Screen resolution

Update them using UI mode or `--update-snapshots` flag.

### Port conflicts

If port 3456 is in use, update:
- `app.py` (change the port in `app.run()`)
- `playwright.config.js` (change `baseURL` and `webServer.url`)
- Test files (update `BASE_URL` constant)

## Additional Resources

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright UI Mode](https://playwright.dev/docs/test-ui-mode)
- [Visual Comparisons](https://playwright.dev/docs/test-snapshots)
