# 🐛 Agentic Bug Hunter

> **Multi-Agent AI System for Detecting Semantic Bugs in Infineon RDI C++ Test Code**

An industry-grade agentic AI pipeline that automatically discovers, validates, classifies, and explains semantic bugs in semiconductor test programs using **Google Gemini** and **Infineon's MCP documentation server**.

---

## 🏆 Hackathon Context

Built for the **Infineon Technologies Agentic Bug Hunter Track**. The challenge required building a fully agentic AI system capable of:
- Discovering semantic bugs in RDI test programs
- Validating issues against official documentation via MCP
- Producing structured explanations aligned with provided datasets

---

## 🧠 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTIC BUG HUNTER PIPELINE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   📄 Input (samples.csv / Paste Code / Upload)                  │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────────────────┐                                   │
│   │   🧠 Reasoning Agent    │  Gemini 2.5 Flash                 │
│   │   (Bug Discovery)       │  Analyzes C++ RDI code            │
│   └──────────┬──────────────┘                                   │
│              │ Bug Hypotheses (line, summary, category)         │
│              ▼                                                   │
│   ┌─────────────────────────┐                                   │
│   │   📚 MCP Knowledge      │  Infineon MCP Server              │
│   │   Agent (Grounding)     │  Vector similarity search         │
│   └──────────┬──────────────┘                                   │
│              │ Documentation Context                             │
│              ▼                                                   │
│   ┌─────────────────────────┐                                   │
│   │   ⚠️  Severity Agent    │  Gemini Classification            │
│   │   (Risk Assessment)     │  CRITICAL/HIGH/MEDIUM/LOW         │
│   └──────────┬──────────────┘                                   │
│              │ Severity + Justification                          │
│              ▼                                                   │
│   ┌─────────────────────────┐                                   │
│   │   ✏️  Explanation Agent  │  Gemini Refinement                │
│   │   (Report Refinement)   │  Dataset-style output             │
│   └──────────┬──────────────┘                                   │
│              │                                                   │
│              ▼                                                   │
│   📊 Output (CSV + HTML + JSON Reports)                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Agent Roles

| Agent | Role | Technology |
|-------|------|------------|
| **Reasoning Agent** | Bug discovery via LLM semantic analysis | Google Gemini 2.5 Flash |
| **MCP Knowledge Agent** | Documentation grounding & validation | Infineon MCP Server (FastMCP + LlamaIndex) |
| **Severity Agent** | Risk classification (Critical/High/Medium/Low) | Gemini + embedded systems context |
| **Explanation Agent** | Concise, professional report refinement | Gemini with dataset-style formatting |
| **Orchestrator** | Multi-agent coordination & trace logging | Python async pipeline |

---

## 🚀 Key Features

- **4-Agent Pipeline** with clear separation of concerns
- **Streamlit Dashboard** — interactive web UI with real-time progress
- **Severity Classification** — CRITICAL / HIGH / MEDIUM / LOW
- **Bug Categorization** — API Misuse, Logic Error, Resource Mgmt, Concurrency, etc.
- **MCP Documentation Grounding** — bugs validated against official docs
- **Multi-Format Reports** — CSV, HTML (with charts), JSON
- **Agent Execution Traces** — full observability into the pipeline
- **Code Context Viewer** — see bugs inline with surrounding code
- **Docker Support** — containerized deployment
- **Configurable Pipeline** — toggle agents, adjust prompts via YAML

---

## 📂 Project Structure

```
agentic-bug-hunter/
├── config/
│   ├── settings.yaml          # Pipeline & agent configuration
│   └── prompts.yaml           # LLM prompt templates
├── server/
│   ├── mcp_server.py          # Infineon MCP server (FastMCP)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── embedding_model/       # BAAI/bge-base-en-v1.5 (auto-downloaded)
│   └── storage/               # LlamaIndex vector store
├── src/
│   ├── app.py                 # Streamlit dashboard
│   ├── main.py                # CLI entry point
│   ├── agents/
│   │   ├── base_agent.py      # Abstract base with tracing
│   │   ├── reasoning_agent.py # Bug discovery (Gemini)
│   │   ├── mcp_agent.py       # Documentation grounding (MCP)
│   │   ├── severity_agent.py  # Severity classification
│   │   ├── explanation_agent.py # Explanation refinement
│   │   └── orchestrator.py    # Multi-agent coordinator
│   ├── models/
│   │   └── schemas.py         # Pydantic v2 data models
│   ├── reports/
│   │   └── generator.py       # CSV/HTML/JSON report generation
│   └── utils/
│       ├── config.py          # Configuration management
│       ├── logger.py          # Structured logging
│       └── helpers.py         # Utility functions
├── data/
│   ├── samples.csv            # Input code samples
│   └── outputs/               # Generated reports
├── tests/
│   ├── test_schemas.py        # Model tests
│   └── test_utils.py          # Utility tests
├── Dockerfile                 # Dashboard container
├── docker-compose.yml         # Full stack deployment
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## ⚡ Quick Start

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd agentic-bug-hunter
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your Gemini API key:
# GENAI_API_KEY=your_key_here
```

### 3. Start MCP Server (requires Infineon data)

```bash
cd server
pip install -r requirements.txt
python mcp_server.py
```

### 4. Run Dashboard

```bash
streamlit run src/app.py
```

### 5. Or Run via CLI

```bash
python -m src.main --input data/samples.csv
```

---

## 🐳 Docker Deployment

```bash
# Build and run full stack
docker-compose up --build

# Dashboard: http://localhost:8501
# MCP Server: http://localhost:8003
```

---

## 📊 Output Formats

### CSV (Hackathon format)
| ID | bug_line | Explanation |
|----|----------|-------------|
| S001 | 8 | BUG: RDI_SetForceRange called with invalid channel parameter... |

### HTML Report
Professional report with severity charts, category breakdown, code context, and statistics.

### JSON Report
Full structured data including agent traces, timing, and metadata.

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| LLM | Google Gemini 2.5 Flash |
| MCP Server | FastMCP + LlamaIndex + BAAI/bge-base-en-v1.5 |
| Data Models | Pydantic v2 |
| Dashboard | Streamlit |
| Config | YAML + python-dotenv |
| Reports | CSV, HTML, JSON |
| Containerization | Docker + Docker Compose |
| Testing | pytest |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

---

## 📝 Configuration

All settings are in `config/settings.yaml`. Key options:

```yaml
llm:
  model: "gemini-2.5-flash"    # LLM model
  temperature: 0.1              # Lower = more deterministic
  retry_attempts: 3             # Automatic retries

agents:
  reasoning:
    enabled: true
  mcp_knowledge:
    enabled: true
    min_relevance_score: 0.3    # Filter low-quality docs
  severity:
    enabled: true
  explanation:
    max_length: 200
```

Prompt templates are in `config/prompts.yaml` — fully customizable.

---

## 👥 Team

Built for the Infineon Technologies Hackathon — Agentic Bug Hunter Track.

---

## 📄 License

MIT License
