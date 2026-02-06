"""
Commander Graph - LangGraph Orchestration

Creates the investigation state graph that orchestrates all agents.
"""

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import os

from .state import IncidentState
from .nodes import (
    detect_node,
    plan_node,
    investigate_node,
    aggregate_node,
    decide_node,
    report_node,
)


def create_commander_graph() -> StateGraph:
    """
    Create the LangGraph investigation workflow

    Returns:
        Compiled StateGraph ready for execution
    """

    # Initialize LLM
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        temperature=0.1,  # Low temperature for consistent analysis
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Create workflow graph
    workflow = StateGraph(IncidentState)

    # Add nodes
    workflow.add_node("detect", detect_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("investigate", lambda state: investigate_node(state, llm))
    workflow.add_node("aggregate", aggregate_node)
    workflow.add_node("decide", lambda state: decide_node(state, llm))
    workflow.add_node("report", report_node)

    # Define edges (workflow transitions)
    workflow.set_entry_point("detect")
    workflow.add_edge("detect", "plan")
    workflow.add_edge("plan", "investigate")
    workflow.add_edge("investigate", "aggregate")
    workflow.add_edge("aggregate", "decide")
    workflow.add_edge("decide", "report")
    workflow.add_edge("report", END)

    # Compile graph
    app = workflow.compile()

    return app


# For testing/debugging
if __name__ == "__main__":
    from datetime import datetime

    # Create test alert
    test_alert = {
        "service": "demo-checkout-service",
        "metric": "error_rate",
        "current_value": 0.50,
        "threshold": 0.05,
        "severity": "critical",
        "timestamp": datetime.now().isoformat(),
    }

    # Initialize state
    initial_state = IncidentState(
        incident_id=f"INC-TEST-{int(datetime.now().timestamp())}",
        trigger_time=datetime.now().isoformat(),
        status="detecting",
        alert=test_alert,
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

    # Run graph
    print("Testing Commander Graph...")
    graph = create_commander_graph()
    result = graph.invoke(initial_state)

    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(f"Status: {result['status']}")
    print(f"Root Cause: {result.get('root_cause')}")
    print(f"Confidence: {result.get('confidence_score'):.1%}")
    print(f"\nFull RCA Report:\n{result.get('rca_report')}")
