# Vivify — Luxury Jewelry Management Platform

> **English** · [Português](./README.pt-BR.md)

[![CI](https://github.com/Sebastiano-cr/vivify-luxury-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Sebastiano-cr/vivify-luxury-platform/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue?logo=python)](https://python.org)
[![Go 1.25](https://img.shields.io/badge/Go-1.25-00ADD8?logo=go)](https://go.dev)
[![Tests](https://img.shields.io/badge/tests-83%20passing-brightgreen)]()

Vivify is a full-stack digital platform for high-end jewelry ateliers — from catalog management and immutable provenance tracking to sales, financial ledger, monitoring, and blue-green deployment.

Built with **FastAPI** (Python), **Bubble Tea** (Go TUIs), **SQLite**, and a **terminal web** (xterm.js + WebSocket).

---

## ✦ Why Vivify?

| Problem | Solution |
|---------|----------|
| Jewelry ateliers need digital certification + provenance | **Hashchain** — SHA256-linked immutable audit trail per jewel |
| Spreadsheets for accounting and inventory | **Ledger** — double-entry accounting integrated at sale time |
| Multiple tools, no unified operations view | **TUI arsenal** — 6 terminal apps for finance, catalog, SOC, monitoring, backup, and a hub menu |
| Context switching between browser and terminal | **Web terminal** — xterm.js inside the dashboard, zero alt-tab |
| Risky manual deploys | **Blue-green deployment** — atomic Nginx switch + health checks + rollback |

---

## ✦ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Browser (Odysseus)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Dashboard │  │ Catalog  │  │ Finance  │  │ Terminal (xterm)  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
└───────┼──────────────┼──────────────┼───────────────────┼─────────┘
        │              │              │                   │
        ▼              ▼              ▼                   ▼ WebSocket
┌──────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend (:3334)                    │
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Jewels │ │ Hashchain │ │ Ledger   │ │ Monitoring│ │ Security  │ │
│  │ CRUD   │ │ (SHA256)  │ │ Client   │ │ Endpoint │ │ (CIS L1)  │ │
│  └────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
└──────────────────────────────────────────────────────────────────┘
        │                             │
        ▼                             ▼
┌──────────────┐         ┌──────────────────────┐
│   SQLite DB  │         │  Ledger REST API     │
│  (vivify.db) │         │  (double-entry)      │
│  (audit.db)  │         │  http://localhost:3002│
└──────────────┘         └──────────────────────┘
```

---

## ✦ Quick Start

### Prerequisites
- Python 3.11+
- Go 1.25+ (for TUIs)
- Node.js 23+ (for Ledger — requires built-in `node:sqlite`)

### 1. Backend

```bash
git clone https://github.com/Sebastiano-cr/vivify-luxury-platform.git
cd vivify-luxury-platform

pip install -r requirements.txt
cd backend
python -m uvicorn server:app --reload --port 3334
```

### 2. Ledger (double-entry accounting)

```bash
cd ../ledger
npm install
npx tsx src/index.ts
```

### 3. TUIs (terminal apps)

```bash
cd ../tui
make all

# Run the hub
~/go/bin/lazyhub
```

### 4. Demo Script (one command)

```bash
bash scripts/demo.sh
```

---

## ✦ TUI Arsenal

| App | Size | What it does | Run |
|-----|------|-------------|-----|
| **lazyledger** | 9.7MB | Finance dashboard — accounts, transactions, P&L | `lazyledger` |
| **lazyvivify** | 9.8MB | Jewel catalog — list, detail, sell, hashchain, AI describe | `lazyvivify` |
| **lazysoc** | 9.6MB | SOC gateway monitor + audit chain viewer | `lazysoc` |
| **lazymon** | 9.5MB | Unified service health dashboard | `lazymon` |
| **lazybackup** | 4.1MB | Database + WORM backup with rotation | `lazybackup` |
| **lazyzellij** | 2.6MB | Zellij multiplexer with 4-tab layout | `lazyzellij` |
| **lazyhub** | 4.2MB | Central menu — browse and launch any tool | `lazyhub` |

```
┌─────────────────────────────────────────┐
│  LAZYHUB — Central Menu                  │
│                                         │
│  > 💰 LazyLedger (finanças)              │
│    💎 LazyVivify (joias)                 │
│    🧠 LazySOC (LLM gateway)             │
│    📊 LazyMon (monitor)                  │
│    💾 LazyBackup (backups)               │
│    🚀 LazyZellij (multiplex)            │
│    📦 LazyGit (repos)                    │
│    🗄️ LazySQL (bancos)                   │
│    🔵 Deploy Blue                        │
│    🟢 Deploy Green                       │
│    ↩️  Rollback                          │
└─────────────────────────────────────────┘
```

---

## ✦ Features

### Jewel Catalog
- CRUD with full validation (metal type, gemstones, weight)
- Immutable **hashchain** — every operation creates a SHA256-linked entry
- **QR code** generation per jewel
- **AI description** generation via local LLM (Ollama)
- Certificate integration with WORM storage

### Financial Ledger
- Double-entry accounting (debit/credit)
- Automated transaction creation on sale
- Channel-based profit tracking (marketplace, direct, credit card)
- Real-time P&L metrics (revenue, COGS, gross margin)

### Monitoring & Operations
- Unified health endpoint (`GET /monitoring/health`)
- Service status dashboard (lazymon)
- Blue-green deployment with zero-downtime Nginx switch
- Automated DB backup with 7-day rotation
- CIS L1/L2 security hardening (Nginx + systemd)

### Terminal Web
- Real browser-based terminal via xterm.js + WebSocket
- Multiple tabs, each with independent PTY
- tmux session persistence across page refreshes
- Keyboard shortcut: `Ctrl+Shift+T`

---

## ✦ Tests

```bash
pip install -r requirements.txt
pytest tests/ -q
```

**83 tests** covering: jewels CRUD, certificates, finances, ledger client, marketplace, trends, defense, browser agent, onboarding.

---

## ✦ Deploy

```bash
# Blue-green deployment
deploy-vivify blue    # Deploy blue environment
deploy-vivify green   # Deploy green environment
rollback-vivify       # Atomic rollback to previous color

# Backup
backup                # Daily backup (DBs + WORM + 7-day rotation)
```

---

## ✦ Security

- **Nginx**: rate limiting (30r/s API, 5r/m auth), HSTS preload, CSP, X-Frame-Options DENY, `server_tokens off`
- **Systemd**: `ProtectSystem=strict`, `NoNewPrivileges=yes`, `MemoryDenyWriteExecute=yes`, capability drop
- **API**: CORS whitelist, security headers middleware
- **CVE-2026-42945**: Nginx version ≥1.30.1 enforced

---

## ✦ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, Uvicorn |
| Database | SQLite3 (production-grade with WAL mode) |
| Hashchain | SHA256-linked entries (tamper-evident audit trail) |
| TUIs | Go 1.25, Bubble Tea, Bubbles, Lipgloss |
| Web Terminal | xterm.js 5.3, WebSocket, PTY (os.fork + os.openpty) |
| Ledger | Node.js, Hono, double-entry accounting, `node:sqlite` |
| Security | Nginx CIS L1/L2, systemd sandboxing |
| Deploy | Blue-green, systemd templates, health checks |

---

## ✦ License

MIT — see [LICENSE](./LICENSE).
