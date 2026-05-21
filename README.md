# 🐛 Agentic Bug Hunter

> **Multi-Agent AI System for Detecting Semantic Bugs in C/C++ Code**

An industry-grade agentic AI pipeline that automatically discovers, validates, classifies, and explains semantic bugs in C/C++ test programs using **Google Gemini** and an **MCP documentation server** with vector similarity search.

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
│   │   (Bug Discovery)       │  Analyzes C/C++ code              │
│   └──────────┬──────────────┘                                   │
│              │ Bug Hypotheses (line, summary, category)         │
│              ▼                                                   │
│   ┌─────────────────────────┐                                   │
│   │   📚 MCP Knowledge      │  MCP Server (FastMCP)             │
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
| **MCP Knowledge Agent** | Documentation grounding & validation | MCP Server (FastMCP + LlamaIndex) |
| **Severity Agent** | Batch risk classification (Critical/High/Medium/Low) | Gemini — 1 API call for all bugs |
| **Explanation Agent** | Batch report refinement to dataset-style output | Gemini — 1 API call for all bugs |
| **Orchestrator** | Multi-agent coordination, caching & trace logging | Python pipeline |

---

## 🚀 Key Features

### Core Pipeline
- **4-Agent Pipeline** with clear separation of concerns
- **Batch Processing** — Severity & Explanation agents process all bugs in a single API call each
- **Automatic Retry with Rate Limiting** — thread-safe rate limiter (5 req/min) + smart retry with API-suggested delays
- **Agent Execution Tracing** — every agent step is timed and logged as an `AgentEvent`

### Cache & Demo System
- **SHA-256 Content-Addressed Cache** — results are cached by code hash, so identical code always returns cached results
- **Demo Mode** — replay previous analyses with **zero API calls** (perfect for presentations and demos)
- **Cache Index** — `cache/index.json` tracks all cached entries with sample IDs and timestamps
- **Cache-only fallback** — demo mode returns empty results gracefully when no cache exists

### Classification & Taxonomy
- **Severity Classification** — CRITICAL / HIGH / MEDIUM / LOW with strict classification rules
- **Bug Categorization** — API_MISUSE, LOGIC_ERROR, RESOURCE_MGMT, CONCURRENCY, CONFIG_ERROR, ERROR_HANDLING, TYPE_ERROR, SECURITY, BUFFER_OVERFLOW
- **CWE Taxonomy Mapping** — every bug category is auto-mapped to industry-standard CWE identifiers (e.g., CWE-120 Buffer Overflow, CWE-362 Race Condition)

### Benchmarking & Evaluation
- **Ground Truth Benchmarking** — compare detected bugs against annotated ground truth (`data/ground_truth.json`)
- **Precision / Recall / F1-Score** — computed per-sample and aggregated across all samples
- **Line Tolerance Matching** — ±1 line tolerance for bug location matching
- **Per-Sample Breakdown** — see matched lines, missed lines, and extra detections for each sample

### Dashboard (Streamlit)
- **Interactive Web UI** with 6 tabs: Analyze, Results, Code View, Benchmark, Pipeline, About
- **Two Input Modes** — upload CSV or paste code directly
- **Pipeline Toggle Controls** — enable/disable MCP, Severity, Explanation agents from the sidebar
- **Confidence Threshold Filter** — adjustable slider to filter bugs by confidence score
- **Inline Code Annotation** — bugs highlighted directly in the code with severity-colored markers
- **Severity & Category Charts** — interactive bar charts for bug distribution
- **Downloadable Reports** — CSV, HTML, JSON download buttons
- **Pipeline DAG View** — visual agent execution trace with timing and status
- **Real-time Progress Bar** — shows current pipeline stage during analysis

### Reports
- **CSV** — hackathon-compatible format with ID, bug_line, Explanation columns
- **HTML** — professional dark-themed report with stats dashboard, severity/category bar charts, and detailed bug table
- **JSON** — full structured data including agent traces, timing, and metadata

