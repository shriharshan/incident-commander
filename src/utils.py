"""
Utility functions for Incident Commander
"""

import json
import os
import re
import boto3
from datetime import datetime
from typing import Dict, Any, Optional


def parse_llm_json(content: str) -> Dict[str, Any]:
    """
    Robustly parse JSON from LLM output, handling markdown code blocks.

    Args:
        content: Raw string output from LLM

    Returns:
        Parsed dictionary

    Raises:
        json.JSONDecodeError: If parsing fails
    """
    if not content:
        raise ValueError("Empty content received from LLM")

    # Strip markdown code blocks if present
    # Pattern matches ```json ... ``` or just ``` ... ```
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, content, re.DOTALL)

    if match:
        json_str = match.group(1)
    else:
        json_str = content.strip()

    return json.loads(json_str)


def upload_report_to_s3(report_content: str, incident_id: str) -> Dict[str, str]:
    """
    Upload RCA report to S3 and generate a presigned URL.

    Args:
        report_content: Markdown content of the report
        incident_id: ID of the incident

    Returns:
        Dict containing 's3_uri' and 'presigned_url'
    """
    bucket_name = os.getenv("REPORTS_BUCKET")

    if not bucket_name:
        print("⚠️ REPORTS_BUCKET env var not set. Skipping upload.")
        return {}

    s3_client = boto3.client("s3")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    object_key = f"reports/{incident_id}/RCA_Report_{timestamp}.md"

    try:
        # Upload file
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=report_content,
            ContentType="text/markdown",
            CacheControl="max-age=3600",
        )

        # Generate presigned URL
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=3600,  # 1 hour
        )

        return {"s3_uri": f"s3://{bucket_name}/{object_key}", "presigned_url": url}

    except Exception as e:
        print(f"❌ Failed to upload report to S3: {e}")
        return {}
