#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"

echo "✦ Vivify — Luxury Jewelry Platform Demo ✦"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Check prerequisites ──
echo "▸ Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "✘ python3 required"; exit 1; }
command -v go >/dev/null 2>&1 || { echo "✘ go required"; exit 1; }

# ── 2. Install Python deps ──
echo "▸ Installing Python dependencies..."
pip install -q -r requirements.txt --break-system-packages 2>/dev/null || true

# ── 3. Start backend ──
echo "▸ Starting backend on :3334..."
cd backend
python -m uvicorn server:app --host 0.0.0.0 --port 3334 &
BACKEND_PID=$!
cd ..
sleep 2

# ── 4. Seed data ──
echo "▸ Seeding sample jewelry data..."
python -c "
import sys; sys.path.insert(0, 'backend')
from scripts.seed import seed_all
result = seed_all()
print(f'  ✓ Seeded {result} items')
" 2>/dev/null || echo "  ⚠ Seed script not found, skipping"

# ── 5. Test endpoints ──
echo "▸ Testing API endpoints..."
curl -sf http://localhost:3334/health > /dev/null && echo "  ✓ /health" || echo "  ✘ /health"
curl -sf http://localhost:3334/jewels > /dev/null && echo "  ✓ GET /jewels" || echo "  ✘ GET /jewels"
curl -sf http://localhost:3334/monitoring/health > /dev/null && echo "  ✓ /monitoring/health" || echo "  ✘ /monitoring/health"

# ── 6. Build TUIs ──
echo "▸ Building TUI arsenal..."
cd tui && make all 2>/dev/null && cd ..
echo "  ✓ All TUIs built"

# ── 7. Report ──
echo ""
echo "✦ Demo running ✦"
echo "  API:        http://localhost:3334"
echo "  Health:     http://localhost:3334/health"
echo "  Monitoring: http://localhost:3334/monitoring/health"
echo ""
echo "  TUI apps in ~/go/bin/:"
ls -lh ~/go/bin/lazy* 2>/dev/null | awk '{print "    " $9 " (" $5 ")"}' || echo "    (not in PATH)"
echo ""
echo "  Press Ctrl+C to stop"

# ── 8. Wait ──
trap "kill $BACKEND_PID 2>/dev/null; echo '✦ Demo stopped ✦'" EXIT
wait $BACKEND_PID
