"""
dashboard/app.py
Flask application factory + dashboard HTML route.
"""

import os
from flask import Flask, render_template_string
from flask_cors import CORS

from modules.config import Config
from modules.logger import getLogger
from api.routes import api

logger = getLogger()

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>GitHub Repo Validator</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
  :root {
    --bg:       #0D0D1A;
    --surface:  #13131F;
    --card:     #1A1A2E;
    --border:   #2A2A45;
    --accent:   #6C63FF;
    --accent2:  #FF6B6B;
    --accent3:  #43E97B;
    --text:     #E8E8FF;
    --muted:    #7070A0;
    --high:     #FF4444;
    --medium:   #FF9800;
    --low:      #FFD600;
    --clean:    #43E97B;
    --radius:   12px;
    --mono:     'Space Mono', monospace;
    --sans:     'Inter', sans-serif;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }

  /* ── Layout ── */
  .shell { display: grid; grid-template-columns: 260px 1fr; min-height: 100vh; }

  /* ── Sidebar ── */
  .sidebar {
    background: var(--surface);
    border-right: 1px solid var(--border);
    padding: 28px 20px;
    display: flex; flex-direction: column; gap: 8px;
  }
  .logo {
    font-family: var(--mono); font-size: 15px; font-weight: 700;
    color: var(--accent); letter-spacing: 1px; margin-bottom: 32px;
    line-height: 1.4;
  }
  .logo span { color: var(--text); font-size: 11px; display: block; font-weight: 400; margin-top: 4px; }
  .nav-item {
    padding: 10px 14px; border-radius: 8px; cursor: pointer;
    font-size: 13px; font-weight: 500; color: var(--muted);
    transition: all .2s; display: flex; align-items: center; gap: 10px;
  }
  .nav-item:hover, .nav-item.active { background: var(--card); color: var(--text); }
  .nav-item.active { border-left: 3px solid var(--accent); }

  /* ── Main ── */
  .main { padding: 36px 40px; overflow-y: auto; }
  h1 { font-size: 26px; font-weight: 700; margin-bottom: 6px; }
  .subtitle { color: var(--muted); font-size: 13px; margin-bottom: 36px; }

  /* ── Input card ── */
  .input-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 28px; margin-bottom: 28px;
  }
  .input-row { display: flex; gap: 12px; align-items: stretch; }
  .url-input {
    flex: 1; padding: 13px 16px; border-radius: 8px;
    background: var(--surface); border: 1px solid var(--border);
    color: var(--text); font-family: var(--mono); font-size: 13px;
    outline: none; transition: border-color .2s;
  }
  .url-input:focus { border-color: var(--accent); }
  .url-input::placeholder { color: var(--muted); }
  .btn {
    padding: 13px 24px; border-radius: 8px; border: none;
    font-family: var(--sans); font-size: 14px; font-weight: 600;
    cursor: pointer; transition: all .2s; white-space: nowrap;
  }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { background: #5a52e8; transform: translateY(-1px); }
  .btn-primary:disabled { opacity: .5; cursor: not-allowed; transform: none; }
  .btn-outline {
    background: transparent; color: var(--accent);
    border: 1px solid var(--accent);
  }
  .btn-outline:hover { background: var(--accent); color: #fff; }

  /* ── KPI grid ── */
  .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 28px; }
  .kpi-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px; text-align: center;
  }
  .kpi-value { font-family: var(--mono); font-size: 32px; font-weight: 700; line-height: 1; margin-bottom: 6px; }
  .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); }
  .kpi-card.total .kpi-value { color: var(--accent); }
  .kpi-card.issues .kpi-value { color: var(--accent2); }
  .kpi-card.clean .kpi-value  { color: var(--clean); }
  .kpi-card.failed .kpi-value { color: var(--high); }
  .kpi-card.skipped .kpi-value{ color: var(--muted); }

  /* ── Progress ── */
  .progress-container {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 24px; margin-bottom: 28px;
    display: none;
  }
  .progress-container.visible { display: block; }
  .progress-label { font-size: 13px; color: var(--muted); margin-bottom: 10px; display: flex; justify-content: space-between; }
  .progress-bar-bg { background: var(--surface); border-radius: 99px; height: 8px; overflow: hidden; }
  .progress-bar-fill {
    height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent3));
    border-radius: 99px; transition: width .3s; width: 0%;
  }
  .progress-file { font-family: var(--mono); font-size: 11px; color: var(--muted); margin-top: 8px; }

  /* ── Table ── */
  .table-container {
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--radius); overflow: hidden; margin-bottom: 28px;
  }
  .table-header {
    padding: 16px 20px; border-bottom: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: center;
  }
  .table-title { font-size: 14px; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th {
    padding: 10px 14px; text-align: left; font-size: 11px;
    text-transform: uppercase; letter-spacing: .5px; color: var(--muted);
    background: var(--surface); border-bottom: 1px solid var(--border);
  }
  td {
    padding: 10px 14px; border-bottom: 1px solid var(--border);
    max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  tr:hover td { background: rgba(108,99,255,.06); }
  .badge {
    display: inline-block; padding: 2px 8px; border-radius: 99px;
    font-size: 10px; font-weight: 700; text-transform: uppercase;
  }
  .badge-high   { background: rgba(255,68,68,.2);  color: var(--high); }
  .badge-medium { background: rgba(255,152,0,.2);  color: var(--medium); }
  .badge-low    { background: rgba(255,214,0,.2);  color: var(--low); }
  .badge-clean  { background: rgba(67,233,123,.2); color: var(--clean); }
  .badge-skipped{ background: rgba(112,112,160,.2);color: var(--muted); }
  .badge-failed { background: rgba(255,68,68,.2);  color: var(--high); }
  .badge-success{ background: rgba(108,99,255,.2); color: var(--accent); }

  /* ── Sev bars ── */
  .sev-row { display: flex; gap: 6px; margin-top: 8px; }
  .sev-bar { flex: 1; text-align: center; padding: 6px 4px; border-radius: 6px; font-size: 11px; font-weight: 700; }
  .sev-bar.h { background: rgba(255,68,68,.2);  color: var(--high); }
  .sev-bar.m { background: rgba(255,152,0,.2);  color: var(--medium); }
  .sev-bar.l { background: rgba(255,214,0,.2);  color: var(--low); }

  /* ── History ── */
  .section { display: none; }
  .section.active { display: block; }

  /* ── Animations ── */
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
  .scanning { animation: pulse 1.5s infinite; color: var(--accent); }
  .empty-state { text-align: center; padding: 60px 20px; color: var(--muted); }
  .empty-state .icon { font-size: 48px; margin-bottom: 16px; }

  /* ── Toast ── */
  #toast {
    position: fixed; bottom: 28px; right: 28px; padding: 14px 20px;
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; font-size: 13px; transform: translateY(100px);
    transition: transform .3s; z-index: 999;
  }
  #toast.show { transform: translateY(0); }
  #toast.error { border-color: var(--high); color: var(--high); }
</style>
</head>
<body>
<div class="shell">

<!-- Sidebar -->
<aside class="sidebar">
  <div class="logo">
    🔍 GH Validator
    <span>Production AI Scanner</span>
  </div>
  <div class="nav-item active" onclick="showSection('scan')">📡 New Scan</div>
  <div class="nav-item" onclick="showSection('history')">🕐 History</div>
</aside>

<!-- Main -->
<main class="main">

  <!-- SCAN SECTION -->
  <section id="section-scan" class="section active">
    <h1>Repository Scanner</h1>
    <p class="subtitle">Hybrid AI + rule-based scanner for GitHub repositories</p>

    <div class="input-card">
      <div class="input-row">
        <input class="url-input" id="repoUrl" type="url"
               placeholder="https://github.com/owner/repository"
               onkeydown="if(event.key==='Enter') startScan()"/>
        <button class="btn btn-primary" id="scanBtn" onclick="startScan()">
          🚀 Start Scan
        </button>
      </div>
    </div>

    <!-- Progress -->
    <div class="progress-container" id="progressBox">
      <div class="progress-label">
        <span id="progressText" class="scanning">Initialising…</span>
        <span id="progressPct">0%</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="progressFill"></div>
      </div>
      <div class="progress-file" id="progressFile"></div>
    </div>

    <!-- KPIs -->
    <div class="kpi-grid" id="kpiGrid" style="display:none">
      <div class="kpi-card total"><div class="kpi-value" id="kTotalFiles">—</div><div class="kpi-label">Total Files</div></div>
      <div class="kpi-card issues"><div class="kpi-value" id="kTotalIssues">—</div><div class="kpi-label">Issues</div></div>
      <div class="kpi-card clean"><div class="kpi-value" id="kCleanFiles">—</div><div class="kpi-label">Clean</div></div>
      <div class="kpi-card failed"><div class="kpi-value" id="kFailedFiles">—</div><div class="kpi-label">Failed</div></div>
      <div class="kpi-card skipped"><div class="kpi-value" id="kSkippedFiles">—</div><div class="kpi-label">Skipped</div></div>
    </div>

    <!-- Severity -->
    <div id="sevCard" style="display:none" class="table-container" style="margin-bottom:28px">
      <div class="table-header"><span class="table-title">Severity Breakdown</span></div>
      <div style="padding:16px 20px">
        <div class="sev-row">
          <div class="sev-bar h"><span id="sevH">0</span><br/>HIGH</div>
          <div class="sev-bar m"><span id="sevM">0</span><br/>MEDIUM</div>
          <div class="sev-bar l"><span id="sevL">0</span><br/>LOW</div>
        </div>
      </div>
    </div>

    <!-- Download -->
    <div id="downloadBar" style="display:none; margin-bottom:28px">
      <button class="btn btn-outline" id="downloadBtn" onclick="downloadReport()">
        📥 Download Excel Report
      </button>
    </div>

    <!-- Results table placeholder -->
    <div class="table-container" id="resultsSection" style="display:none">
      <div class="table-header">
        <span class="table-title">File Results</span>
        <span id="tableCount" style="font-size:12px;color:var(--muted)"></span>
      </div>
      <div style="overflow-x:auto">
        <table>
          <thead>
            <tr>
              <th>File</th><th>Type</th><th>Code Type</th>
              <th>Status</th><th>Issues</th><th>Mode</th><th>Time(s)</th>
            </tr>
          </thead>
          <tbody id="resultsBody"></tbody>
        </table>
      </div>
    </div>

  </section>

  <!-- HISTORY SECTION -->
  <section id="section-history" class="section">
    <h1>Scan History</h1>
    <p class="subtitle">Recent scans stored in the local database</p>
    <div class="table-container" id="historyContainer">
      <div class="empty-state"><div class="icon">🕐</div>Loading history…</div>
    </div>
  </section>

</main>
</div>

<div id="toast"></div>

<script>
let currentJobId = null;
let pollInterval = null;

function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('section-' + name).classList.add('active');
  event.currentTarget.classList.add('active');
  if (name === 'history') loadHistory();
}

