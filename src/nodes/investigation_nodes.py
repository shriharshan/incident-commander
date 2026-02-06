"""
LangGraph Nodes for Investigation Workflow

Implements the investigation flow:
DETECT → PLAN → INVESTIGATE → AGGREGATE → DECIDE → REPORT
"""

from typing import Dict
from datetime import datetime
from langchain_openai import ChatOpenAI

from ..state import IncidentState, AgentMessage
from ..agents import LogsAgent, MetricsAgent, DeployAgent


def detect_node(state: IncidentState) -> Dict:
    """
    DETECT Node - Initial incident detection

    Validates alert and prepares for investigation.
    """
    print("\n" + "=" * 60)
    print("🔍 PHASE: DETECT")
    print("=" * 60)

    alert = state["alert"]
    incident_id = state["incident_id"]

    print(f"Incident ID: {incident_id}")
    print(f"Service: {alert.get('service')}")
    print(f"Metric: {alert.get('metric')}")
    print(f"Current Value: {alert.get('current_value')}")
    print(f"Threshold: {alert.get('threshold')}")

    message = AgentMessage(
        agent="System",
        timestamp=datetime.now().isoformat(),
        message=f"Incident detected: {alert.get('metric')} spike on {alert.get('service')}",
        metadata=alert,
    )

    return {"status": "planning", "messages": state["messages"] + [message]}


def plan_node(state: IncidentState) -> Dict:
    """
    PLAN Node - Create investigation strategy

    Determines which agents to invoke based on alert type.
    """
    print("\n" + "=" * 60)
    print("📋 PHASE: PLAN")
    print("=" * 60)

    alert = state["alert"]
    metric = alert.get("metric", "")

    # Determine investigation strategy
    agents_to_invoke = ["Logs Agent", "Metrics Agent", "Deploy Agent"]

    investigation_plan = {
        "agents": agents_to_invoke,
        "parallel_execution": True,
        "timeout_seconds": 30,
    }

    print(f"Investigation Plan:")
    print(f"  Agents: {', '.join(agents_to_invoke)}")
    print(f"  Execution: Parallel")

    message = AgentMessage(
        agent="Commander",
        timestamp=datetime.now().isoformat(),
        message=f"Investigation plan created: {len(agents_to_invoke)} agents will investigate",
        metadata=investigation_plan,
    )

    return {
        "status": "investigating",
        "investigation_plan": investigation_plan,
        "messages": state["messages"] + [message],
    }


def investigate_node(state: IncidentState, llm: ChatOpenAI) -> Dict:
    """
    INVESTIGATE Node - Parallel agent execution

    Invokes specialized agents to gather evidence.
    """
    print("\n" + "=" * 60)
    print("🔬 PHASE: INVESTIGATE")
    print("=" * 60)

    # Initialize agents
    logs_agent = LogsAgent(llm)
    metrics_agent = MetricsAgent(llm)
    deploy_agent = DeployAgent(llm)

    # Execute agents (would be parallel in production with ThreadPoolExecutor)
    logs_result = logs_agent.investigate(state)
    metrics_result = metrics_agent.investigate(state)
    deploy_result = deploy_agent.investigate(state)

    # Track failures
    failed_agents = []
    if logs_result.get("error"):
        failed_agents.append("Logs Agent")
    if metrics_result.get("error"):
        failed_agents.append("Metrics Agent")
    if deploy_result.get("error"):
        failed_agents.append("Deploy Agent")

    # Create messages
    messages = state["messages"].copy()
    for result in [logs_result, metrics_result, deploy_result]:
        if not result.get("error"):
            messages.append(
                AgentMessage(
                    agent=result["agent"],
                    timestamp=result["timestamp"],
                    message=f"Investigation complete: {result['findings'].get('reasoning', 'N/A')[:100]}...",
                    metadata=result["findings"],
                )
            )

    return {
        "status": "aggregating",
        "logs_findings": logs_result.get("findings"),
        "metrics_findings": metrics_result.get("findings"),
        "deploy_findings": deploy_result.get("findings"),
        "failed_agents": failed_agents,
        "partial_results": len(failed_agents) > 0,
        "messages": messages,
    }


def aggregate_node(state: IncidentState) -> Dict:
    """
    AGGREGATE Node - Combine agent findings

    Synthesizes evidence from all agents.
    """
    print("\n" + "=" * 60)
    print("📊 PHASE: AGGREGATE")
    print("=" * 60)

    logs_findings = state.get("logs_findings")
    metrics_findings = state.get("metrics_findings")
    deploy_findings = state.get("deploy_findings")

    print(f"Logs findings: {bool(logs_findings)}")
    print(f"Metrics findings: {bool(metrics_findings)}")
    print(f"Deploy findings: {bool(deploy_findings)}")
    print(f"Failed agents: {len(state.get('failed_agents', []))}")

    message = AgentMessage(
        agent="Commander",
        timestamp=datetime.now().isoformat(),
        message="Agent findings aggregated",
        metadata={
            "total_findings": sum(
                [bool(logs_findings), bool(metrics_findings), bool(deploy_findings)]
            )
        },
    )

    return {"status": "deciding", "messages": state["messages"] + [message]}


