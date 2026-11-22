'use strict';
const $ = (id) => document.getElementById(id);
const samples = {
  gateway: 'Production outage: HTTP 502 Bad Gateway after an upstream deployment. Contact ops@example.test; host 10.0.0.8; password=demo-only',
  memory: 'Worker terminated OOMKilled during a large batch. Memory hits its cgroup limit and the container exits with code 137.',
  windows: 'Windows deployment fails with 0x80070005 Access Denied on the application directory after a permissions baseline change.',
  kubernetes: 'Deployment has CrashLoopBackOff after a startup configuration change. Previous container logs show exit code 1.',
  unknown: 'The quantum printer flickers purple intermittently; no error codes or diagnostic evidence are available.'
};
let threadId = null;
let busy = false;
$('ticket').value = samples.gateway;
$('sample').addEventListener('change', () => { $('ticket').value = samples[$('sample').value]; });
const labels = {awaiting_approval: 'Awaiting approval', completed: 'Completed', denied: 'Plan rejected', escalated: 'Escalated to operator'};
function setBusy(value) {
  busy = value;
  for (const id of ['triage', 'approve', 'reject']) $(id).disabled = value;
  $('triage').textContent = value ? 'Working…' : 'Analyze incident →';
}
async function api(path, body) {
  const headers = {};
  if ($('token').value) headers.Authorization = `Bearer ${$('token').value}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body)});
  const payload = await response.json();
  if (!response.ok) {
    const detail = typeof payload.detail === 'string' ? payload.detail : 'Check the incident text and access token.';
    throw new Error(`${response.status}: ${detail}`);
  }
  return payload;
}
function render(result) {
  threadId = result.thread_id;
  $('empty').hidden = true;
  $('report').hidden = false;
  $('status').textContent = labels[result.status] || result.status;
  $('status').classList.remove('muted');
  $('severity').textContent = result.severity;
  $('category').textContent = result.category;
  $('confidence').textContent = `${Math.round(result.report.confidence_score * 100)}%`;
  $('cause').textContent = result.report.root_cause;
  $('commands').textContent = result.report.proposed_commands.join('\n') || 'No executable plan. An operator must investigate.';
  $('citations').replaceChildren();
  for (const id of result.report.cited_runbook_ids) {
    const tag = document.createElement('span'); tag.className = 'citation'; tag.textContent = id; $('citations').append(tag);
  }
  $('approval').hidden = result.status !== 'awaiting_approval';
  $('execution').hidden = result.execution_log.length === 0;
  $('receipts').replaceChildren();
  for (const record of result.execution_log) {
    const receipt = document.createElement('div'); receipt.className = 'receipt';
    const command = document.createElement('code'); command.textContent = record.command;
    const text = document.createElement('p'); text.textContent = record.result;
    receipt.append(command, text); $('receipts').append(receipt);
  }
  $('thread').textContent = `Thread: ${threadId} · retrieval retries: ${result.retry_count}`;
}
$('triage').addEventListener('click', async () => {
  if (busy) return;
  const text = $('ticket').value.trim();
  if (text.length < 8) { $('message').textContent = 'Please enter an incident of at least 8 characters.'; return; }
  setBusy(true); $('message').textContent = ''; $('note').value = '';
  // Clear the old plan before starting a new incident so it cannot be approved by mistake.
  threadId = null; $('approval').hidden = true; $('report').hidden = true; $('empty').hidden = false;
  try {
    const result = await api('/triage', {text}); render(result);
    const snapshot = await api(`/threads/${encodeURIComponent(threadId)}`);
    $('redacted').textContent = snapshot.state.scrubbed_ticket;
    $('ticket').value = snapshot.state.scrubbed_ticket;
    if (result.status === 'escalated') $('message').textContent = 'Evidence remained insufficient after two retries. No actions were executed.';
  } catch (error) { $('message').textContent = error.message; }
  finally { setBusy(false); }
});
async function decide(approved) {
  if (busy || !threadId) return;
  setBusy(true); $('message').textContent = '';
  try {
    render(await api(`/approve/${encodeURIComponent(threadId)}`, {approved, reviewer_note: $('note').value}));
    $('note').value = '';
    $('message').textContent = approved ? 'Simulation completed. No infrastructure was changed.' : 'Plan rejected. No actions were executed.';
  } catch (error) { $('message').textContent = error.message; }
  finally { setBusy(false); }
}
$('approve').addEventListener('click', () => decide(true));
$('reject').addEventListener('click', () => decide(false));
(async () => {
  try {
    const ready = await api('/ready');
    $('connection').textContent = 'Knowledge base ready';
    $('mode').textContent = `${ready.mock_llm ? 'Free deterministic demo' : 'Live model analysis'} · all remediation is simulated`;
  } catch (error) {
    $('connection').textContent = 'Server not ready';
    $('message').textContent = 'The knowledge base is still starting. Reload after a few seconds, or check the server logs.';
  }
})();
