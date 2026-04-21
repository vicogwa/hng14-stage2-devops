#!/bin/bash
set -e

echo "Starting integration test..."

RESPONSE=$(curl -sf -X POST http://localhost:3000/submit \
  -H "Content-Type: application/json")
echo "Submit response: $RESPONSE"

JOB_ID=$(echo "$RESPONSE" | python3 -c \
  "import sys, json; print(json.load(sys.stdin)['job_id'])")
echo "Job ID: $JOB_ID"

TIMEOUT=60
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
  STATUS=$(curl -sf "http://localhost:3000/status/$JOB_ID" \
    | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
  echo "  [$ELAPSED s] status: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    echo "Integration test passed"
    exit 0
  fi

  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

echo "FAIL: job did not complete within ${TIMEOUT}s"
exit 1
