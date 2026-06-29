/* Vivify Dashboard — ES module */
const API = window.location.origin;

/* ── Navigation ── */
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + btn.dataset.view).classList.add('active');
    if (btn.dataset.view === 'terminal') initTerminals();
    if (btn.dataset.view === 'health') fetchHealth();
  });
});

/* ── LazyHub Grid ── */
const HUB_APPS = [
  { icon: '💰', label: 'LazyLedger',  desc: 'Financeiro',       action: 'finances' },
  { icon: '💎', label: 'LazyVivify',  desc: 'Catálogo de joias', action: 'jewels' },
  { icon: '🧠', label: 'LazySOC',     desc: 'Gateway LLM',       action: 'soc' },
  { icon: '📊', label: 'LazyMon',     desc: 'Monitor unificado',  action: 'monitor' },
  { icon: '💾', label: 'LazyBackup',  desc: 'Backups automáticos', action: 'backup' },
  { icon: '🚀', label: 'LazyZellij',  desc: 'Multiplexador',      action: 'zellij' },
  { icon: '🔵', label: 'Deploy Blue', desc: 'Ambiente azul',      action: 'deploy-blue' },
  { icon: '🟢', label: 'Deploy Green',desc: 'Ambiente verde',     action: 'deploy-green' },
  { icon: '↩️', label: 'Rollback',    desc: 'Rollback atômico',   action: 'rollback' },
  { icon: '🖥️', label: 'Terminal Web',desc: 'Terminal no browser', action: 'terminal' },
  { icon: '❤', label: 'Health Check',desc: 'Status dos serviços', action: 'health' },
  { icon: '📋', label: 'Audit Chain', desc: 'Hashchain total',    action: 'audit' },
];

function renderHub() {
  const grid = document.getElementById('hub-grid');
  grid.innerHTML = '';
  for (const app of HUB_APPS) {
    const card = document.createElement('div');
    card.className = 'hub-card';
    card.innerHTML = `<div class="icon">${app.icon}</div>
      <div class="label">${app.label}</div>
      <div class="desc">${app.desc}</div>`;
    card.addEventListener('click', () => handleHubAction(app.action));
    grid.appendChild(card);
  }
}

async function handleHubAction(action) {
  switch (action) {
    case 'terminal':
      document.querySelector('[data-view="terminal"]').click();
      break;
    case 'health':
      document.querySelector('[data-view="health"]').click();
      break;
    case 'audit':
      await openModal('Audit Chain', '/static/pages/audit.html');
      break;
    default:
      await openModal(action.charAt(0).toUpperCase() + action.slice(1), null);
  }
}

/* ── Modal ── */
window.closeModal = function(e) {
  if (e && e.target !== document.getElementById('modal-overlay') && e.target.closest('#modal')) return;
  document.getElementById('modal-overlay').classList.add('hidden');
  document.getElementById('modal').classList.add('hidden');
};

async function openModal(title, url) {
  document.getElementById('modal-title').textContent = title;
  const body = document.getElementById('modal-body');
  if (url) {
    try {
      const resp = await fetch(url);
      body.innerHTML = await resp.text();
    } catch {
      body.innerHTML = `<p style="padding:20px;color:var(--text-dim);">Could not load ${url}</p>`;
    }
  } else {
    body.innerHTML = `<p style="padding:20px;color:var(--text-dim);">Launching <strong>${title}</strong> — run the equivalent TUI locally:</p>
      <pre style="margin:12px 20px;padding:12px;background:#111;border-radius:8px;font-size:13px;">lazy${title.toLowerCase().replace(' ','')}</pre>`;
  }
  document.getElementById('modal-overlay').classList.remove('hidden');
  document.getElementById('modal').classList.remove('hidden');
}

/* ── Terminal (xterm.js) ── */
let terminals = [];

function initTerminals() {
  if (terminals.length > 0) return;
  addTerminalTab();
}

