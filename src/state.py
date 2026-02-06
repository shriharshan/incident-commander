"""
Incident State Schema

Defines the state structure for LangGraph investigation workflow.
"""

from typing import TypedDict, List, Dict, Optional, Literal
from datetime import datetime


class AgentMessage(TypedDict):
    """Message from an agent during investigation"""

    agent: str
    timestamp: str
    message: str
    metadata: Optional[Dict]


class IncidentState(TypedDict):
    """
    State schema for incident investigation workflow

    This state is passed through all LangGraph nodes and updated
    as the investigation progresses.
    """

    # Incident metadata
    incident_id: str
    trigger_time: str
    status: Literal[
        "detecting",
        "planning",
        "investigating",
        "aggregating",
        "deciding",
        "acting",
        "completed",
        "failed",
    ]

    # Alert details
    alert: Dict

    # Investigation plan
    investigation_plan: Optional[Dict]

    # Agent messages (full conversation history)
    messages: List[AgentMessage]

    # Findings from specialized agents
    logs_findings: Optional[Dict]
    metrics_findings: Optional[Dict]
    deploy_findings: Optional[Dict]

    # Analysis results
    root_cause: Optional[str]
    confidence_score: Optional[float]
    recommended_action: Optional[str]

    # Edge case handling
    failed_agents: List[str]
    retry_count: int
    partial_results: bool

    # Output artifacts
    rca_report: Optional[str]
    chain_of_thought: Optional[List[Dict]]