function toast(msg, isError=false) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'show' + (isError ? ' error' : '');
  setTimeout(() => t.className = '', 3500);
}

async function startScan() {
  const url = document.getElementById('repoUrl').value.trim();
  if (!url) { toast('Please enter a GitHub URL', true); return; }

  document.getElementById('scanBtn').disabled = true;
  document.getElementById('progressBox').classList.add('visible');
  document.getElementById('kpiGrid').style.display = 'none';
  document.getElementById('sevCard').style.display = 'none';
  document.getElementById('downloadBar').style.display = 'none';
  document.getElementById('resultsSection').style.display = 'none';

  try {
    const res = await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repoUrl: url })
    });
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Scan failed to start', true); resetUI(); return; }

    currentJobId = data.jobId;
    toast('Scan started — Job #' + currentJobId);
    startPolling();
  } catch(e) {
    toast('Network error: ' + e.message, true);
    resetUI();
  }
}

function startPolling() {
  clearInterval(pollInterval);
  pollInterval = setInterval(checkProgress, 1500);
}

async function checkProgress() {
  if (!currentJobId) return;
  try {
    const res = await fetch('/api/scan/' + currentJobId + '/progress');
    const data = await res.json();

    if (data.total > 0) {
      const pct = Math.round((data.completed / data.total) * 100);
      document.getElementById('progressFill').style.width = pct + '%';
      document.getElementById('progressPct').textContent = pct + '%';
      document.getElementById('progressText').textContent = `Scanning ${data.completed}/${data.total} files…`;
      document.getElementById('progressFile').textContent = '→ ' + (data.currentFile || '');
    }

    if (data.status === 'completed') {
      clearInterval(pollInterval);
      await loadResults();
    } else if (data.status === 'failed') {
      clearInterval(pollInterval);
      toast('Scan failed: ' + (data.error || 'Unknown error'), true);
      resetUI();
    }
  } catch(e) { /* retry next tick */ }
}

