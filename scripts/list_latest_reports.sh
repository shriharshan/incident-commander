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

# Get the absolute latest key for convenience
LATEST_KEY=$(aws s3 ls "s3://$BUCKET/reports/" --recursive | sort | tail -n 1 | awk '{print $4}')

echo "=================================================="
echo "� To get the link for the MOST RECENT report, just run this:"
echo ""
echo "    ./scripts/get_report_link.sh s3://$BUCKET/$LATEST_KEY"
echo ""
