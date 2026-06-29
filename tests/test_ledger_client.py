import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.services.ledger_client import LedgerClient


def _mock_response(data, status=200):
    m = MagicMock()
    m.status_code = status
    m.raise_for_status.return_value = None
    m.json.return_value = data
    return m


@pytest.fixture
def client():
    return LedgerClient(base_url="http://test-ledger:3002")


@pytest.fixture
def mock_httpx():
    with patch("httpx.AsyncClient") as mock:
        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        mock_client.get = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock.return_value = mock_client
        yield mock_client


class TestCreateAccount:
    @pytest.mark.asyncio
    async def test_success(self, client, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"id": "acc-1", "name": "teste"})
        result = await client.create_account("teste", "debit")
        assert result["id"] == "acc-1"
        mock_httpx.post.assert_called_once_with(
            "http://test-ledger:3002/accounts",
            json={"name": "teste", "direction": "debit"},
        )

    @pytest.mark.asyncio
    async def test_http_error(self, client, mock_httpx):
        mock_httpx.post.side_effect = Exception("timeout")
        with pytest.raises(Exception):
            await client.create_account("teste")


class TestCreateTransaction:
    @pytest.mark.asyncio
    async def test_success(self, client, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"id": "txn-1"})
        entries = [{"account_id": "acc-1", "direction": "debit", "amount": 100}]
        result = await client.create_transaction("teste", entries)
        assert result["id"] == "txn-1"
        mock_httpx.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_conflict(self, client, mock_httpx):
        mock_httpx.post.return_value = _mock_response({"id": "existing-txn"}, status=409)
        result = await client.create_transaction("teste", [])
        assert result["id"] == "existing-txn"


class TestRecordSale:
    @pytest.mark.asyncio
    async def test_full_flow(self, client):
        with patch.object(client, "get_account_id") as mock_get_id:
            mock_get_id.side_effect = lambda name: {
                "caixa": "acc-caixa",
                "receita_vendas": "acc-receita",
                "custo_mercadorias": "acc-custo",
                "estoque_joias": "acc-estoque",
            }.get(name)

            with patch.object(client, "create_transaction", new=AsyncMock()) as mock_txn:
                mock_txn.return_value = {"id": "txn-1"}
                result = await client.record_sale("Anel", "marketplace", 1500, 800, 100)

                assert result["id"] == "txn-1"
                mock_txn.assert_called_once()
                name, entries = mock_txn.call_args[0]
                assert "Venda Anel via marketplace" in name
                assert len(entries) == 4

    @pytest.mark.asyncio
    async def test_credit_card_channel(self, client):
        with patch.object(client, "get_account_id") as mock_get_id:
            def side_effect(name):
                return {
                    "caixa": "acc-caixa",
                    "contas_receber": "acc-receber",
                    "receita_vendas": "acc-receita",
                    "taxas_cartao": "acc-taxas",
                }.get(name)
            mock_get_id.side_effect = side_effect

            with patch.object(client, "create_transaction", new=AsyncMock()) as mock_txn:
                mock_txn.return_value = {"id": "txn-1"}
                await client.record_sale("Anel", "credit_card", 1500, 0, 50)

                _, entries = mock_txn.call_args[0]
                account_ids = [e["account_id"] for e in entries]
                assert "acc-receber" in account_ids
                assert "acc-taxas" in account_ids
                assert "acc-caixa" not in account_ids


class TestRecordCost:
    @pytest.mark.asyncio
    async def test_success(self, client):
        with patch.object(client, "get_account_id") as mock_get_id:
            mock_get_id.side_effect = lambda name: {
                "custo_mercadorias": "acc-custo",
                "caixa": "acc-caixa",
            }.get(name)

            with patch.object(client, "create_transaction", new=AsyncMock()) as mock_txn:
                mock_txn.return_value = {"id": "txn-1"}
                result = await client.record_cost("Compra de gemas", 500)
                assert result["id"] == "txn-1"
                mock_txn.assert_called_once()
                _, entries = mock_txn.call_args[0]
                assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_account_not_found(self, client):
        with patch.object(client, "get_account_id", return_value=None):
            with pytest.raises(ValueError, match="Account not found"):
                await client.record_cost("teste", 100)


class TestGetProfitMetrics:
    @pytest.mark.asyncio
    async def test_with_profit(self, client):
        with patch.object(client, "list_accounts", new=AsyncMock()) as mock_list:
            mock_list.return_value = [
                {"name": "receita_vendas", "balance": 10000},
                {"name": "custo_mercadorias", "balance": 4000},
                {"name": "taxas_cartao", "balance": 500},
                {"name": "caixa", "balance": 5000},
            ]
            result = await client.get_profit_metrics()
            assert result["revenue"] == 10000
            assert result["cogs"] == 4000
            assert result["taxes"] == 500
            assert result["gross_profit"] == 6000
            assert result["gross_margin"] == 60.0

    @pytest.mark.asyncio
    async def test_zero_revenue(self, client):
        with patch.object(client, "list_accounts", new=AsyncMock()) as mock_list:
            mock_list.return_value = []
            result = await client.get_profit_metrics()
            assert result["revenue"] == 0
            assert result["gross_margin"] == 0


class TestGetProfitByChannel:
    @pytest.mark.asyncio
    async def test_multiple_channels(self, client):
        with patch.object(client, "list_transactions", new=AsyncMock()) as mock_txns, \
             patch.object(client, "get_account_name", new=AsyncMock()) as mock_name:

            mock_txns.return_value = [
                {"name": "Venda Anel via marketplace", "entries": [
                    {"account_id": "acc-rec", "direction": "credit", "amount": 3000},
                ]},
                {"name": "Venda Brinco via direct", "entries": [
                    {"account_id": "acc-rec", "direction": "credit", "amount": 2000},
                ]},
            ]
            mock_name.return_value = "receita_vendas"

            result = await client.get_profit_by_channel()
            assert len(result) == 2
            channels = {c["channel"]: c["revenue"] for c in result}
            assert channels["marketplace"] == 3000
            assert channels["direct"] == 2000

    @pytest.mark.asyncio
    async def test_empty(self, client):
        with patch.object(client, "list_transactions", new=AsyncMock()) as mock_txns:
            mock_txns.return_value = []
            result = await client.get_profit_by_channel()
            assert result == []
