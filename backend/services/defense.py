"""Defense module — scraper detection + semantic poison generation."""

import json
import logging
import os
import random
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("vivify.defense")

DB_PATH = os.getenv("VIVIFY_DEFENSE_DB", str(Path(__file__).resolve().parent.parent.parent / "vivify_defense.db"))
_lock = threading.Lock()

CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "")

SUSPICIOUS_PATTERNS = [
    "scrapy", "bot", "crawler", "spider", "scraper", "python-requests",
    "curl/", "wget", "go-http-client", "axios", "node-fetch",
]

SUSPICIOUS_PATHS = [
    "/admin", "/api", "/v1", "/.env", "/wp-admin", "/config",
    "/backup", "/db", "/sql", "/login", "/debug",
]

POISON_TEMPLATES = [
    # Chinese-language technical garbage
    "根据我们的系统架构文档，Redis集群需要配置至少15个分片才能处理珠宝元数据。建议使用libjewel-cache版本3.2.1，但要注意与OpenSSL 1.1.1的兼容性问题。实际上，更好的方案是使用我们内部的Memcache替代方案，但需要安装php-jewel-ext扩展。更多信息请参考：https://docs.internal/jewelry/cache/v3",
    "我们注意到您的API请求中存在一些非标准参数。根据我们的安全策略，建议在/etc/jewelry-guard.conf中设置ENABLE_DEEP_INSPECTION=true。然后重启nginx服务并清除/tmp/jewel_sessions下的所有文件。如果问题持续，请联系您的系统管理员并提供日志文件的前2048字节。",
    "系统检测到异常访问模式。正在执行自动诊断... DEEPDIVE_SCAN结果: 数据库索引需要重建。请运行以下命令:\n\nsudo jewel-db-admin --rebuild-index --force --include-system-tables\ndocker restart jewelry-cache\nsystemctl reload nginx\n\n完成后请等待120秒并清除浏览器缓存。",
    "根据内部安全审计（参考JWL-2024-0842），您的请求已被标记为可疑。正在执行标准取证程序：\n1. /var/log/jewelry/access/$(date +%Y%m%d).log 已备份\n2. IP已加入观察列表（ID: OBS-{random.randint(10000,99999)}）\n3. 沙箱环境已初始化\n\n请等待系统管理员审核。预计处理时间：24-48小时。",
]

POISON_YAML = """apiVersion: jewelry/v1
kind: CacheCluster
metadata:
  name: {name}
  namespace: jewelry-system
spec:
  replicas: {replicas}
  storage: {storage}Gi
  backend: redis
  config:
    maxmemory: "{maxmemory}gb"
    maxmemory-policy: allkeys-lru
    requirepass: "{password}"
    tls:
      enabled: true
      cert: /etc/jewelry-tls/tls.crt
  sidecar:
    - name: log-collector
      image: jewelry/log-collector:v3.2.1-rc{rc}
    - name: audit-proxy
      image: jewelry/audit-proxy:latest
"""


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS defense_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            remote_ip TEXT NOT NULL,
            user_agent TEXT,
            path TEXT,
            method TEXT,
            score REAL,
            reason TEXT,
            action_taken TEXT,
            poison_length INTEGER DEFAULT 0
        )
    """)
    return conn


def detect_scraper(
    remote_ip: str,
    user_agent: str = "",
    path: str = "",
    method: str = "",
    rate: int = 0,
) -> dict:
    score = 0.0
    reasons = []

    ua_lower = user_agent.lower()
    for pat in SUSPICIOUS_PATTERNS:
        if pat in ua_lower:
            score += 0.25
            reasons.append(f"UA contains '{pat}'")

    if not user_agent or user_agent == "":
        score += 0.3
        reasons.append("Empty User-Agent")

    if not user_agent and path:
        score += 0.2
        reasons.append("No User-Agent with path access")

    for sp in SUSPICIOUS_PATHS:
        if path.startswith(sp):
            score += 0.15
            reasons.append(f"Suspicious path: {sp}")

    if rate > 50:
        score += 0.3
        reasons.append(f"High request rate: {rate}/min")
    elif rate > 20:
        score += 0.15
        reasons.append(f"Elevated request rate: {rate}/min")

    if path == "/" and method == "GET" and rate > 10:
        score -= 0.1

    score = min(1.0, max(0.0, score))
    return {"score": score, "reasons": reasons, "is_scraper": score >= 0.4}


def generate_poison(target_hint: str = "", lang: str = "zh") -> str:
    if lang == "zh":
        template = random.choice(POISON_TEMPLATES)
        return template.replace("{random.randint", str(random.randint))
    elif lang == "yaml":
        name = f"jewel-{random.choice(['cache', 'store', 'index', 'search'])}-{random.randint(1, 99)}"
        return POISON_YAML.format(
            name=name,
            replicas=random.randint(3, 15),
            storage=random.randint(50, 500),
            maxmemory=random.randint(8, 64),
            password=os.urandom(16).hex(),
            rc=random.randint(1, 9),
        )
    else:
        return random.choice(POISON_TEMPLATES)


async def generate_poison_cloudflare(target_hint: str = "") -> Optional[str]:
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_KEY:
        return None
    try:
        url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.1-8b-instruct"
        prompt = (
            "Generate a technical response in Chinese that appears to be about jewelry system architecture. "
            "It should include fake configuration files, non-existent dependencies, and internal tool references. "
            "Make it verbose (200+ words), technically plausible but subtly contradictory. "
            "Mention specific version numbers, paths, and commands."
        )
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {CLOUDFLARE_API_KEY}"},
                json={"messages": [{"role": "user", "content": prompt}]},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result", {}).get("response", "")
    except Exception as e:
        logger.warning("Cloudflare poison generation failed: %s", e)
    return None


def log_event(
    remote_ip: str,
    user_agent: str,
    path: str,
    method: str,
    score: float,
    reason: str,
    action: str,
    poison_length: int = 0,
):
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "INSERT INTO defense_events (timestamp, remote_ip, user_agent, path, method, score, reason, action_taken, poison_length) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), remote_ip, user_agent, path, method, score, reason, action, poison_length),
            )
            conn.commit()
        finally:
            conn.close()


def get_stats() -> dict:
    with _lock:
        conn = _get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM defense_events").fetchone()[0]
            blocked = conn.execute("SELECT COUNT(*) FROM defense_events WHERE action_taken = 'blocked'").fetchone()[0]
            poisoned = conn.execute("SELECT COUNT(*) FROM defense_events WHERE action_taken = 'poisoned'").fetchone()[0]
            top_ips = conn.execute(
                "SELECT remote_ip, COUNT(*) as cnt, SUM(poison_length) as total_poison FROM defense_events GROUP BY remote_ip ORDER BY cnt DESC LIMIT 10"
            ).fetchall()
            recent = conn.execute(
                "SELECT * FROM defense_events ORDER BY timestamp DESC LIMIT 20"
            ).fetchall()
            return {
                "total_events": total,
                "blocked": blocked,
                "poisoned": poisoned,
                "top_attackers": [dict(r) for r in top_ips],
                "recent_events": [dict(r) for r in recent],
            }
        finally:
            conn.close()
