"""
Lambda Handler for Incident Commander

AWS Lambda entry point for investigation workflow.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv()

from .graph import create_commander_graph
from .state import IncidentState


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for incident investigation

    Args:
        event: Lambda event with alert data
        context: Lambda context

    Returns:
        Dict with RCA report and findings
    """

    print(f"🚀 Incident Commander invoked")
    print(f"Request ID: {context.request_id}")

    # Parse alert from event
    if "body" in event:
        body = json.loads(event["body"])
        alert = body.get("alert", body)
    else:
        alert = event

    print(f"Alert: {alert.get('service')} - {alert.get('metric')}")

    # Initialize state
    initial_state = IncidentState(
        incident_id=f"INC-{context.request_id[:8].upper()}",
        trigger_time=datetime.now().isoformat(),
        status="detecting",
        alert=alert,
        investigation_plan=None,
        messages=[],
        logs_findings=None,
        metrics_findings=None,
        deploy_findings=None,
        root_cause=None,
        confidence_score=None,
        recommended_action=None,
        failed_agents=[],
        retry_count=0,
        partial_results=False,
        rca_report=None,
        chain_of_thought=None,
    )

    try:
        # Create and run investigation graph
        graph = create_commander_graph()
        final_state = graph.invoke(initial_state)

        print(f"✅ Investigation complete")
        print(f"Root Cause: {final_state.get('root_cause')}")
        print(f"Confidence: {final_state.get('confidence_score'):.1%}")

        # Return response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "incident_id": final_state["incident_id"],
                    "status": final_state["status"],
                    "root_cause": final_state.get("root_cause"),
                    "confidence_score": final_state.get("confidence_score"),
                    "recommended_action": final_state.get("recommended_action"),
                    "rca_report": final_state.get("rca_report"),
                    "chain_of_thought": final_state.get("chain_of_thought"),
                    "partial_results": final_state.get("partial_results", False),
                    "failed_agents": final_state.get("failed_agents", []),
                },
                default=str,
            ),
        }

    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback

        traceback.print_exc()

        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"error": str(e), "incident_id": initial_state["incident_id"], "status": "failed"}
            ),
        }


# For local testing
if __name__ == "__main__":

    class MockContext:
        request_id = "local-test-12345"
        function_name = "incident-commander-local"

    test_event = {
        "service": "demo-checkout-service",
        "metric": "error_rate",
        "current_value": 0.50,
        "threshold": 0.05,
        "severity": "critical",
        "timestamp": datetime.now().isoformat(),
    }

    print("Testing Lambda Handler Locally...")
    print("=" * 60)

    result = handler(test_event, MockContext())

    print("\n" + "=" * 60)
    print("LAMBDA RESPONSE")
    print("=" * 60)
    print(json.dumps(json.loads(result["body"]), indent=2))
