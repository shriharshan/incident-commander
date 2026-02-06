"""
Logs Agent - Forensic Expert

Analyzes CloudWatch Logs to identify error patterns and stack traces.
"""

from typing import Dict
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from toolkits.logs_toolkit import search_logs, get_error_rate_over_time
from state import IncidentState, AgentMessage


class LogsAgent:
    """
    Forensic log analyzer agent

    Searches CloudWatch Logs for errors, patterns, and anomalies
    that may indicate the root cause of an incident.
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Logs Agent"

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a forensic log analysis expert investigating production incidents.

Your task: Analyze CloudWatch Logs to identify error patterns and potential root causes.

Guidelines:
- Focus on error-level logs and exceptions
- Look for timing correlations with the incident
- Identify most frequent error types
- Extract relevant stack traces or error messages
- Be specific about findings (include timestamps, counts, error types)

Return your analysis in this JSON format:
{{
    "primary_error": "Most common error type",
    "error_count": number,
    "error_pattern": "Description of the pattern",
    "timing": "When errors started",
    "stack_trace_summary": "Key info from stack traces",
    "confidence": 0.0-1.0,
    "reasoning": "Why you reached this conclusion"
}}""",
                ),
                (
                    "human",
                    """Incident Alert:
{alert}

CloudWatch Logs Search Results:
{logs_data}

Error Rate Trend:
{error_trend}

Analyze these logs and identify error patterns.""",
                ),
            ]
        )

    def investigate(self, state: IncidentState) -> Dict:
        """
        Investigate logs for the incident

        Args:
            state: Current incident state

        Returns:
            Dict with findings from log analysis
        """
        alert = state["alert"]
        service = alert.get("service", "demo-checkout-service")

        print(f"\n[{self.name}] Starting log investigation...")

        # Search CloudWatch Logs
        logs_data = search_logs(
            service=service,
            time_window_minutes=30,
            error_keywords=["error", "timeout", "exception", "failed"],
        )

        # Get error rate trend
        error_trend = get_error_rate_over_time(time_window_minutes=30, bin_minutes=5)

        # Prepare context for LLM
        chain = self.prompt | self.llm

        try:
            response = chain.invoke(
                {"alert": str(alert), "logs_data": str(logs_data), "error_trend": str(error_trend)}
            )

            # Parse LLM response
            import json

            findings = json.loads(response.content)

            print(f"[{self.name}] ✅ Analysis complete")
            print(f"   Primary error: {findings.get('primary_error')}")
            print(f"   Error count: {findings.get('error_count')}")
            print(f"   Confidence: {findings.get('confidence'):.2f}")

            return {
                "agent": self.name,
                "findings": findings,
                "raw_data": {"logs_search": logs_data, "error_trend": error_trend},
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
