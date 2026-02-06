"""
Metrics Agent - Telemetry Analyst

Analyzes CloudWatch Metrics to detect performance spikes and anomalies.
"""

from typing import Dict
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from toolkits.metrics_toolkit import query_metrics, detect_anomalies
from state import IncidentState, AgentMessage


class MetricsAgent:
    """
    Performance telemetry analyst agent

    Analyzes CloudWatch Metrics to identify performance degradation,
    spikes, and anomalies that correlate with the incident.
    """

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Metrics Agent"

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a performance telemetry expert investigating production incidents.

Your task: Analyze CloudWatch Metrics to identify performance issues and spikes.

Guidelines:
- Compare current values to baseline
- Identify spike timing and magnitude
- Look for anomalies in latency, errors, or throughput
- Correlate metrics with incident timeline
- Quantify the severity (e.g., "3x baseline")

Return your analysis in this JSON format:
{{
    "primary_metric": "Metric with most significant change",
    "spike_detected": true/false,
    "spike_magnitude": "How much above baseline",
    "spike_start_time": "When spike started",
    "affected_metrics": ["list", "of", "metrics"],
    "confidence": 0.0-1.0,
    "reasoning": "Why you reached this conclusion"
}}""",
                ),
                (
                    "human",
                    """Incident Alert:
{alert}

Metrics Data:
{metrics_data}

Anomalies Detection:
{anomalies}

Analyze these metrics and identify performance issues.""",
                ),
            ]
        )

    def investigate(self, state: IncidentState) -> Dict:
        """
        Investigate metrics for the incident

        Args:
            state: Current incident state

        Returns:
            Dict with findings from metrics analysis
        """
        alert = state["alert"]
        service = alert.get("service", "demo-checkout-service")

        print(f"\n[{self.name}] Starting metrics investigation...")

        # Query multiple metrics
        metrics_to_check = ["p99_latency_ms", "error_count", "invocations"]
        metrics_data = {}

        for metric in metrics_to_check:
            result = query_metrics(service=service, metric=metric, time_window_minutes=30)
            metrics_data[metric] = result

        # Detect anomalies
        anomalies = detect_anomalies(service=service, metric="p99_latency_ms", lookback_hours=2)

        # Prepare context for LLM
        chain = self.prompt | self.llm

        try:
            response = chain.invoke(
                {
                    "alert": str(alert),
                    "metrics_data": str(metrics_data),
                    "anomalies": str(anomalies),
                }
            )

            # Parse LLM response
            import json

            findings = json.loads(response.content)

            print(f"[{self.name}] ✅ Analysis complete")
            print(f"   Primary metric: {findings.get('primary_metric')}")
            print(f"   Spike detected: {findings.get('spike_detected')}")
            print(f"   Confidence: {findings.get('confidence'):.2f}")

            return {
                "agent": self.name,
                "findings": findings,
                "raw_data": {"metrics": metrics_data, "anomalies": anomalies},
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
