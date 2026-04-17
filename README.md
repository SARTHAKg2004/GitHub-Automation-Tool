# 🔍 GitHub Repository Validator
## Production-Grade Hybrid AI Scanner

A scalable, parallel GitHub repository security and quality scanner combining **rule-based fast scanning** with **Claude LLM deep scanning**. Generates professional Excel reports and provides a real-time localhost dashboard.

---

## 🏗️ Project Structure

```
github_validator/
├── main.py                    ← Entry point (CLI + dashboard launcher)
├── requirements.txt
├── .env.example               ← Copy to .env and fill in keys
│
├── modules/
│   ├── config.py              ← Environment config loader
│   ├── logger.py              ← Dual log system (scan + error)
│   ├── fileClassifier.py      ← Frontend/Backend/Config/Binary detection
│   ├── fastScanner.py         ← Rule-based regex scanner
│   ├── deepScanner.py         ← Claude LLM deep scanner
│   ├── scanner.py             ← Core orchestrator (ThreadPoolExecutor)
│   └── reportGenerator.py     ← Excel report builder (openpyxl)
│
├── api/
│   └── routes.py              ← Flask REST API (/api/scan, /api/history…)
│
├── dashboard/
│   └── app.py                 ← Flask app + embedded dashboard UI
│
├── database/
│   └── db.py                  ← SQLite scan history persistence
│
├── tests/
│   └── test_scanner.py        ← pytest unit tests
│
├── logs/
│   ├── scanLogs.log           ← Auto-created: INFO+ scan events
│   └── errorLogs.log          ← Auto-created: ERROR+ events
│
└── uploads/                   ← Cloned repos (temp) + Excel reports
```

---

## ⚡ Quick Start

### 1. Clone / Download

```bash
git clone <this-repo>
cd github_validator
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx
MAX_WORKERS=8
DEEP_SCAN_THRESHOLD=3
```

> **Note**: The scanner works without an API key using fast (rule-based) scanning only. Deep LLM scanning requires a valid `ANTHROPIC_API_KEY`.

### 4. Launch Dashboard

```bash
python main.py
```

Open **http://localhost:5000** in your browser.

### 5. CLI Mode (no dashboard)

```bash
python main.py --url https://github.com/owner/repo --output report.xlsx
```

---

## 🎛️ Configuration Options

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(empty)* | Claude API key for deep scanning |
| `MAX_WORKERS` | `8` | Parallel file processing threads |
| `MAX_FILE_SIZE_MB` | `10` | Max file size before truncated scan |
| `DEEP_SCAN_THRESHOLD` | `3` | Rule issues needed to trigger LLM |
| `LLM_TIMEOUT_SECONDS` | `30` | Per-file LLM timeout |
| `DASHBOARD_PORT` | `5000` | Dashboard HTTP port |
| `GIT_DEPTH` | `1` | Shallow clone depth (1 = fastest) |

---

## 📊 Excel Report Sheets

### Sheet 1: Summary
- KPIs: total files, issues, clean, failed, skipped
- Severity breakdown (High / Medium / Low)
- Pie chart visualisation

### Sheet 2: File Details
All 16 columns including:
- File Name, Path, Type, Code Type
- Scan Status, Issues Found, Scan Mode
- Processing Time, Error Message, Skipped Reason

### Sheet 3: All Issues
Full line-level issue details:
- Issue Type, Description, Line Number
- Severity, Suggestion/Fix, Validation Type

---

## 🔒 Security Patterns Detected (Fast Scan)

| Pattern | Severity | Type |
|---|---|---|
| `eval()` / `exec()` | High | Security |
| Hardcoded passwords | High | Security |
| Hardcoded API keys | High | Security |
| Private key material | High | Security |
| AWS credentials | High | Security |
| SQL injection via format strings | High | Security |
| `pickle.loads()` | High | Security |
| `os.system()` | Medium | Security |
| `subprocess` with `shell=True` | Medium | Security |
| Insecure HTTP URLs | Low | Security |
| Python syntax errors | High | Syntax |
| `SELECT *` queries | Low | Performance |
| Long sleep calls | Low | Performance |
| TODO / FIXME comments | Low | Best Practice |

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

---

## 🔄 Hybrid Scan Pipeline

```
File
  │
  ├─[Binary?]──────────────────────→ Skipped (binary)
  │
  ├─[Unreadable?]──────────────────→ Skipped (reason stored)
  │
  ├─[Fast Scan] ← regex + syntax
  │     │
  │     ├─[issues < threshold]──────→ Status: Clean / Success
  │     │
  │     └─[issues ≥ threshold + API key]
  │           │
  │           └─[Deep LLM Scan]─────→ Combined issues stored
  │
  └─→ Excel row + SQLite record
```

---

## 🌐 API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/scan` | Start a new scan (`{ "repoUrl": "..." }`) |
| `GET` | `/api/scan/:id/progress` | Real-time progress |
| `GET` | `/api/scan/:id/results` | Final summary |
| `GET` | `/api/scan/:id/report` | Download Excel file |
| `GET` | `/api/history` | Recent scan jobs |
| `GET` | `/api/health` | Health check |

---

## 📋 Requirements

- Python 3.10+
- Git installed and in PATH
- Internet access (to clone repos and call Anthropic API)
=======
# GitHub-Automation-Tool
>>>>>>> 99d1e87cdc71f0004b559ff56030d4ab91d2341f
