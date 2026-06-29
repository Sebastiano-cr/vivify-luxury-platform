import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..config import LEDGER_URL

_account_cache: dict[str, str] | None = None
_account_cache_ts: datetime | None = None


class LedgerClient:
    def __init__(self, base_url: str = LEDGER_URL):
        self.base_url = base_url

    async def create_account(self, name: str, direction: str = "debit") -> Dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/accounts",
                json={"name": name, "direction": direction},
            )
            resp.raise_for_status()
            return resp.json()

    async def create_transaction(self, name: str, entries: List[Dict]) -> Dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/transactions",
                json={"name": name, "entries": entries},
            )
            if resp.status_code == 409:
                return resp.json()
            resp.raise_for_status()
            return resp.json()

    async def get_account_balance(self, account_id: str) -> Dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/accounts/{account_id}")
            resp.raise_for_status()
            return resp.json()

    async def list_accounts(self) -> List[Dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/accounts")
            resp.raise_for_status()
            return resp.json()

    async def list_transactions(self, limit: int = 100) -> List[Dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/transactions?limit={limit}")
            resp.raise_for_status()
            return resp.json()

    async def refresh_account_cache(self):
        global _account_cache, _account_cache_ts
        accounts = await self.list_accounts()
        _account_cache = {a["name"]: a["id"] for a in accounts if a.get("name")}
        _account_cache_ts = datetime.now(timezone.utc)

    async def get_account_id(self, name: str) -> Optional[str]:
        global _account_cache, _account_cache_ts
        if _account_cache is None or (datetime.now(timezone.utc) - _account_cache_ts).total_seconds() > 300:
            await self.refresh_account_cache()
        return (_account_cache or {}).get(name)

    async def record_sale(
        self,
        jewel_name: str,
        channel: str,
        price: float,
        cost: float = 0.0,
        tax: float = 0.0,
    ) -> Dict:
        entries = []
        caixa_id = await self.get_account_id("caixa")
        contas_receber_id = await self.get_account_id("contas_receber")
        receita_id = await self.get_account_id("receita_vendas")
        custo_id = await self.get_account_id("custo_mercadorias")
        estoque_id = await self.get_account_id("estoque_joias")
        taxas_id = await self.get_account_id("taxas_cartao")

        if channel in ("credit_card", "installment", "mercado_pago"):
            if contas_receber_id:
                entries.append({"account_id": contas_receber_id, "direction": "debit", "amount": round(price, 2)})
        else:
            if caixa_id:
                entries.append({"account_id": caixa_id, "direction": "debit", "amount": round(price, 2)})

        if receita_id:
            entries.append({"account_id": receita_id, "direction": "credit", "amount": round(price, 2)})

        if cost > 0 and custo_id:
            entries.append({"account_id": custo_id, "direction": "debit", "amount": round(cost, 2)})
            if estoque_id:
                entries.append({"account_id": estoque_id, "direction": "credit", "amount": round(cost, 2)})

        if tax > 0 and taxas_id:
            entries.append({"account_id": taxas_id, "direction": "debit", "amount": round(tax, 2)})

        txn_name = f"Venda {jewel_name} via {channel}"
        return await self.create_transaction(txn_name, entries)

    async def record_cost(self, description: str, amount: float, account_name: str = "custo_mercadorias") -> Dict:
        custo_id = await self.get_account_id(account_name)
        caixa_id = await self.get_account_id("caixa")
        if not custo_id or not caixa_id:
            raise ValueError(f"Account not found: {account_name} or caixa")
        entries = [
            {"account_id": custo_id, "direction": "debit", "amount": round(amount, 2)},
            {"account_id": caixa_id, "direction": "credit", "amount": round(amount, 2)},
        ]
        return await self.create_transaction(description, entries)

    async def get_profit_metrics(self) -> Dict:
        accounts = await self.list_accounts()
        balances = {a["name"]: a["balance"] for a in accounts if a.get("name")}
        revenue = balances.get("receita_vendas", 0)
        cogs = balances.get("custo_mercadorias", 0)
        taxes = balances.get("taxas_cartao", 0)
        gross_profit = revenue - cogs
        return {
            "revenue": revenue,
            "cogs": cogs,
            "taxes": taxes,
            "gross_profit": gross_profit,
            "gross_margin": round((gross_profit / revenue * 100), 1) if revenue > 0 else 0,
        }

    async def get_profit_by_channel(self) -> List[Dict]:
        txn_resp = await self.list_transactions(limit=500)
        channels = {}
        for txn in txn_resp:
            name = (txn.get("name") or "")
            if "Venda " not in name or " via " not in name:
                continue
            parts = name.rsplit(" via ", 1)
            channel_name = parts[1] if len(parts) > 1 else "unknown"
            entries = txn.get("entries", [])
            for e in entries:
                if e.get("direction") == "credit":
                    acc = await self.get_account_name(e["account_id"])
                    if acc == "receita_vendas":
                        channels.setdefault(channel_name, {"channel": channel_name, "revenue": 0})
                        channels[channel_name]["revenue"] += e["amount"]
        return list(channels.values())

    async def get_account_name(self, account_id: str) -> Optional[str]:
        global _account_cache, _account_cache_ts
        if _account_cache is None:
            await self.refresh_account_cache()
        reverse = {v: k for k, v in (_account_cache or {}).items()}
        return reverse.get(account_id)
