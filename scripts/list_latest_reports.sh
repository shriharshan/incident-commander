#!/bin/bash

# Usage: ./scripts/list_latest_reports.sh
# Lists the top 5 most recent reports in the S3 bucket

# Get bucket name from Terraform state or env var logic (simplified for script)
# We'll try to find the bucket name using aws s3 ls
BUCKET=$(aws s3 ls | grep "incident-commander-reports" | awk '{print $3}')

if [ -z "$BUCKET" ]; then
    echo "❌ Could not find S3 bucket 'incident-commander-reports-*'"
    exit 1
fi

echo "🔍 Scanning s3://$BUCKET for latest reports..."
echo "=================================================="

# List objects, sort by date (column 1+2), tail the last 5
aws s3 ls "s3://$BUCKET/reports/" --recursive | sort | tail -n 5

echo "=================================================="
echo "💡 To get a link for the latest report, copy the key (everything after the date/size) and run:"
echo "   ./scripts/get_report_link.sh s3://$BUCKET/<KEY>"
