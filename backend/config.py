import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = os.getenv("VIVIFY_DB_PATH", str(BASE_DIR / "vivify_backend.db"))

AUDIT_DB_PATH = os.getenv("AUDIT_CHAIN_DB", str(BASE_DIR / "audit_chain.db"))

MATERIALVIEW_URL = os.getenv("MATERIALVIEW_URL", "http://localhost:3001")
LEDGER_URL = os.getenv("LEDGER_URL", "http://localhost:3002")

SOC_GATEWAY_URL = os.getenv("SOC_GATEWAY_URL", "http://localhost:3333")
WAVESPEED_API_KEY = os.getenv("WAVESPEED_API_KEY", "")