async function loadResults() {
  const res = await fetch('/api/scan/' + currentJobId + '/results');
  const data = await res.json();
  if (data.status !== 'completed') return;

  const s = data.summary;
  document.getElementById('progressText').textContent = '✅ Scan complete!';
  document.getElementById('progressText').classList.remove('scanning');
  document.getElementById('progressFill').style.width = '100%';
  document.getElementById('progressPct').textContent = '100%';
  document.getElementById('progressFile').textContent = '';

  document.getElementById('kTotalFiles').textContent  = s.totalFiles;
  document.getElementById('kTotalIssues').textContent = s.totalIssues;
  document.getElementById('kCleanFiles').textContent  = s.cleanFiles;
  document.getElementById('kFailedFiles').textContent = s.failedFiles;
  document.getElementById('kSkippedFiles').textContent= s.skippedFiles;

  document.getElementById('sevH').textContent = (s.severityCounts||{}).High   || 0;
  document.getElementById('sevM').textContent = (s.severityCounts||{}).Medium || 0;
  document.getElementById('sevL').textContent = (s.severityCounts||{}).Low    || 0;

  document.getElementById('kpiGrid').style.display = '';
  document.getElementById('sevCard').style.display = '';
  document.getElementById('downloadBar').style.display = '';

  toast('Scan complete — ' + s.totalIssues + ' issues found');
  document.getElementById('scanBtn').disabled = false;
}

