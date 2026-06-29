import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.server import app
from backend.api.finances import ledger

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_mocks():
    yield


@pytest.fixture
def mock_ledger():
    with patch.object(ledger, "get_profit_metrics", new=AsyncMock()) as mock_metrics, \
         patch.object(ledger, "get_profit_by_channel", new=AsyncMock()) as mock_channel, \
         patch.object(ledger, "list_accounts", new=AsyncMock()) as mock_accounts, \
         patch.object(ledger, "list_transactions", new=AsyncMock()) as mock_txns, \
         patch.object(ledger, "record_sale", new=AsyncMock()) as mock_sale, \
         patch.object(ledger, "record_cost", new=AsyncMock()) as mock_cost:

        mock_metrics.return_value = {
            "revenue": 5000, "cogs": 2000, "taxes": 500,
            "gross_profit": 3000, "gross_margin": 60.0,
        }
        mock_channel.return_value = [
            {"channel": "marketplace", "revenue": 4000},
            {"channel": "direct", "revenue": 1000},
        ]
        mock_accounts.return_value = [
            {"id": "acc-1", "name": "caixa", "balance": 10000, "direction": "debit"},
            {"id": "acc-2", "name": "receita_vendas", "balance": 5000, "direction": "credit"},
        ]
        mock_txns.return_value = []
        mock_sale.return_value = {"id": "txn-1", "name": "Venda Anel via marketplace"}
        mock_cost.return_value = {"id": "txn-2", "name": "Compra de insumos"}

        yield {
            "metrics": mock_metrics,
            "channel": mock_channel,
            "accounts": mock_accounts,
            "txns": mock_txns,
            "sale": mock_sale,
            "cost": mock_cost,
        }


class TestFinancesMetrics:
    def test_get_metrics(self, mock_ledger):
        resp = client.get("/finances/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["revenue"] == 5000
        assert data["cogs"] == 2000
        assert data["gross_profit"] == 3000
        assert data["gross_margin"] == 60.0
        assert len(data["by_channel"]) == 2

    def test_get_metrics_empty(self, mock_ledger):
        mock_ledger["metrics"].return_value = {
            "revenue": 0, "cogs": 0, "taxes": 0,
            "gross_profit": 0, "gross_margin": 0,
        }
        mock_ledger["channel"].return_value = []
        resp = client.get("/finances/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["revenue"] == 0
        assert data["gross_margin"] == 0

    def test_get_metrics_ledger_unavailable(self, mock_ledger):
        mock_ledger["metrics"].side_effect = Exception("Connection refused")
        resp = client.get("/finances/metrics")
        assert resp.status_code == 502

    def test_get_metrics_ledger_timeout(self, mock_ledger):
        mock_ledger["metrics"].side_effect = TimeoutError("timeout")
        resp = client.get("/finances/metrics")
        assert resp.status_code == 502


class TestFinancesAccounts:
    def test_list_accounts(self, mock_ledger):
        resp = client.get("/finances/accounts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "caixa"

    def test_list_accounts_unavailable(self, mock_ledger):
        mock_ledger["accounts"].side_effect = Exception("down")
        resp = client.get("/finances/accounts")
        assert resp.status_code == 502


class TestFinancesTransactions:
    def test_list_transactions(self, mock_ledger):
        mock_ledger["txns"].return_value = [
            {"id": "txn-1", "name": "Venda", "entries": []}
        ]
        resp = client.get("/finances/transactions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_transactions_unavailable(self, mock_ledger):
        mock_ledger["txns"].side_effect = Exception("down")
        resp = client.get("/finances/transactions")
        assert resp.status_code == 502
