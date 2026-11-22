// CI-only browser test. The application itself needs no Node installation.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { setTimeout as pause } from 'node:timers/promises';

const require = createRequire(path.join(process.env.PLAYWRIGHT_PACKAGE_ROOT, 'package.json'));
const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8015';
const server = spawn('uv', ['run', '--frozen', '--no-sync', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8015', '--no-access-log'], {
  env: { ...process.env, MOCK_LLM: 'true', RETRIEVAL_BACKEND: 'mock', AUTO_INGEST: 'true', QDRANT_MODE: 'memory', CHECKPOINT_PATH: ':memory:', API_TOKEN: '', LANGFUSE_PUBLIC_KEY: '' },
  stdio: ['ignore', 'pipe', 'pipe']
});
let logs = '';
server.stdout.on('data', data => { logs = (logs + data).slice(-50000); });
server.stderr.on('data', data => { logs = (logs + data).slice(-50000); });
let browser;
try {
  let ready = false;
  for (let attempt = 0; attempt < 90; attempt++) {
    if (server.exitCode !== null) throw new Error('Browser-test API exited before readiness');
    try { ready = (await fetch(`${base}/ready`)).ok; } catch { /* Wait for socket readiness. */ }
    if (ready) break;
    await pause(1000);
  }
  assert(ready, 'Browser-test API did not become ready');
  browser = await chromium.launch({ executablePath: process.env.CHROME_BIN || '/usr/bin/google-chrome', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base);
  await page.getByText('Knowledge base ready', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Analyze incident' }).click();
  await page.getByText('Awaiting approval', { exact: true }).waitFor();
  assert.equal(await page.locator('#execution').isVisible(), false);
  assert(!((await page.locator('#ticket').inputValue()).includes('password=demo-only')));
  await page.getByRole('button', { name: 'Approve simulation', exact: true }).click();
  await page.getByText('Completed', { exact: true }).waitFor();
  assert.equal(await page.locator('.receipt').count(), 2);
  await mkdir('dist', { recursive: true });
  await page.screenshot({ path: 'dist/SentinelOps-console.png', fullPage: true });
  await page.getByLabel('Start with an example').selectOption('windows');
  await page.getByRole('button', { name: 'Analyze incident' }).click();
  await page.getByText('Awaiting approval', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Reject plan', exact: true }).click();
  await page.getByText('Plan rejected', { exact: true }).waitFor();
  assert.equal(await page.locator('#execution').isVisible(), false);
  await page.getByLabel('Start with an example').selectOption('unknown');
  await page.getByRole('button', { name: 'Analyze incident' }).click();
  await page.getByText('Escalated to operator', { exact: true }).waitFor();
  assert.equal(await page.locator('#approval').isVisible(), false);
  assert.deepEqual(errors, []);
  console.log('PASS: browser analysis, redaction, approval, rejection and escalation');
} catch (error) {
  console.error(logs);
  throw error;
} finally {
  if (browser) await browser.close();
  server.kill('SIGTERM');
}
