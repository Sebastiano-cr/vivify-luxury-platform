import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

from ..config import DB_PATH


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    # Migrate existing DBs: add columns if missing
    for col in ["price REAL DEFAULT NULL", "image_url TEXT DEFAULT NULL", "description TEXT DEFAULT NULL"]:
        try:
            with get_connection() as conn:
                conn.execute(f"ALTER TABLE jewels ADD COLUMN {col}")
        except Exception:
            pass

    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jewels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                metal TEXT NOT NULL,
                gemstones TEXT NOT NULL DEFAULT '[]',
                weight_grams REAL NOT NULL,
                origin TEXT,
                status TEXT NOT NULL DEFAULT 'cadastrada',
                hash_chain_entry_hash TEXT NOT NULL,
                qr_code_url TEXT NOT NULL,
                certificate_worm_key TEXT,
                description TEXT DEFAULT NULL,
                price REAL DEFAULT NULL,
                image_url TEXT DEFAULT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS provenance_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jewel_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                description TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                document_hash TEXT,
                FOREIGN KEY (jewel_id) REFERENCES jewels(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_jewels_status ON jewels(status);
            CREATE INDEX IF NOT EXISTS idx_jewels_metal ON jewels(metal);
            CREATE INDEX IF NOT EXISTS idx_provenance_jewel ON provenance_steps(jewel_id);
            
            CREATE TABLE IF NOT EXISTS monitored_competitors (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                last_scan TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS themes (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                tokens_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_themes_tenant ON themes(tenant_id);

            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL DEFAULT 'default',
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                config TEXT NOT NULL DEFAULT '{}',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_channels_tenant ON channels(tenant_id);

            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL UNIQUE DEFAULT 'default',
                plan TEXT NOT NULL DEFAULT 'trial',
                status TEXT NOT NULL DEFAULT 'active',
                starts_at TEXT NOT NULL,
                expires_at TEXT,
                max_products INTEGER NOT NULL DEFAULT 10,
                max_channels INTEGER NOT NULL DEFAULT 1,
                max_competitors INTEGER NOT NULL DEFAULT 3,
                max_scans_per_day INTEGER NOT NULL DEFAULT 5,
                features_json TEXT NOT NULL DEFAULT '{}',
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_subscriptions_tenant ON subscriptions(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_channels_type ON channels(type);

            CREATE TABLE IF NOT EXISTS channel_products (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                external_id TEXT DEFAULT '',
                sync_status TEXT NOT NULL DEFAULT 'pending',
                last_sync TEXT,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES jewels(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chp_channel ON channel_products(channel_id);
            CREATE INDEX IF NOT EXISTS idx_chp_product ON channel_products(product_id);

            CREATE TABLE IF NOT EXISTS sync_log (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                product_count INTEGER DEFAULT 0,
                message TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sync_log_channel ON sync_log(channel_id);
        """)


def fetchone(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def fetchall(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def execute(query: str, params: tuple = ()) -> None:
    with get_connection() as conn:
        conn.execute(query, params)
        conn.commit()
