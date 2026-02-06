# Autonomous Incident Commander

AI-powered real-time incident investigation system using Multi-Agent Reasoning and CloudWatch integration.

## 🎯 Purpose

Analyzes CloudWatch logs, metrics, and deployment history to automatically diagnose incidents and generate Root Cause Analysis (RCA) reports.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- AWS CLI configured with credentials
- OpenAI API key (for LLM agents)
- Terraform (for deployment)

### Setup

```bash
# Install dependencies with uv
uv sync

# Activate virtual environment
source .venv/bin/activate

# Configure environment
cp .env.example .env
# Edit .env and add your OpenAI API key

# Run tests
uv run pytest
```

### Deploy to AWS

```bash
# Package Lambda
bash scripts/package.sh

# Deploy with Terraform
cd terraform
terraform init
terraform plan
terraform apply
```

## 📦 Project Structure

```
incident-commander/
├── src/
│   ├── agents/
│   │   ├── commander.py        # Orchestrator agent
│   │   ├── logs_agent.py       # Forensic log analyzer
│   │   ├── metrics_agent.py    # Performance analyst
│   │   └── deploy_agent.py     # Deployment historian
│   ├── nodes/
│   │   ├── detect.py           # DETECT node
│   │   ├── investigate.py      # INVESTIGATE node
│   │   └── report.py           # REPORT node
│   ├── toolkits/
│   │   ├── logs_toolkit.py     # CloudWatch Logs queries
│   │   ├── metrics_toolkit.py  # CloudWatch Metrics
│   │   └── deploy_toolkit.py   # CloudTrail integration
│   └── lambda_handler.py       # Main Lambda entry point
├── tests/
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── terraform/
│   └── modules/
│       ├── lambda/             # Commander Lambda
│       └── iam/                # IAM roles & policies
├── scripts/
│   └── package.sh              # Deployment packaging
├── pyproject.toml              # uv project config
├── .env.example                # Environment template
└── README.md
```

## 🤖 Agent Architecture

### Commander Agent
- Orchestrates investigation workflow
- Delegates to specialized agents
- Synthesizes findings into RCA

### Specialized Agents
1. **Logs Agent** - Searches CloudWatch Logs for errors
2. **Metrics Agent** - Analyzes performance metrics & spikes
3. **Deploy Agent** - Correlates deployments with incidents

## 🔬 Investigation Flow

```
DETECT → PLAN → INVESTIGATE → AGGREGATE → DECIDE → ACT → REPORT
```

1. **DETECT**: Receive alert (latency spike, error rate, etc.)
2. **PLAN**: Create investigation strategy
3. **INVESTIGATE**: Parallel agent execution (Logs + Metrics + Deploy)
4. **AGGREGATE**: Combine findings
5. **DECIDE**: Determine root cause with confidence score
6. **ACT**: Generate recommended actions
7. **REPORT**: Create RCA markdown report

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test suite
uv run pytest tests/unit/test_agents.py -v

# Integration tests (requires AWS credentials)
uv run pytest tests/integration/ -v
```

## 📊 Usage

### Trigger Investigation

```bash
# Via API (after deployment)
curl -X POST "$LAMBDA_URL/investigate" \
  -H "Content-Type: application/json" \
  -d '{
    "service": "demo-checkout-service",
    "metric": "error_rate",
    "current_value": 0.50,
    "threshold": 0.05,
    "timestamp": "2026-02-06T14:30:00Z"
  }'
```

### Local Testing

```bash
# Test with sample incident
uv run python -m src.lambda_handler --incident tests/fixtures/sample_incident.json
```

## 🔧 Configuration

Copy `.env.example` to `.env`:

```bash
OPENAI_API_KEY=sk-...
AWS_REGION=us-east-1
LOG_GROUP_NAME=/aws/lambda/demo-checkout-service
FUNCTION_NAME=demo-checkout-service
```

## 🛠️ Technologies

- **LangGraph** - Agent orchestration
- **LangChain** - LLM integration
- **OpenAI GPT-4** - Reasoning engine
- **AWS Lambda** - Serverless compute
- **CloudWatch** - Log/metrics data source
- **Boto3** - AWS SDK

## 📝 License

MIT
