from fastapi import APIRouter, HTTPException
from ..services.ledger_client import LedgerClient
from ..storage.db import fetchone

router = APIRouter(prefix="/finances", tags=["finances"])
ledger = LedgerClient()


@router.get("/metrics")
async def get_metrics():
    try:
        metrics = await ledger.get_profit_metrics()
        channels = await ledger.get_profit_by_channel()
        return {**metrics, "by_channel": channels}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ledger unavailable: {e}")


@router.get("/accounts")
async def list_accounts():
    try:
        return await ledger.list_accounts()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ledger unavailable: {e}")


@router.get("/transactions")
async def list_transactions(limit: int = 100):
    try:
        return await ledger.list_transactions(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ledger unavailable: {e}")


@router.post("/record-sale")
async def record_sale(
    jewel_id: str,
    channel: str = "marketplace",
    price: float = 0,
    cost: float = 0,
    tax: float = 0,
):
    row = fetchone("SELECT name, price, cost FROM jewels WHERE id = ?", (jewel_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Jewel not found")
    try:
        result = await ledger.record_sale(
            jewel_name=row["name"],
            channel=channel,
            price=price or (row["price"] or 0),
            cost=cost,
            tax=tax,
        )
        return {"status": "ok", "transaction": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ledger error: {e}")


@router.post("/record-cost")
async def record_cost(
    description: str,
    amount: float,
    account_name: str = "custo_mercadorias",
):
    try:
        result = await ledger.record_cost(description, amount, account_name)
        return {"status": "ok", "transaction": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ledger error: {e}")