def decide_node(state: IncidentState, llm: ChatOpenAI) -> Dict:
    """
    DECIDE Node - Determine root cause

    Uses LLM to synthesize all findings into root cause analysis.
    """
    print("\n" + "=" * 60)
    print("🎯 PHASE: DECIDE")
    print("=" * 60)

    from langchain.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an expert incident investigator synthesizing evidence from multiple agents.

Your task: Determine the root cause of the incident based on all available evidence.

Guidelines:
- Consider findings from all agents (Logs, Metrics, Deploy)
- Weigh evidence by agent confidence scores
- Strong correlation between deployment and errors = likely root cause
- Quantify confidence (0.0-1.0)
- Be specific and actionable in recommendations

Return your analysis as valid JSON:
{{
    "root_cause": "Specific root cause identified",
    "confidence_score": 0.0-1.0,
    "recommended_action": "Specific action to resolve",
    "supporting_evidence": [
        "Evidence point 1",
        "Evidence point 2"
    ]
}}""",
            ),
            (
                "human",
                """Incident Alert:
{alert}

Logs Agent Findings:
{logs_findings}

Metrics Agent Findings:
{metrics_findings}

Deploy Agent Findings:
{deploy_findings}

Synthesize these findings and determine the root cause.""",
            ),
        ]
    )

    chain = prompt | llm

    try:
        response = chain.invoke(
            {
                "alert": str(state["alert"]),
                "logs_findings": str(state.get("logs_findings")),
                "metrics_findings": str(state.get("metrics_findings")),
                "deploy_findings": str(state.get("deploy_findings")),
            }
        )

        import json

        decision = json.loads(response.content)

        print(f"✅ ROOT CAUSE IDENTIFIED")
        print(f"   Cause: {decision['root_cause']}")
        print(f"   Confidence: {decision['confidence_score']:.2%}")
        print(f"   Action: {decision['recommended_action']}")

        message = AgentMessage(
            agent="Commander",
            timestamp=datetime.now().isoformat(),
            message=f"Root cause determined: {decision['root_cause']}",
            metadata=decision,
        )

        return {
            "status": "acting",
            "root_cause": decision["root_cause"],
            "confidence_score": decision["confidence_score"],
            "recommended_action": decision["recommended_action"],
            "messages": state["messages"] + [message],
        }

    except Exception as e:
        print(f"❌ Decision failed: {e}")
        return {
            "status": "failed",
            "root_cause": "Unable to determine root cause",
            "confidence_score": 0.0,
            "recommended_action": "Manual escalation required",
        }


def report_node(state: IncidentState) -> Dict:
    """
    REPORT Node - Generate RCA report

    Creates markdown RCA report with all findings.
    """
    print("\n" + "=" * 60)
    print("📝 PHASE: REPORT")
    print("=" * 60)

    # Generate RCA Report
    report = f"""# Root Cause Analysis Report

**Incident ID:** {state["incident_id"]}  
**Timestamp:** {state["trigger_time"]}  
**Service:** {state["alert"].get("service")}  
**Status:** {state["status"]}

---

## Summary

**Root Cause:** {state.get("root_cause", "Unknown")}  
**Confidence:** {state.get("confidence_score", 0.0):.1%}  
**Recommended Action:** {state.get("recommended_action", "N/A")}

---

## Alert Details

- **Metric:** {state["alert"].get("metric")}
- **Current Value:** {state["alert"].get("current_value")}
- **Threshold:** {state["alert"].get("threshold")}
- **Severity:** {state["alert"].get("severity", "unknown")}

---

## Investigation Findings

### Logs Agent
{_format_findings(state.get("logs_findings"))}

### Metrics Agent
{_format_findings(state.get("metrics_findings"))}

### Deploy Agent
{_format_findings(state.get("deploy_findings"))}

---

## Timeline

{_format_timeline(state.get("messages", []))}

---

## Recommendations

{state.get("recommended_action", "Manual investigation required")}

---

*Report generated at {datetime.now().isoformat()}*
"""

    print("✅ RCA Report generated")
    print(f"   Length: {len(report)} characters")

    # Generate chain of thought
    chain_of_thought = [
        {"phase": "DETECT", "status": "complete"},
        {"phase": "PLAN", "status": "complete"},
        {"phase": "INVESTIGATE", "status": "complete"},
        {"phase": "AGGREGATE", "status": "complete"},
        {"phase": "DECIDE", "status": "complete", "root_cause": state.get("root_cause")},
        {"phase": "REPORT", "status": "complete"},
    ]

    return {"status": "completed", "rca_report": report, "chain_of_thought": chain_of_thought}


def _format_findings(findings: Dict) -> str:
    """Format agent findings as markdown"""
    if not findings:
        return "*No findings available*"

    output = []
    for key, value in findings.items():
        if key != "reasoning":
            output.append(f"- **{key.replace('_', ' ').title()}:** {value}")

    if findings.get("reasoning"):
        output.append(f"\n**Analysis:** {findings['reasoning']}")

    return "\n".join(output)


def _format_timeline(messages: list) -> str:
    """Format message timeline as markdown"""
    if not messages:
        return "*No timeline data*"

    output = []
    for msg in messages[-10:]:  # Last 10 messages
        output.append(f"- **{msg['timestamp'][:19]}** [{msg['agent']}]: {msg['message'][:80]}...")

    return "\n".join(output)
