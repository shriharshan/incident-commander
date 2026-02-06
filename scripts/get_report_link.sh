#!/bin/bash

# Usage: ./scripts/get_report_link.sh <s3-uri>
# Example: ./scripts/get_report_link.sh s3://my-bucket/reports/INC-123/Report.md

if [ -z "$1" ]; then
    echo "Usage: $0 <s3-uri>"
    echo "Example: $0 s3://incident-commander-reports-123/reports/INC-001/Report.md"
    exit 1
fi

S3_URI=$1
BUCKET=$(echo $S3_URI | cut -d/ -f3)
KEY=$(echo $S3_URI | cut -d/ -f4-)

echo "generating presigned url for:"
echo "BUCKET: $BUCKET"
echo "KEY:    $KEY"

aws s3 presign "s3://$BUCKET/$KEY" --expires-in 3600
