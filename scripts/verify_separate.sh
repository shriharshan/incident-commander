#!/bin/bash
set -e

DEMO_FUNCTION="demo-checkout-service"
COMMANDER_FUNCTION="incident-commander"

echo "🧪 MANUAL SEPARATE VERIFICATION"
echo "=============================="

# 1. Trigger Demo App (Generate Logs)
echo -e "\n1️⃣  Running Demo App (Generating 504 Error Logs)..."
echo "   (This writes to CloudWatch Logs so the Agent has something to find)"

# Set fault to timeout
aws lambda update-function-configuration \
  --function-name $DEMO_FUNCTION \
  --environment "Variables={FAULT_SCENARIO=db_pool_exhaustion,LOG_LEVEL=INFO}" > /dev/null
sleep 5 # Wait for update

# Invoke to generate log entry
aws lambda invoke \
  --function-name $DEMO_FUNCTION \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  response.json > /dev/null

echo "   ✅ Demo App Executed. Response:"
cat response.json
echo ""

# Reset fault
aws lambda update-function-configuration \
  --function-name $DEMO_FUNCTION \
  --environment "Variables={FAULT_SCENARIO=normal,LOG_LEVEL=INFO}" > /dev/null

echo "   ⏳ Waiting 15s for logs to propagate in CloudWatch..."
sleep 15


# 2. Trigger Incident Agent (Manual Invoke)
echo -e "\n2️⃣  Running Incident Agent (Manual Trigger)..."
echo "   (Bypassing CloudWatch Subscription Filter)"

PAYLOAD='{
  "service": "demo-checkout-service",
  "metric": "MANUAL_TEST_TRIGGER",
  "current_value": 1.0,
  "threshold": 0.0,
  "severity": "critical",
  "trigger_source": "manual_verification"
}'

aws lambda invoke \
  --function-name $COMMANDER_FUNCTION \
  --payload "$PAYLOAD" \
  --cli-binary-format raw-in-base64-out \
   commander_response.json > /dev/null

echo "   ✅ Incident Agent Executed. Response:"
cat commander_response.json | jq .

echo -e "\n\n🎉 Verification Complete!"
echo "You ran the Demo App and the Agent separately."