function addTerminalTab() {
  const idx = terminals.length;
  const container = document.getElementById('terminal-container');

  const termDiv = document.createElement('div');
  termDiv.id = `term-${idx}`;
  termDiv.style.cssText = 'position:absolute;inset:0;display:' + (idx === 0 ? 'block' : 'none');
  container.appendChild(termDiv);

  const term = new Terminal({
    cursorBlink: true,
    cursorStyle: 'bar',
    fontSize: 13,
    fontFamily: "'Fira Code', 'Cascadia Code', monospace",
    theme: {
      background: '#0d0d0d', foreground: '#e0e0e0',
      cursor: '#D4AF37', cursorAccent: '#000',
      selectionBackground: 'rgba(212,175,55,0.3)',
      black: '#000', red: '#f87171', green: '#4ade80',
      yellow: '#fbbf24', blue: '#60a5fa', magenta: '#c084fc',
      cyan: '#22d3ee', white: '#e0e0e0',
      brightBlack: '#555', brightRed: '#f87171', brightGreen: '#4ade80',
      brightYellow: '#fbbf24', brightBlue: '#60a5fa', brightMagenta: '#c084fc',
      brightCyan: '#22d3ee', brightWhite: '#fff',
    },
    allowTransparency: true,
  });
  const fit = new FitAddon.FitAddon();
  term.loadAddon(fit);

  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/terminal`;
  const ws = new WebSocket(wsUrl);
  ws.binaryType = 'arraybuffer';

  term.onData(data => {
    if (ws.readyState === WebSocket.OPEN) ws.send(data);
  });

  ws.onopen = () => {
    fit.fit();
    term.focus();
  };
  ws.onmessage = ev => {
    if (ev.data instanceof ArrayBuffer) {
      term.write(new Uint8Array(ev.data));
    } else {
      term.write(ev.data);
    }
  };
  ws.onclose = () => {
    term.write('\r\n\x1b[31m[disconnected]\x1b[0m\r\n');
  };

  term.open(termDiv);
  setTimeout(() => fit.fit(), 100);

  terminals.push({ term, fit, ws, div: termDiv });

  const tabstrip = document.getElementById('tabstrip');
  const addBtn = document.getElementById('add-tab');
  const tab = document.createElement('div');
  tab.className = 'tab' + (idx === 0 ? ' active' : '');
  tab.dataset.idx = idx;
  tab.innerHTML = `bash <span class="tab-close">×</span>`;
  tab.querySelector('.tab-close').addEventListener('click', e => {
    e.stopPropagation();
    closeTerminalTab(idx);
  });
  tab.addEventListener('click', () => switchTerminalTab(idx));
  tabstrip.insertBefore(tab, addBtn);
}

function switchTerminalTab(idx) {
  document.querySelectorAll('#tabstrip .tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('#terminal-container > div').forEach(d => d.style.display = 'none');
  const tab = document.querySelector(`#tabstrip .tab[data-idx="${idx}"]`);
  if (tab) tab.classList.add('active');
  const termDiv = document.getElementById(`term-${idx}`);
  if (termDiv) {
    termDiv.style.display = 'block';
    setTimeout(() => { try { terminals[idx]?.fit.fit(); } catch {} }, 50);
  }
}

function closeTerminalTab(idx) {
  const t = terminals[idx];
  if (t) {
    t.ws.close();
    t.term.dispose();
  }
  const tab = document.querySelector(`#tabstrip .tab[data-idx="${idx}"]`);
  if (tab) tab.remove();
  const termDiv = document.getElementById(`term-${idx}`);
  if (termDiv) termDiv.remove();
  terminals.splice(idx, 1);
  // re-index
  document.querySelectorAll('#tabstrip .tab').forEach((t, i) => t.dataset.idx = i);
  document.querySelectorAll('#terminal-container > div').forEach((d, i) => d.id = `term-${i}`);
  if (terminals.length === 0) addTerminalTab();
  else switchTerminalTab(terminals.length - 1);
}

document.getElementById('add-tab').addEventListener('click', addTerminalTab);

/* ── Health Check ── */
async function fetchHealth() {
  const grid = document.getElementById('health-grid');
  grid.innerHTML = '<p style="padding:24px;color:var(--text-dim);">Loading...</p>';
  try {
    const resp = await fetch('/monitoring/health');
    const data = await resp.json();
    grid.innerHTML = '';
    for (const [key, svc] of Object.entries(data.services || {})) {
      const card = document.createElement('div');
      const isUp = svc.status === 'up';
      card.className = `health-card ${isUp ? 'up' : 'down'}`;
      card.innerHTML = `
        <div class="name">${isUp ? '✔' : '✘'} ${svc.label || key}</div>
        <div class="status" style="color:${isUp ? 'var(--green)' : 'var(--red)'}">${svc.status}</div>
        <div class="code">HTTP ${svc.code || '—'}</div>
        ${svc.error ? `<div class="error">${svc.error}</div>` : ''}`;
      grid.appendChild(card);
    }
    document.getElementById('status-dot').className = `dot ${data.overall === 'ok' ? 'green' : 'amber'}`;
  } catch {
    grid.innerHTML = '<p style="padding:24px;color:var(--red);">Failed to fetch health</p>';
  }
}
document.getElementById('refresh-health').addEventListener('click', fetchHealth);

/* ── Init ── */
renderHub();
fetchHealth();

/* Keyboard shortcut: Ctrl+Shift+T → terminal */
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.shiftKey && e.key === 'T') {
    e.preventDefault();
    document.querySelector('[data-view="terminal"]').click();
  }
});
