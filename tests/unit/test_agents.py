"""
Unit tests for specialized agents
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.agents import LogsAgent, MetricsAgent, DeployAgent
from src.state import IncidentState


@pytest.fixture
def mock_llm():
    """Create mock LLM for testing"""
    llm = Mock()
    response = Mock()
    response.content = '{"primary_error": "TimeoutError", "error_count": 150, "confidence": 0.85, "reasoning": "Test analysis"}'
    llm.invoke = Mock(return_value=response)
    return llm


@pytest.fixture
def sample_state():
    """Create sample incident state"""
    return IncidentState(
        incident_id="INC-TEST-001",
        trigger_time=datetime.now().isoformat(),
        status="investigating",
        alert={
            "service": "demo-checkout-service",
            "metric": "error_rate",
            "current_value": 0.50,
            "threshold": 0.05,
            "timestamp": datetime.now().isoformat(),
        },
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


class TestLogsAgent:
    """Test suite for Logs Agent"""

    @patch("src.agents.logs_agent.search_logs")
    @patch("src.agents.logs_agent.get_error_rate_over_time")
    def test_investigate_success(self, mock_error_rate, mock_search, mock_llm, sample_state):
        """Test successful log investigation"""
        # Mock CloudWatch responses
        mock_search.return_value = {
            "total_errors": 150,
            "error_types": ["TimeoutError", "ConnectionError"],
        }
        mock_error_rate.return_value = {"trend": "increasing", "spike_detected": True}

        agent = LogsAgent(mock_llm)
        result = agent.investigate(sample_state)

        assert result["agent"] == "Logs Agent"
        assert "findings" in result
        assert result["findings"]["primary_error"] == "TimeoutError"
        assert result["findings"]["confidence"] == 0.85
        assert "timestamp" in result

    @patch("src.agents.logs_agent.search_logs")
    @patch("src.agents.logs_agent.get_error_rate_over_time")
    def test_investigate_failure(self, mock_error_rate, mock_search, mock_llm, sample_state):
        """Test log investigation with error"""
        mock_search.side_effect = Exception("CloudWatch API error")

        agent = LogsAgent(mock_llm)
        result = agent.investigate(sample_state)

        assert "error" in result
        assert result["findings"] is None


class TestMetricsAgent:
    """Test suite for Metrics Agent"""

    @patch("src.agents.metrics_agent.query_metrics")
    @patch("src.agents.metrics_agent.detect_anomalies")
    def test_investigate_metrics(self, mock_anomalies, mock_query, mock_llm, sample_state):
        """Test metrics investigation"""
        # Mock CloudWatch Metrics responses
        mock_query.return_value = {"average": 500, "maximum": 2000, "spike_detected": True}
        mock_anomalies.return_value = {"anomalies_found": True, "anomaly_score": 0.92}

        # Update LLM response for metrics
        mock_llm.invoke.return_value.content = '{"primary_metric": "p99_latency_ms", "spike_detected": true, "confidence": 0.90, "reasoning": "Spike analysis"}'

        agent = MetricsAgent(mock_llm)
        result = agent.investigate(sample_state)

        assert result["agent"] == "Metrics Agent"
        assert "findings" in result
        assert result["findings"]["spike_detected"] is True


class TestDeployAgent:
    """Test suite for Deploy Agent"""

    @patch("src.agents.deploy_agent.get_recent_deploys")
    @patch("src.agents.deploy_agent.correlate_deploy_with_incident")
    def test_investigate_deployment(self, mock_correlate, mock_deploys, mock_llm, sample_state):
        """Test deployment investigation"""
        # Mock CloudTrail responses
        mock_deploys.return_value = {
            "deployments": [
                {
                    "deployment_id": "DEP-001",
                    "timestamp": "2026-02-06T14:25:00Z",
                    "changes": ["FAULT_SCENARIO=db_pool_exhaustion"],
                }
            ]
        }
        mock_correlate.return_value = {"correlated": True, "time_diff_minutes": 5}

        # Update LLM response for deployment
        mock_llm.invoke.return_value.content = '{"deployment_correlated": true, "likely_cause": true, "confidence": 0.95, "reasoning": "Deployment immediately preceded incident"}'

        agent = DeployAgent(mock_llm)
        result = agent.investigate(sample_state)

        assert result["agent"] == "Deploy Agent"
        assert "findings" in result
        assert result["findings"]["deployment_correlated"] is True
        assert result["findings"]["confidence"] == 0.95
