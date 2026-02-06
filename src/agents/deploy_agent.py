"""
Deploy Agent - Deployment Historian

Analyzes CloudTrail to correlate deployments with incidents.
"""

from typing import Dict
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from ..toolkits.deploy_toolkit import get_recent_deploys, correlate_deploy_with_incident
from ..state import IncidentState, AgentMessage


class DeployAgent:
    """
    Deployment history analyst agent

    Tracks Lambda deployments and configuration changes via CloudTrail
    to identify if a recent deployment caused the incident.
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Deploy Agent"

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a deployment history expert investigating production incidents.

Your task: Analyze recent deployments and configuration changes to determine if they caused the incident.

Guidelines:
- Look for deployments shortly before the incident
- Identify configuration changes (env vars, memory, timeout)
- Strong correlation if deployment within 30 min of incident
- Focus on high-criticality changes (FAULT_SCENARIO, connection pool size)
- Consider deployment timing relative to error spike

Return your analysis in this JSON format:
{{
    "deployment_correlated": true/false,
    "deployment_id": "ID if found",
    "deployment_time": "When deployed",
    "time_difference_minutes": number,
    "config_changes": ["list", "of", "changes"],
    "likely_cause": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Why you reached this conclusion"
}}""",
                ),
                (
                    "human",
                    """Incident Alert:
{alert}

Recent Deployments:
{deployments}

Correlation Analysis:
{correlation}

Analyze these deployments and determine if they caused the incident.""",
                ),
            ]
        )

    def investigate(self, state: IncidentState) -> Dict:
        """
        Investigate deployments for the incident

        Args:
            state: Current incident state

        Returns:
            Dict with findings from deployment analysis
        """
        alert = state["alert"]
        service = alert.get("service", "demo-checkout-service")
        incident_time_str = alert.get("timestamp")

        print(f"\n[{self.name}] Starting deployment investigation...")

        # Get recent deployments
        deployments = get_recent_deploys(service=service, time_window_minutes=60)

        # Correlate with incident
        incident_time = datetime.fromisoformat(incident_time_str.replace("Z", "+00:00"))
        correlation = correlate_deploy_with_incident(
            incident_time=incident_time, lookback_minutes=60
        )

        # Prepare context for LLM
        chain = self.prompt | self.llm

        try:
            response = chain.invoke(
                {
                    "alert": str(alert),
                    "deployments": str(deployments),
                    "correlation": str(correlation),
                }
            )

            # Parse LLM response
            import json

            findings = json.loads(response.content)

            print(f"[{self.name}] ✅ Analysis complete")
            print(f"   Deployment correlated: {findings.get('deployment_correlated')}")
            if findings.get("deployment_correlated"):
                print(f"   Time difference: {findings.get('time_difference_minutes')} min")
            print(f"   Confidence: {findings.get('confidence'):.2f}")

            return {
                "agent": self.name,
                "findings": findings,
                "raw_data": {"deployments": deployments, "correlation": correlation},
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"[{self.name}] ❌ Investigation failed: {e}")
            return {
                "agent": self.name,
                "error": str(e),
                "findings": None,
                "timestamp": datetime.now().isoformat(),
            }

    def add_message(self, state: IncidentState, content: str) -> AgentMessage:
        """Create agent message for state history"""
        return AgentMessage(
            agent=self.name, timestamp=datetime.now().isoformat(), message=content, metadata=None
        )
