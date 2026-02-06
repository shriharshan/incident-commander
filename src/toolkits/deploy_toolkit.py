"""
Deployment Intelligence Toolkit for Incident Commander

Tracks Lambda deployments and configuration changes via CloudTrail.
"""

import boto3
from datetime import datetime, timedelta
from typing import List, Dict
import json

lambda_client = boto3.client("lambda")
cloudtrail = boto3.client("cloudtrail")

FUNCTION_NAME = "demo-checkout-service"


def get_recent_deploys(service: str, time_window_minutes: int) -> List[Dict]:
    """
    Get deployment history from AWS CloudTrail

    Args:
        service: Service name (Lambda function)
        time_window_minutes: How far back to search

    Returns:
        List of deployments with timestamps and config changes
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=time_window_minutes)

    print(f"📜 Querying CloudTrail for deployments")
    print(f"   Function: {FUNCTION_NAME}")
    print(f"   Time window: {time_window_minutes} minutes")

    deployments = []

    try:
        # Query CloudTrail for Lambda configuration updates
        response = cloudtrail.lookup_events(
            LookupAttributes=[
                {
                    "AttributeKey": "EventName",
                    "AttributeValue": "UpdateFunctionConfiguration20150331v2",
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            MaxResults=50,
        )

        print(f"   ✅ Found {len(response.get('Events', []))} CloudTrail events")

        for event in response.get("Events", []):
            # Parse CloudTrail event
            event_data = json.loads(event["CloudTrailEvent"])

            request_params = event_data.get("requestParameters", {})
            function_name = request_params.get("functionName", "")

            # Filter to our function
            if FUNCTION_NAME not in function_name:
                continue

            # Extract environment variable changes
            config_changes = []
            if "environment" in request_params:
                new_env = request_params["environment"].get("variables", {})

                # Highlight important changes
                for key, value in new_env.items():
                    if key in ["FAULT_SCENARIO", "FAULT_START_TIME"]:
                        config_changes.append(
                            {
                                "type": "environment_variable",
                                "variable": key,
                                "new_value": value,
                                "criticality": "high"
                                if key == "FAULT_SCENARIO"
                                else "medium",
                            }
                        )

            # Extract memory/timeout changes
            if "memorySize" in request_params:
                config_changes.append(
                    {
                        "type": "memory_size",
                        "new_value": request_params["memorySize"],
                        "criticality": "medium",
                    }
                )

            if "timeout" in request_params:
                config_changes.append(
                    {
                        "type": "timeout",
                        "new_value": request_params["timeout"],
                        "criticality": "medium",
                    }
                )

            deployment = {
                "deployment_id": event["EventId"],
                "timestamp": event["EventTime"].isoformat(),
                "service": function_name,
                "deployed_by": event_data.get("userIdentity", {}).get(
                    "principalId", "unknown"
                ),
                "event_type": "config_update",
                "config_changes": config_changes,
                "rollback_available": True,  # Lambda keeps previous versions
            }

            deployments.append(deployment)

            print(f"   📦 Deploy {deployment['deployment_id'][:8]}...")
            print(f"      Time: {deployment['timestamp']}")
            print(f"      Changes: {len(config_changes)}")

    except Exception as e:
        print(f"   ❌ Error querying CloudTrail: {e}")
        # Graceful fallback - still return empty list rather than failing

    # Sort by timestamp (most recent first)
    deployments.sort(key=lambda x: x["timestamp"], reverse=True)

    print(f"\n   📊 Total deployments found: {len(deployments)}")

    return deployments


def get_config_diff(deployment_id: str) -> Dict:
    """
    Get detailed config changes for a specific deployment

    Args:
        deployment_id: CloudTrail event ID

    Returns:
        Dict with detailed configuration diff
    """
    print(f"🔍 Fetching config diff for deployment: {deployment_id}")

    try:
        # Query CloudTrail for specific event
        response = cloudtrail.lookup_events(
            LookupAttributes=[
                {"AttributeKey": "EventId", "AttributeValue": deployment_id}
            ],
            MaxResults=1,
        )

        if not response.get("Events"):
            print(f"   ❌ Deployment not found")
            return {"error": "Deployment not found"}

        event = response["Events"][0]
        event_data = json.loads(event["CloudTrailEvent"])

        request_params = event_data.get("requestParameters", {})
        response_elements = event_data.get("responseElements", {})

        print(f"   ✅ Retrieved deployment details")

        return {
            "deployment_id": deployment_id,
            "timestamp": event["EventTime"].isoformat(),
            "request_parameters": request_params,
            "response_elements": response_elements,
            "user_identity": event_data.get("userIdentity", {}),
        }

    except Exception as e:
        print(f"   ❌ Error fetching config diff: {e}")
        return {"error": str(e)}


def correlate_deploy_with_incident(
    incident_time: datetime, lookback_minutes: int = 60
) -> Dict:
    """
    Correlate incident with recent deployments

    Args:
        incident_time: When the incident occurred
        lookback_minutes: How far back to look for deployments

    Returns:
        Dict with correlation analysis
    """
    print(f"🔗 Correlating incident with deployments")
    print(f"   Incident time: {incident_time.isoformat()}")
    print(f"   Lookback: {lookback_minutes} minutes")

    deployments = get_recent_deploys(FUNCTION_NAME, lookback_minutes)

    if not deployments:
        print(f"   ℹ️  No recent deployments found")
        return {
            "correlation_found": False,
            "message": "No deployments in lookback window",
        }

    # Find closest deployment before incident
    deployments_before_incident = [
        d for d in deployments if datetime.fromisoformat(d["timestamp"]) < incident_time
    ]

    if not deployments_before_incident:
        print(f"   ℹ️  No deployments before incident")
        return {
            "correlation_found": False,
            "message": "No deployments before incident time",
        }

    # Get most recent deployment before incident
    most_recent = deployments_before_incident[0]
    deploy_time = datetime.fromisoformat(most_recent["timestamp"])
    time_diff = (incident_time - deploy_time).total_seconds() / 60

    # Strong correlation if deployment was within 30 minutes of incident
    correlation_strength = "strong" if time_diff <= 30 else "weak"

    print(f"\n   🎯 CORRELATION FOUND!")
    print(f"      Deploy: {most_recent['deployment_id'][:8]}...")
    print(f"      Time gap: {time_diff:.1f} minutes")
    print(f"      Strength: {correlation_strength}")

    return {
        "correlation_found": True,
        "correlation_strength": correlation_strength,
        "deployment": most_recent,
        "time_difference_minutes": time_diff,
        "likely_cause": time_diff <= 30,
    }


# For local testing
if __name__ == "__main__":
    print("Testing Deployment Intelligence Toolkit\n")

    # Test recent deployments
    deploys = get_recent_deploys(
        service="demo-checkout-service", time_window_minutes=60
    )

    print(f"\nFound {len(deploys)} deployments")

    if deploys:
        print(f"\nMost recent deployment:")
        print(json.dumps(deploys[0], indent=2, default=str))

        # Test config diff
        print("\n" + "=" * 60)
        diff = get_config_diff(deploys[0]["deployment_id"])
        print(f"\nConfig diff keys: {list(diff.keys())}")

    # Test correlation
    print("\n" + "=" * 60)
    correlation = correlate_deploy_with_incident(
        incident_time=datetime.now(), lookback_minutes=60
    )
    print(f"\nCorrelation result: {correlation.get('correlation_found')}")
