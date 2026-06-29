---
layout: default
title: Vivify — Luxury Jewelry Platform
description: Full-stack digital platform for high-end jewelry ateliers
---

# Vivify — Luxury Jewelry Platform

> *Full-stack digital platform for high-end jewelry ateliers*

---

## Quick Links

| | |
|---|---|
| [**README**](https://github.com/Sebastiano-cr/vivify-luxury-platform) | Main repo page |
| [**API (OpenAPI)**](https://github.com/Sebastiano-cr/vivify-luxury-platform/blob/main/backend/api) | Backend API modules |
| [**TUIs**](https://github.com/Sebastiano-cr/vivify-luxury-platform/tree/main/tui) | Go/Bubble Tea terminal apps |
| [**Ledger**](https://github.com/Sebastiano-cr/vivify-luxury-platform/tree/main/ledger) | Node.js double-entry accounting |
| [**Deploy**](https://github.com/Sebastiano-cr/vivify-luxury-platform/tree/main/deploy) | Blue-green, systemd, Nginx |
| [**Tests**](https://github.com/Sebastiano-cr/vivify-luxury-platform/tree/main/tests) | 83 pytest test suite |
| [**CI**](https://github.com/Sebastiano-cr/vivify-luxury-platform/actions) | GitHub Actions workflows |
| [**License**](https://github.com/Sebastiano-cr/vivify-luxury-platform/blob/main/LICENSE) | MIT |

---

## Architecture

```
Browser (Odysseus)          TUI Apps (Go/Bubble Tea)
     │                              │
     ▼                              ▼
┌──────────────────────────────────────────┐
│          FastAPI Backend (:3334)          │
│  ┌────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Jewels │ │ Hashchain │ │ Monitoring  │ │
│  │ CRUD   │ │ (SHA256)  │ │ + Terminal  │ │
│  └────────┘ └──────────┘ └────────────┘ │
└────────────────────┬─────────────────────┘
                     │
              ┌──────┴──────┐
              │             │
          SQLite DB    Ledger API
         (vivify.db)   (:3002)
         (audit.db)
```

## Components

- **Jewel Catalog** — CRUD with validation, QR codes, AI description (Ollama)
- **Hashchain** — SHA256-linked immutable audit trail per jewel
- **Certificate** — Digital certificate with chain integrity verification
- **Ledger** — Double-entry accounting (Hono + Node.js)
- **Monitoring** — Unified health endpoint checking 5 services
- **Terminal Web** — xterm.js + WebSocket PTY with tmux persistence
- **TUIs** — 7 Bubble Tea apps for finance, catalog, SOC, monitor, backup, Zellij
- **Deploy** — Blue-green Nginx switch, systemd, CIS L1/L2

## Quick Start

```bash
git clone https://github.com/Sebastiano-cr/vivify-luxury-platform.git
cd vivify-luxury-platform

# Backend
pip install -r requirements.txt
python -m uvicorn backend.server:app --port 3334

# Dashboard
open http://localhost:3334

# TUIs
cd tui && make all
~/go/bin/lazyhub
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, Uvicorn |
| Database | SQLite3 (WAL mode) |
| Hashchain | SHA256-linked (tamper-evident) |
| TUIs | Go 1.25, Bubble Tea, Lipgloss |
| Web Terminal | xterm.js 5.3, WebSocket, PTY |
| Ledger | Node.js 23+, Hono, `node:sqlite` |
| Security | Nginx CIS L1/L2, systemd sandbox |
| Deploy | Blue-green, health checks |

---

*MIT License — [Sebastiano-cr](https://github.com/Sebastiano-cr)*
