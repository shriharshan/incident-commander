"""
CloudWatch Subscription Event Handler for Incident Commander

Processes CloudWatch Logs subscription filter events to trigger automated RCA.
"""

import base64
import gzip
import json
from typing import Dict, List, Any
from datetime import datetime


def is_subscription_event(event: Dict) -> bool:
    """Check if event is from CloudWatch Logs subscription filter"""
    return "awslogs" in event


def parse_subscription_event(event: Dict) -> Dict[str, Any]:
    """
    Parse CloudWatch Logs subscription filter event

    Returns:
        {
            "log_group": str,
            "log_stream": str,
            "subscription_filters": List[str],
            "log_events": List[Dict],
            "error_events": List[Dict],  # Parsed JSON errors only
        }
    """
    # Decompress the payload
    compressed_payload = base64.b64decode(event["awslogs"]["data"])
    uncompressed_payload = gzip.decompress(compressed_payload)
    log_data = json.loads(uncompressed_payload)

    # Extract log events
    log_events = log_data.get("logEvents", [])

    # Parse structured JSON logs and filter ERROR level
    error_events = []
    for log_event in log_events:
        try:
            message = json.loads(log_event["message"])
            if message.get("level") in ["ERROR", "CRITICAL"]:
                # Add event metadata
                message["_log_timestamp"] = log_event["timestamp"]
                message["_log_id"] = log_event["id"]
                error_events.append(message)
        except (json.JSONDecodeError, KeyError):
            # Skip non-JSON or malformed logs
            continue

    return {
        "log_group": log_data.get("logGroup", "unknown"),
        "log_stream": log_data.get("logStream", "unknown"),
        "subscription_filters": log_data.get("subscriptionFilters", []),
        "log_events": log_events,
        "error_events": error_events,
        "message_type": log_data.get("messageType", "DATA_MESSAGE"),
    }


def categorize_errors(error_events: List[Dict]) -> Dict[str, Any]:
    """
    Categorize errors by type for analysis

    Returns:
        {
            "total_errors": int,
            "categories": {
                "database": int,
                "api": int,
                "validation": int,
                "memory": int,
                "external_service": int,
                "unknown": int,
            },
            "dominant_category": str,
            "error_rate_per_minute": float,
            "sample_errors": Dict[str, List[Dict]],
        }
    """
    categories = {
        "database": [],
        "api": [],
        "validation": [],
        "memory": [],
        "external_service": [],
        "unknown": [],
    }

    for error in error_events:
        error_type = error.get("error_type", "UnknownError")
        message = error.get("message", "").lower()

        # Categorize by error_type field or message content
        if "timeout" in error_type.lower() or "database" in message:
            categories["database"].append(error)
        elif "api" in error_type.lower() or "payment" in message:
            categories["api"].append(error)
        elif "validation" in error_type.lower():
            categories["validation"].append(error)
        elif "memory" in error_type.lower():
            categories["memory"].append(error)
        elif "external" in error_type.lower() or "inventory" in message or "shipping" in message:
            categories["external_service"].append(error)
        else:
            categories["unknown"].append(error)

    # Find dominant category
    category_counts = {k: len(v) for k, v in categories.items()}
    dominant_category = (
        max(category_counts.items(), key=lambda x: x[1])[0] if error_events else "none"
    )

    # Calculate error rate (errors per minute)
    if error_events:
        timestamps = [e.get("_log_timestamp", 0) for e in error_events]
        time_span_ms = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 60000
        time_span_minutes = max(time_span_ms / 60000, 1.0)
        error_rate = len(error_events) / time_span_minutes
    else:
        error_rate = 0.0

    # Sample errors (max 3 per category)
    sample_errors = {k: v[:3] for k, v in categories.items() if v}

    return {
        "total_errors": len(error_events),
        "categories": category_counts,
        "dominant_category": dominant_category,
        "error_rate_per_minute": round(error_rate, 2),
        "sample_errors": sample_errors,
    }


def should_trigger_investigation(error_analysis: Dict) -> bool:
    """
    Determine if error volume/type warrants automated investigation

    Criteria:
    - More than 5 errors received
    - Error rate > 2 errors/minute
    - Any critical error types (memory, database timeout)
    """
    if error_analysis["total_errors"] >= 5:
        return True

    if error_analysis["error_rate_per_minute"] > 2.0:
        return True

    critical_categories = ["database", "memory"]
    for category in critical_categories:
        if error_analysis["categories"].get(category, 0) > 0:
            return True

    return False


def create_incident_context(parsed_event: Dict, error_analysis: Dict) -> Dict:
    """
    Create incident context for RCA investigation

    Returns standardized incident object for Commander Agent
    """
    # Generate incident ID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_group_short = parsed_event["log_group"].split("/")[-1]
    incident_id = f"INC-{log_group_short}-{timestamp}"

    return {
        "incident_id": incident_id,
        "source": "cloudwatch_subscription",
        "trigger_time": datetime.now().isoformat(),
        "log_group": parsed_event["log_group"],
        "log_stream": parsed_event["log_stream"],
        "error_summary": error_analysis,
        "total_log_events": len(parsed_event["log_events"]),
        "error_events": parsed_event["error_events"],
    }
