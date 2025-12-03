// @ts-check
import { test, expect } from '@playwright/test';
import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const BASE_URL = 'http://localhost:3456';

test.describe.configure({ mode: 'serial' });

test.describe('Sanity Tests - Table Tennis Tracker', () => {
  
  test.afterEach(async () => {
    // Copy the test database to the instance folder
    const sourceDb = join(__dirname, 'files', 'v0_tabletennis.db');
    const instanceDir = join(__dirname, '..', 'instance');
    const targetDb = join(instanceDir, 'tabletennis.db');
    
    // Ensure instance directory exists
    if (!existsSync(instanceDir)) {
      mkdirSync(instanceDir, { recursive: true });
    }
    
    // Copy the database file
    copyFileSync(sourceDb, targetDb);
    console.log('Test database copied to instance folder');
  });
  
  test('homepage loads successfully', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page).toHaveTitle(/Overengineered Ping Pong Tracker/);
    await expect(page.getByRole('heading', { name: /Current Rankings/i })).toBeVisible();
  });

  test('navigation menu is visible and functional', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Check main navigation links
    await expect(page.getByRole('link', { name: /Rankings/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Add Player/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Add Game/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Recent Games/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Statistics/i })).toBeVisible();
  });

  test('add player page loads', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.getByRole('link', { name: /Add Player/i }).click();
    
    await expect(page).toHaveURL(/\/add_player/);
    await expect(page.getByRole('heading', { name: /Add New Player/i })).toBeVisible();
    await expect(page.getByLabel(/Player Name/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Add Player/i })).toBeVisible();
  });

  test('add game page loads', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.getByRole('link', { name: /Add Game/i }).click();
    
    await expect(page).toHaveURL(/\/add_game/);
    await expect(page.getByRole('heading', { name: /Record New Game/i })).toBeVisible();
  });

  test('recent games page loads', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.getByRole('link', { name: /Recent Games/i }).click();
    
    await expect(page).toHaveURL(/\/recent_games/);
    await expect(page.getByRole('heading', { name: /Recent Games/i })).toBeVisible();
  });

  test('statistics page loads', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.getByRole('link', { name: /Statistics/i }).click();
    
    await expect(page).toHaveURL(/\/statistics/);
    await expect(page.getByRole('heading', { name: '📈 Statistics' })).toBeVisible();
  });

  test('can add a new player', async ({ page }) => {
    await page.goto(`${BASE_URL}/add_player`);
    
    const uniqueName = `TestPlayer_${Date.now()}`;
    await page.getByLabel(/Player Name/i).fill(uniqueName);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    // Should redirect to rankings with success message
    await expect(page).toHaveURL(BASE_URL + '/');
    await expect(page.getByText(/added successfully/i)).toBeVisible();
    await expect(page.getByRole('link', { name: uniqueName })).toHaveText(uniqueName);
  });

  test('cannot add duplicate player', async ({ page }) => {
    await page.goto(`${BASE_URL}/add_player`);
    
    const uniqueName = `DupeTest_${Date.now()}`;
    
    // Add first time
    await page.getByLabel(/Player Name/i).fill(uniqueName);
    await page.getByRole('button', { name: /Add Player/i }).click();
    await expect(page.getByText(/added successfully/i)).toBeVisible();
    
    // Try to add again
    await page.goto(`${BASE_URL}/add_player`);
    await page.getByLabel(/Player Name/i).fill(uniqueName);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    await expect(page.getByText(/already exists/i)).toBeVisible();
  });

  test('cannot add player with empty name', async ({ page }) => {
    await page.goto(`${BASE_URL}/add_player`);
    
    const input = page.getByLabel(/Player Name/i);
    const submitButton = page.getByRole('button', { name: /Add Player/i });
    
    // Verify the input has the required attribute
    await expect(input).toHaveAttribute('required');
    
    // Try to submit without filling the input
    await submitButton.click();
    
    // Check that validation prevented submission - page should still be on add_player
    await expect(page).toHaveURL(/\/add_player/);
  });

  test('rankings table displays correct columns', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Check for table headers
    const headers = ['Rank', 'Player', 'ELO Rating', 'Games', 'Wins', 'Losses', 'Win Rate', 'Actions'];
    for (const header of headers) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible();
    }
  });

  test('new players start with 1500 ELO', async ({ page }) => {
    await page.goto(`${BASE_URL}/add_player`);
    
    const uniqueName = `ELOTest_${Date.now()}`;
    await page.getByLabel(/Player Name/i).fill(uniqueName);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    await page.goto(BASE_URL);
    const playerRow = page.locator('tr', { has: page.getByText(uniqueName) });
    await expect(playerRow.locator('td.elo')).toHaveText('1500');
  });

  test('can delete player with no games', async ({ page }) => {
    await page.goto(`${BASE_URL}/add_player`);
    
    const uniqueName = `DeleteTest_${Date.now()}`;
    await page.getByLabel(/Player Name/i).fill(uniqueName);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    // Find and delete the player
    await page.goto(BASE_URL);
    const playerRow = page.locator('tr', { has: page.getByText(uniqueName) });
    
    page.on('dialog', dialog => dialog.accept());
    await playerRow.getByRole('button', { name: /Delete/i }).click();
    
    await expect(page.getByText(/deleted successfully/i)).toBeVisible();
    // Verify the player row is no longer in the table
    await expect(playerRow).not.toBeVisible();
  });

  test('can view player history', async ({ page }) => {
    await page.goto(`${BASE_URL}/add_player`);
    
    const uniqueName = `HistoryTest_${Date.now()}`;
    await page.getByLabel(/Player Name/i).fill(uniqueName);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    // Click on player name to view history
    await page.goto(BASE_URL);
    await page.getByRole('link', { name: uniqueName }).click();
    
    await expect(page).toHaveURL(/\/player\/\d+/);
    await expect(page.getByRole('heading', { name: uniqueName })).toBeVisible();
    await expect(page.getByText(/Game History/i)).toBeVisible();
  });

  test('can record a game between two players', async ({ page }) => {
    // Create two players
    const player1 = `Winner_${Date.now()}`;
    const player2 = `Loser_${Date.now()}`;
    
    await page.goto(`${BASE_URL}/add_player`);
    await page.getByLabel(/Player Name/i).fill(player1);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    await page.goto(`${BASE_URL}/add_player`);
    await page.getByLabel(/Player Name/i).fill(player2);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    // Record a game - need to get player IDs from the page first
    await page.goto(`${BASE_URL}/add_game`);
    // Get the IDs by matching player names in the select options
    const winnerOption = page.locator(`select[name="winner_id"] option:has-text("${player1}")`).first();
    const loserOption = page.locator(`select[name="loser_id"] option:has-text("${player2}")`).first();
    const winnerId = await winnerOption.getAttribute('value');
    const loserId = await loserOption.getAttribute('value');
    await page.selectOption('select[name="winner_id"]', winnerId || '');
    await page.selectOption('select[name="loser_id"]', loserId || '');
    await page.getByRole('button', { name: /Record Game/i }).click();
    
    await expect(page.getByText(/Game recorded/i)).toBeVisible();
    await expect(page.getByText(new RegExp(`${player1}.*defeated.*${player2}`, 'i'))).toBeVisible();

  });

  test('cannot record game with same player as winner and loser', async ({ page }) => {
    const player = `SelfPlay_${Date.now()}`;
    
    await page.goto(`${BASE_URL}/add_player`);
    await page.getByLabel(/Player Name/i).fill(player);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    await page.goto(`${BASE_URL}/add_game`);
    // Get the player ID from the select options
    const playerOption = page.locator(`select[name="winner_id"] option:has-text("${player}")`).first();
    const playerId = await playerOption.getAttribute('value');
    await page.selectOption('select[name="winner_id"]', playerId || '');
    await page.selectOption('select[name="loser_id"]', playerId || '');
    await page.getByRole('button', { name: /Record Game/i }).click();
    
    await expect(page.getByText(/must be different/i)).toBeVisible();
  });

  test('statistics page shows correct metrics', async ({ page }) => {
    await page.goto(`${BASE_URL}/statistics`);
    
    // Check for key statistics labels and specific values from test database
    await expect(page.getByText(/Total Players/i)).toBeVisible();
    await expect(page.locator('.stat-number').filter({ hasText: '7' }).first()).toBeVisible();
    
    await expect(page.getByText(/Total Games/i)).toBeVisible();
    await expect(page.locator('.stat-number').filter({ hasText: '11' }).first()).toBeVisible();
    
    await expect(page.getByText(/Highest ELO/i)).toBeVisible();
    await expect(page.locator('.stat-number').filter({ hasText: '1581' }).first()).toBeVisible();
    
    await expect(page.getByText(/Most Games/i)).toBeVisible();
    await expect(page.locator('.stat-number').filter({ hasText: '6' }).first()).toBeVisible();
  });

  test('ELO changes after game', async ({ page }) => {
    const player1 = `ELOWinner_${Date.now()}`;
    const player2 = `ELOLoser_${Date.now()}`;
    
    // Create players
    await page.goto(`${BASE_URL}/add_player`);
    await page.getByLabel(/Player Name/i).fill(player1);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    await page.goto(`${BASE_URL}/add_player`);
    await page.getByLabel(/Player Name/i).fill(player2);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    // Record game - get player IDs from select options
    await page.goto(`${BASE_URL}/add_game`);
    const winnerOpt = page.locator(`select[name="winner_id"] option:has-text("${player1}")`).first();
    const loserOpt = page.locator(`select[name="loser_id"] option:has-text("${player2}")`).first();
    const wId = await winnerOpt.getAttribute('value');
    const lId = await loserOpt.getAttribute('value');
    await page.selectOption('select[name="winner_id"]', wId || '');
    await page.selectOption('select[name="loser_id"]', lId || '');
    await page.getByRole('button', { name: /Record Game/i }).click();
    
    // Check ELO changed
    await page.goto(BASE_URL);
    const winner = page.locator('tr', { has: page.getByText(player1) });
    const loser = page.locator('tr', { has: page.getByText(player2) });
    
    const winnerELO = await winner.locator('td.elo').textContent();
    const loserELO = await loser.locator('td.elo').textContent();
    
    expect(Number.parseInt(winnerELO || '0')).toBeGreaterThan(1500);
    expect(Number.parseInt(loserELO || '0')).toBeLessThan(1500);
  });

  test('recent games page shows game records', async ({ page }) => {
    const player1 = `Recent1_${Date.now()}`;
    const player2 = `Recent2_${Date.now()}`;
    
    // Create players and game
    await page.goto(`${BASE_URL}/add_player`);
    await page.getByLabel(/Player Name/i).fill(player1);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    await page.goto(`${BASE_URL}/add_player`);
    await page.getByLabel(/Player Name/i).fill(player2);
    await page.getByRole('button', { name: /Add Player/i }).click();
    
    await page.goto(`${BASE_URL}/add_game`);
    // Get player IDs from select options by matching player names
    const wOpt = page.locator(`select[name="winner_id"] option:has-text("${player1}")`).first();
    const lOpt = page.locator(`select[name="loser_id"] option:has-text("${player2}")`).first();
    const wVal = await wOpt.getAttribute('value');
    const lVal = await lOpt.getAttribute('value');
    await page.selectOption('select[name="winner_id"]', wVal || '');
    await page.selectOption('select[name="loser_id"]', lVal || '');
    await page.getByRole('button', { name: /Record Game/i }).click();
    
    // Check recent games
    await page.goto(`${BASE_URL}/recent_games`);
    await expect(page.getByText(player1)).toBeVisible();
    await expect(page.getByText(player2)).toBeVisible();
  });

  test('visual snapshot of homepage', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page).toHaveScreenshot('homepage.png', { fullPage: true });
  });

  test('visual snapshot of add player page', async ({ page }) => {
    await page.goto(`${BASE_URL}/add_player`);
    await expect(page).toHaveScreenshot('add-player.png', { fullPage: true });
  });

  test('visual snapshot of statistics page', async ({ page }) => {
    await page.goto(`${BASE_URL}/statistics`);
    await expect(page).toHaveScreenshot('statistics.png', { fullPage: true });
  });

  test('visual snapshot of player 1 information page', async ({ page }) => {
    await page.goto(`${BASE_URL}/player/2`);
    await expect(page).toHaveScreenshot('player-info.png', { fullPage: true });
  });

  test('visual snapshot of player 2 with ELO information page', async ({ page }) => {
    await page.goto(`${BASE_URL}/player/2`);
    // click on ELO chart toggle to expand it
    await page.locator('summary.chart-toggle').click();
    // wait 3s for animation
    await page.waitForTimeout(3000);
    await expect(page).toHaveScreenshot('player-info-elo.png', { fullPage: true });
  });
});
