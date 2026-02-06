"""
CloudWatch Logs Toolkit for Incident Commander

Replaces mock JSON data with real CloudWatch Logs queries.
"""

import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

cloudwatch_logs = boto3.client("logs")

# CloudWatch Log Group for demo app
LOG_GROUP_NAME = "/aws/lambda/demo-checkout-service"


def search_logs(service: str, time_window_minutes: int, error_keywords: List[str]) -> Dict:
    """
    Search CloudWatch Logs for errors within time window

    Args:
        service: Service name (maps to log group)
        time_window_minutes: How far back to search
        error_keywords: Error patterns to match (e.g., ["timeout", "error"])

    Returns:
        Dict with matches, error counts, and common patterns
    """
    start_time = int((datetime.now() - timedelta(minutes=time_window_minutes)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)

    # Build CloudWatch Logs Insights query
    # Look for error-level logs matching keywords
    keywords_pattern = "|".join(error_keywords)

    query = f"""
    fields @timestamp, @message, order_id, error_type, database, query_duration_ms, user_id
    | filter level = "ERROR" or @message like /{keywords_pattern}/
    | sort @timestamp desc
    | limit 100
    """

    print(f"🔍 Searching CloudWatch Logs: {LOG_GROUP_NAME}")
    print(f"   Time window: Last {time_window_minutes} minutes")
    print(f"   Keywords: {error_keywords}")

    # Start query
    try:
        query_response = cloudwatch_logs.start_query(
            logGroupName=LOG_GROUP_NAME, startTime=start_time, endTime=end_time, queryString=query
        )

        query_id = query_response["queryId"]
        print(f"   Query ID: {query_id}")

    except Exception as e:
        print(f"   ❌ Failed to start query: {e}")
        return {"error": str(e), "matches": [], "total_errors": 0}

    # Poll for results (timeout after 30 seconds)
    max_wait = 30
    waited = 0
    while waited < max_wait:
        try:
            results = cloudwatch_logs.get_query_results(queryId=query_id)

            if results["status"] == "Complete":
                print(f"   ✅ Query completed in {waited}s")
                break
            elif results["status"] == "Failed":
                print(f"   ❌ Query failed")
                return {"error": "Query failed", "matches": [], "total_errors": 0}

        except Exception as e:
            print(f"   ⚠️  Error polling results: {e}")
            break

        time.sleep(1)
        waited += 1

    # Parse results
    matches = []
    error_types = {}

    for result in results.get("results", []):
        fields = {r["field"]: r["value"] for r in result}

        match = {
            "timestamp": fields.get("@timestamp", ""),
            "message": fields.get("@message", ""),
            "order_id": fields.get("order_id", ""),
            "error_type": fields.get("error_type", "Unknown"),
            "database": fields.get("database", ""),
            "query_duration_ms": fields.get("query_duration_ms", 0),
        }

        matches.append(match)

        error_type = match["error_type"]
        error_types[error_type] = error_types.get(error_type, 0) + 1

    total_errors = len(matches)
    most_common_error = max(error_types, key=error_types.get) if error_types else None

    print(f"   📊 Found {total_errors} errors")
    if error_types:
        print(f"   Top errors: {dict(list(error_types.items())[:3])}")

    return {
        "matches": matches,
        "total_errors": total_errors,
        "most_common_error": most_common_error,
        "error_breakdown": error_types,
        "time_range": {
            "start": datetime.fromtimestamp(start_time / 1000).isoformat(),
            "end": datetime.fromtimestamp(end_time / 1000).isoformat(),
        },
        "query_id": query_id,
    }


def get_stack_trace(request_id: str) -> str:
    """
    Get full stack trace for specific request from CloudWatch

    Args:
        request_id: Lambda request ID

    Returns:
        Concatenated log messages for the request
    """
    query = f"""
    fields @timestamp, @message
    | filter request_id = "{request_id}"
    | sort @timestamp asc
    """

    start_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)

    print(f"🔍 Fetching stack trace for request: {request_id}")

    try:
        query_response = cloudwatch_logs.start_query(
            logGroupName=LOG_GROUP_NAME, startTime=start_time, endTime=end_time, queryString=query
        )

        query_id = query_response["queryId"]

        # Poll for results
        for _ in range(30):
            results = cloudwatch_logs.get_query_results(queryId=query_id)
            if results["status"] == "Complete":
                break
            time.sleep(1)

        # Concatenate log messages
        stack_trace_lines = []
        for result in results.get("results", []):
            fields = {r["field"]: r["value"] for r in result}
            stack_trace_lines.append(fields.get("@message", ""))

        stack_trace = "\n".join(stack_trace_lines)
        print(f"   ✅ Found {len(stack_trace_lines)} log lines")

        return stack_trace

    except Exception as e:
        print(f"   ❌ Failed to fetch stack trace: {e}")
        return f"Error fetching stack trace: {e}"


def get_error_rate_over_time(time_window_minutes: int = 30, bin_minutes: int = 5) -> Dict:
    """
    Get error rate trend over time

    Args:
        time_window_minutes: Total time window
        bin_minutes: Time bucket size

    Returns:
        Dict with time series data
    """
    start_time = int((datetime.now() - timedelta(minutes=time_window_minutes)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)

    query = f"""
    fields @timestamp
    | filter level = "ERROR"
    | stats count() as error_count by bin({bin_minutes}m) as time_bucket
    | sort time_bucket asc
    """

    print(f"📈 Analyzing error rate trend ({time_window_minutes}min window, {bin_minutes}min bins)")

    try:
        query_response = cloudwatch_logs.start_query(
            logGroupName=LOG_GROUP_NAME, startTime=start_time, endTime=end_time, queryString=query
        )

        query_id = query_response["queryId"]

        # Poll for results
        for _ in range(30):
            results = cloudwatch_logs.get_query_results(queryId=query_id)
            if results["status"] == "Complete":
                break
            time.sleep(1)

        time_series = []
        for result in results.get("results", []):
            fields = {r["field"]: r["value"] for r in result}
            time_series.append(
                {
                    "timestamp": fields.get("time_bucket", ""),
                    "error_count": int(fields.get("error_count", 0)),
                }
            )

        print(f"   ✅ Generated {len(time_series)} data points")

        return {
            "time_series": time_series,
            "window_minutes": time_window_minutes,
            "bin_minutes": bin_minutes,
        }

    except Exception as e:
        print(f"   ❌ Failed to get error rate: {e}")
        return {"error": str(e), "time_series": []}


# For local testing
if __name__ == "__main__":
    print("Testing CloudWatch Logs Toolkit\n")

    # Test error search
    results = search_logs(
        service="checkout-service",
        time_window_minutes=60,
        error_keywords=["timeout", "error", "exception"],
    )

    print(f"\nResults: {results['total_errors']} errors found")
    print(f"Most common: {results['most_common_error']}")

    # Test error rate trend
    trend = get_error_rate_over_time(time_window_minutes=30, bin_minutes=5)
    print(f"\nTrend data points: {len(trend.get('time_series', []))}")