function downloadReport() {
  if (!currentJobId) return;
  window.location.href = '/api/scan/' + currentJobId + '/report';
}

function resetUI() {
  document.getElementById('scanBtn').disabled = false;
  document.getElementById('progressBox').classList.remove('visible');
}

function statusBadge(status) {
  const m = { Clean:'clean', Success:'success', Failed:'failed', Skipped:'skipped' };
  const cls = m[status] || 'skipped';
  return `<span class="badge badge-${cls}">${status}</span>`;
}

async function loadHistory() {
  const container = document.getElementById('historyContainer');
  try {
    const res = await fetch('/api/history');
    const jobs = await res.json();
    if (!jobs.length) {
      container.innerHTML = '<div class="empty-state"><div class="icon">🕐</div>No scans yet</div>';
      return;
    }
    let html = `<table><thead><tr>
      <th>ID</th><th>Repository</th><th>Status</th>
      <th>Files</th><th>Issues</th><th>Started</th>
    </tr></thead><tbody>`;
    jobs.forEach(j => {
      const d = new Date(j.startedAt * 1000).toLocaleString();
      html += `<tr>
        <td>#${j.id}</td>
        <td style="max-width:240px;overflow:hidden;text-overflow:ellipsis">${j.repoUrl}</td>
        <td>${statusBadge(j.status.charAt(0).toUpperCase()+j.status.slice(1))}</td>
        <td>${j.totalFiles}</td>
        <td>${j.totalIssues}</td>
        <td>${d}</td>
      </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  } catch(e) {
    container.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div>Failed to load history</div>';
  }
}
</script>
</body>
</html>
"""


def createApp() -> Flask:
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY
    CORS(app)

    app.register_blueprint(api)

    @app.route("/")
    def dashboard():
        return DASHBOARD_HTML

    return app


def runDashboard():
    app = createApp()
    logger.info(
        f"Dashboard starting at http://{Config.DASHBOARD_HOST}:{Config.DASHBOARD_PORT}"
    )
    print(f"\n🌐 Dashboard: http://localhost:{Config.DASHBOARD_PORT}\n")
    app.run(
        host=Config.DASHBOARD_HOST,
        port=Config.DASHBOARD_PORT,
        debug=False,
        use_reloader=False,
    )
