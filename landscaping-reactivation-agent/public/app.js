async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || 'Request failed');
  }
  return res.json();
}

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
    });
  });
}

async function loadSettings() {
  const settings = await api('/settings');
  const form = document.getElementById('settings-form');
  for (const [key, value] of Object.entries(settings)) {
    if (form.elements[key]) form.elements[key].value = value;
  }
  document.getElementById('business-name-header').textContent = settings.businessName || 'Landscaping Reactivation';
  document.getElementById('webhook-url').textContent = `${location.origin}/sms`;
}

async function loadCustomers() {
  const customers = await api('/customers');
  const tbody = document.querySelector('#customers-table tbody');
  tbody.innerHTML = customers.map((c) => `
    <tr>
      <td>${escapeHtml(c.name)}</td>
      <td>${escapeHtml(c.phone)}</td>
      <td>${escapeHtml(c.lastServiceDate)}</td>
      <td><button data-phone="${escapeHtml(c.phone)}" class="remove-customer">Remove</button></td>
    </tr>`).join('');
  document.getElementById('stat-customers').textContent = customers.length;

  tbody.querySelectorAll('.remove-customer').forEach((btn) => {
    btn.addEventListener('click', async () => {
      await api(`/customers/${encodeURIComponent(btn.dataset.phone)}`, { method: 'DELETE' });
      loadCustomers();
    });
  });
}

async function loadCampaigns() {
  const campaigns = await api('/campaigns');
  const container = document.getElementById('campaign-list');
  container.innerHTML = Object.entries(campaigns).map(([name, template]) => `
    <div class="campaign-card">
      <h3>${escapeHtml(name)}</h3>
      <p>${escapeHtml(template)}</p>
      <button data-campaign="${escapeHtml(name)}">Send blast</button>
    </div>`).join('');

  container.querySelectorAll('button').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!confirm(`Send the "${btn.dataset.campaign}" campaign to all active customers?`)) return;
      btn.disabled = true;
      const statusEl = document.getElementById('campaign-status');
      try {
        const result = await api(`/campaigns/${btn.dataset.campaign}/blast`, { method: 'POST' });
        statusEl.textContent = `Sent: ${result.sent}, Failed: ${result.failed}, Skipped (opted out): ${result.skipped}`;
        loadActivity();
      } catch (err) {
        statusEl.textContent = `Error: ${err.message}`;
      } finally {
        btn.disabled = false;
      }
    });
  });
}

async function loadActivity() {
  const [optOuts, replies, blastLog] = await Promise.all([
    api('/opt-outs'),
    api('/replies'),
    api('/blast-log'),
  ]);

  document.getElementById('stat-optouts').textContent = optOuts.length;
  document.getElementById('stat-replies').textContent = replies.length;
  document.getElementById('stat-sent').textContent = blastLog.filter((r) => r.status === 'sent').length;

  const optBody = document.querySelector('#optouts-table tbody');
  optBody.innerHTML = optOuts.map((phone) => `
    <tr>
      <td>${escapeHtml(phone)}</td>
      <td><button data-phone="${escapeHtml(phone)}" class="resub">Resubscribe</button></td>
    </tr>`).join('');
  optBody.querySelectorAll('.resub').forEach((btn) => {
    btn.addEventListener('click', async () => {
      await api(`/opt-outs/${encodeURIComponent(btn.dataset.phone)}`, { method: 'DELETE' });
      loadActivity();
    });
  });

  document.querySelector('#replies-table tbody').innerHTML = replies.map((r) => `
    <tr>
      <td>${new Date(r.timestamp).toLocaleString()}</td>
      <td>${escapeHtml(r.from)}</td>
      <td>${escapeHtml(r.body)}</td>
      <td>${escapeHtml(r.intent)}</td>
    </tr>`).join('');

  document.querySelector('#blastlog-table tbody').innerHTML = blastLog.map((r) => `
    <tr>
      <td>${new Date(r.timestamp).toLocaleString()}</td>
      <td>${escapeHtml(r.campaign)}</td>
      <td>${escapeHtml(r.name)}</td>
      <td>${escapeHtml(r.phone)}</td>
      <td>${escapeHtml(r.status)}</td>
    </tr>`).join('');
}

document.getElementById('settings-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target).entries());
  const statusEl = document.getElementById('settings-status');
  try {
    await api('/settings', { method: 'POST', body: JSON.stringify(data) });
    document.getElementById('business-name-header').textContent = data.businessName;
    statusEl.textContent = 'Saved.';
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  }
});

document.getElementById('customer-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target).entries());
  const statusEl = document.getElementById('customers-status');
  try {
    await api('/customers', { method: 'POST', body: JSON.stringify(data) });
    e.target.reset();
    statusEl.textContent = 'Added.';
    loadCustomers();
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  }
});

document.getElementById('csv-import-btn').addEventListener('click', async () => {
  const csv = document.getElementById('csv-import').value;
  const statusEl = document.getElementById('customers-status');
  try {
    await api('/customers/import', { method: 'POST', body: JSON.stringify({ csv }) });
    statusEl.textContent = 'Imported.';
    loadCustomers();
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  }
});

setupTabs();
loadSettings();
loadCustomers();
loadCampaigns();
loadActivity();
