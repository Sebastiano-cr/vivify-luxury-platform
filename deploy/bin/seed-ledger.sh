#!/bin/bash
# Seed ledger with default accounts for the joalheria
# Usage: seed-ledger.sh [url]  (default: http://localhost:3002)
set -euo pipefail
BASE="${1:-http://localhost:3002}"

echo "🌱 Seeding ledger at $BASE..."
for acc in caixa contas_receber estoque_joias custo_mercadorias taxas_cartao; do
  curl -s -X POST "$BASE/accounts" -H "Content-Type: application/json" \
    -d "{\"name\":\"$acc\",\"direction\":\"debit\"}" | jq -r '.id + " " + .name'
done
curl -s -X POST "$BASE/accounts" -H "Content-Type: application/json" \
  -d '{"name":"receita_vendas","direction":"credit"}' | jq -r '.id + " " + .name'
echo "✅ Ledger seeded"
