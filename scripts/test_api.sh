#!/bin/bash
BASE="${1:-http://localhost:8000}"
echo "Testing API at $BASE"
curl -s "$BASE/health" | python3 -m json.tool
curl -s "$BASE/api/tools" | python3 -m json.tool
curl -s -X POST "$BASE/api/chat/default" -H "Content-Type: application/json" -d '{"message": "What is 2+2?", "use_tools": true}' | python3 -m json.tool
