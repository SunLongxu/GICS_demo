#!/bin/bash
# 前后端连通性冒烟测试（需先启动 backend/ICSGNN: python run_api.py）
set -uo pipefail

API="${API_BASE:-http://localhost:5001}"
PASS=0
FAIL=0

check() {
  local name="$1"
  shift
  if "$@"; then
    echo "✓ $name"
    PASS=$((PASS + 1))
  else
    echo "✗ $name"
    FAIL=$((FAIL + 1))
  fi
}

check "GET /test" curl -sf "$API/test" | grep -q success
check "GET initial p=5" curl -sf "$API/api/graph/initial?dataset=DBLP&model=GNN&parameter=5" | grep -q '"status"'
check "GET initial p=30" curl -sf "$API/api/graph/initial?dataset=DBLP&model=GNN&parameter=30" | grep -q '"status"'
check "GET initial query" curl -sf "$API/api/graph/initial?dataset=DBLP&model=GNN&parameter=10&query=Jiawei%20Han" | grep -q '"type": "query"'
check "POST search GNN" curl -sf -X POST "$API/api/search" -H 'Content-Type: application/json' \
  -d '{"query":"Jiawei Han","dataset":"DBLP","model":"GNN","parameter":10}' | grep -q '"type": "query"'
check "POST search ACQ" curl -sf -X POST "$API/api/search" -H 'Content-Type: application/json' \
  -d '{"query":"Jiawei Han","dataset":"DBLP","model":"ACQ","parameter":10}' | grep -q '"model": "ACQ"'
check "POST search WCS" curl -sf -X POST "$API/api/search" -H 'Content-Type: application/json' \
  -d '{"query":"Jiawei Han","dataset":"DBLP","model":"WCS","parameter":10}' | grep -q '"model": "WCS"'
check "GET visualtest" curl -sf "$API/api/visualtest" | grep -q '"status"'

echo ""
echo "Passed: $PASS  Failed: $FAIL"
test "$FAIL" -eq 0