### MCP Server
- **FastMCP SSE Server** — runs on port 8003 with Server-Sent Events transport
- **LlamaIndex Vector Store** — pre-built index over CWE knowledge documents
- **BAAI/bge-base-en-v1.5 Embeddings** — auto-downloaded on first run (~420MB)
- **13 CWE Knowledge Documents** — covering buffer overflow, SQL injection, race conditions, memory leaks, use-after-free, format strings, command injection, and more
- **Rebuilable Index** — `build_index.py` script to rebuild the vector store from knowledge docs

### Utilities
- **YAML Configuration** — `settings.yaml` for pipeline settings, `prompts.yaml` for LLM prompt templates
- **Structured Logging** — console + file logging with timestamps and severity levels
- **Timer Context Manager** — precise `perf_counter` timing for all operations
- **Rate Limiter** — global thread-safe rate limiter with API retry delay extraction from 429 errors

---

## 📂 Project Structure

```
agentic-bug-hunter/
├── config/
│   ├── settings.yaml              # Pipeline & agent configuration
│   └── prompts.yaml               # LLM prompt templates (reasoning, severity, explanation)
├── server/                        # MCP Server (runs separately in its own terminal)
│   ├── mcp_server.py              # FastMCP SSE server entry point (port 8003)
│   ├── build_index.py             # Rebuild vector index from knowledge docs
│   ├── requirements.txt           # Server-specific dependencies (llama-index, torch, etc.)
│   ├── knowledge/                 # 13 CWE knowledge base documents (*.txt)
│   ├── embedding_model/           # BAAI/bge-base-en-v1.5 (auto-downloaded on first run)
│   └── storage/                   # Pre-built LlamaIndex vector store
├── src/
│   ├── app.py                     # Streamlit dashboard (6 tabs, custom CSS, real-time progress)
│   ├── main.py                    # CLI entry point with --demo, --benchmark, --no-cache flags
│   ├── agents/
│   │   ├── base_agent.py          # Abstract base agent with timing & trace event generation
│   │   ├── reasoning_agent.py     # Bug discovery via Gemini (adds line numbers to code)
│   │   ├── mcp_agent.py           # Documentation grounding via FastMCP async client
│   │   ├── severity_agent.py      # Batch severity classification (1 API call for all bugs)
│   │   ├── explanation_agent.py   # Batch explanation refinement (1 API call for all bugs)
│   │   └── orchestrator.py        # Multi-agent coordinator with cache integration
│   ├── cache/
│   │   └── manager.py             # SHA-256 content-addressed cache for demo mode
│   ├── models/
│   │   └── schemas.py             # Pydantic v2 models (BugReport, Severity, BugCategory, CWE mapping)
│   ├── reports/
│   │   └── generator.py           # Multi-format report generator (CSV, HTML, JSON)
│   ├── evaluation/
│   │   └── benchmark.py           # Ground truth evaluation (Precision, Recall, F1-Score)
│   └── utils/
│       ├── config.py              # YAML config loader + env variable management
│       ├── logger.py              # Structured logging (console + file)
│       └── helpers.py             # Timer, RateLimiter, code context extraction
├── cache/                         # Cached analysis results (SHA-256 hashed JSON files)
│   ├── index.json                 # Cache index with sample IDs and timestamps
│   └── *.json                     # Individual cached results (3 pre-cached samples)
├── data/
│   ├── samples.csv                # Input code samples (3 C programs with known bugs)
│   ├── ground_truth.json          # Ground truth annotations for benchmarking (23 bugs across 3 samples)
│   └── outputs/                   # Generated reports (CSV, HTML, JSON)
├── tests/
│   ├── test_schemas.py            # Pydantic model tests
│   └── test_utils.py              # Utility function tests
├── logs/                          # Application log files
├── requirements.txt               # Main app dependencies
├── .env.example                   # Environment variable template
└── .gitignore
```

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.10+**
- **Google Gemini API key** — get one at [Google AI Studio](https://aistudio.google.com/apikey)

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/atharvabhakre2005/EDI-6.git
cd agentic-bug-hunter
```

---

### Step 2 — Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env
```

Open `.env` in a text editor and add your Gemini API key:

```env
GENAI_API_KEY="your_google_gemini_api_key_here"
MCP_SERVER_URL=http://127.0.0.1:8003/sse
```

---

### Step 3 — Start the MCP Server (Terminal 1)

The MCP server provides documentation grounding via vector similarity search. It must be running before you start the Streamlit app (unless you use Demo Mode).

```bash
# Navigate to the server directory
cd server

# Create a virtual environment for the server
python -m venv venv

# Activate the virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.\venv\Scripts\activate.bat
# On macOS/Linux:
source venv/bin/activate

# Install server dependencies
pip install -r requirements.txt

# Start the MCP server (runs on port 8003)
python mcp_server.py
```

> **Note:** On first run, the embedding model (`BAAI/bge-base-en-v1.5`) will be auto-downloaded (~420MB). This only happens once.

You should see:

```
Embedding model found at: ./embedding_model
Starting MCP Server on port 8003...
```

**Leave this terminal running.** The server must stay active while using the dashboard.

---

### Step 4 — Run the Streamlit Dashboard (Terminal 2)

Open a **new terminal** window:

```bash
# Navigate to the project root
cd agentic-bug-hunter

# Create a virtual environment for the main app
python -m venv venv

# Activate the virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.\venv\Scripts\activate.bat
# On macOS/Linux:
source venv/bin/activate

# Install main app dependencies
pip install -r requirements.txt

# Run the Streamlit dashboard
streamlit run src/app.py
```

The dashboard will open automatically at **http://localhost:8501**.

---

### Step 5 — Using the Dashboard

1. Choose an **Analysis Mode** in the sidebar:
   - **Upload CSV** — upload a CSV file with `ID` and `Code` columns (use `data/samples.csv` for testing)
   - **Paste Code** — paste C/C++ code directly
2. Configure **Pipeline Settings** in the sidebar:
   - Toggle **MCP Grounding** — query documentation server
   - Toggle **Severity Classification** — classify bug severity
   - Toggle **Explanation Refinement** — refine bug descriptions
   - Toggle **Demo Mode (Cache Only)** — use cached results with zero API calls
3. Adjust **Min Confidence** slider to filter bugs by confidence score
4. Click **"Run Analysis"**
5. View results across the tabs:
   - **Analyze** — run new analyses
   - **Results** — detailed bug reports with severity/category filters, charts, and download buttons
   - **Code View** — inline annotated code with severity-colored bug highlighting
   - **Benchmark** — precision/recall/F1 evaluation against ground truth
   - **Pipeline** — visual agent DAG with execution trace and timing
   - **About** — system overview and CWE mapping reference

---

## 💻 CLI Usage (Alternative)

You can also run the analysis without the web UI:

```bash
# Basic analysis
python -m src.main --input data/samples.csv

# Demo mode (cached results, zero API calls)
python -m src.main --input data/samples.csv --demo

# With benchmark evaluation against ground truth
python -m src.main --input data/samples.csv --benchmark

# Disable caching (force fresh API calls every time)
python -m src.main --input data/samples.csv --no-cache

# Combined: fresh analysis + benchmark
python -m src.main --input data/samples.csv --no-cache --benchmark
```

---

## 🗂️ Running Summary (Two Terminals)

| Terminal | Directory | Command | Port | Purpose |
|----------|-----------|---------|------|---------|
| **Terminal 1** | `server/` | `python mcp_server.py` | `8003` | MCP documentation server |
| **Terminal 2** | project root | `streamlit run src/app.py` | `8501` | Web dashboard |

> **Tip:** If you don't need MCP documentation grounding, you can disable it in the sidebar toggle and run only the Streamlit app. **Demo Mode also works without the MCP server** — it replays cached results with zero API calls.

---

## 💾 Cache & Demo Mode

The cache system enables **zero-API-call replays** of previous analyses:

- **How it works:** When code is analyzed, the orchestrator hashes the source code with SHA-256 and stores the complete `AnalysisResult` as a JSON file in `cache/`
- **Cache lookup:** On subsequent runs with the same code, results are loaded from cache instead of calling Gemini
- **Demo Mode:** Enable via sidebar toggle or `--demo` CLI flag — forces cache-only mode, never calls APIs
- **Pre-cached samples:** 3 samples (S001, S002, S003) come pre-cached in the repo for immediate demo use
- **Cache index:** `cache/index.json` tracks all entries with sample IDs, timestamps, and code previews
- **Disable caching:** Use `--no-cache` CLI flag to force fresh API calls

---

## 🔧 Rebuilding the Vector Index (Optional)

If you add new knowledge documents to `server/knowledge/`, rebuild the vector index:

```bash
cd server
python build_index.py
```

This reads all `.txt` files from `server/knowledge/`, builds embeddings using BAAI/bge-base-en-v1.5, and persists the index to `server/storage/`. The old index is automatically backed up to `server/storage_backup/`.

---

## 📊 Output Formats

All reports are saved to `data/outputs/` with timestamps:

### CSV (Hackathon format)
| ID | bug_line | Explanation |
|----|----------|-------------|
| S001 | 8 | BUG: Returning pointer to local stack buffer — dangling pointer... |

### HTML Report
Professional dark-themed report with:
- Summary statistics cards (samples, bugs, avg/sample, processing time, critical/high counts)
- Severity & category bar charts
- Detailed bug table with severity badges, category labels, code snippets, and confidence scores

### JSON Report
Full structured data including:
- Analysis summary with aggregated statistics
- Per-sample results with all bug details
- Agent execution traces with timing
- Timestamps and metadata

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| LLM | Google Gemini 2.5 Flash (configurable) |
| MCP Server | FastMCP + LlamaIndex + BAAI/bge-base-en-v1.5 |
| Data Models | Pydantic v2 |
| Dashboard | Streamlit |
| Caching | SHA-256 content-addressed JSON file cache |
| Config | YAML + python-dotenv |
| Reports | CSV, HTML, JSON |
| Benchmarking | Custom evaluator (Precision, Recall, F1) |
| Testing | pytest |
| Logging | Python logging (console + file) |

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

Tests cover:
- **Pydantic models** — BugReport, RawBug, Severity, BugCategory, CWE auto-mapping
- **Utility functions** — CSV reading, code line extraction, code context, Timer, RateLimiter

---

## 📝 Configuration

### Pipeline Settings (`config/settings.yaml`)

```yaml
llm:
  model: "gemini-2.5-flash-lite"     # LLM model name
  temperature: 0.1                    # Lower = more deterministic
  max_tokens: 4096                    # Max output tokens
  retry_attempts: 2                   # Auto-retries on failure
  retry_delay: 15                     # Base delay between retries (seconds)

cache:
  enabled: true                       # Enable/disable result caching
  directory: "cache"                  # Cache storage directory

mcp:
  server_url: "http://127.0.0.1:8003/sse"
  timeout: 30
  similarity_top_k: 20               # Number of docs to retrieve

agents:
  reasoning:
    enabled: true
    max_bugs_per_sample: 15
  mcp_knowledge:
    enabled: true
    min_relevance_score: 0.3          # Filter low-quality docs
  severity:
    enabled: true
  explanation:
    enabled: true
    max_length: 200                   # Max chars per explanation

reports:
  output_dir: "data/outputs"
  formats: [csv, html, json]
  include_timestamp: true
```

### Prompt Templates (`config/prompts.yaml`)

Three fully customizable prompt templates:
- **`reasoning_agent`** — instructs Gemini to find bugs with specific category guidelines and output format
- **`severity_agent_batch`** — strict classification rules for CRITICAL/HIGH/MEDIUM/LOW with examples
- **`explanation_agent_batch`** — rewrite rules for professional, concise dataset-style explanations

---

## 🐞 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Make sure you activated the virtual environment and ran `pip install -r requirements.txt` |
| `from src.cache.manager import CacheManager` fails | Ensure you're running from the project root directory |
| MCP server connection refused | Ensure the MCP server is running in Terminal 1 on port 8003 |
| `GENAI_API_KEY` error | Check that `.env` exists and contains a valid API key |
| `429 Resource Exhausted` | The rate limiter handles this automatically — wait for the retry |
| Embedding model download fails | Check internet connection; model downloads from HuggingFace Hub |
| `streamlit: command not found` | Run `pip install streamlit` or ensure venv is activated |
| Port already in use | Kill the existing process or change the port in `config/settings.yaml` |
| Demo mode shows no results | Pre-cached samples only cover S001, S002, S003 from `data/samples.csv` |

---

## 👥 Team

Built for the Infineon Technologies Hackathon — Agentic Bug Hunter Track.

---

## 📄 License

MIT License
