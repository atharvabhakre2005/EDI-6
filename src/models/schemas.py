"""Pydantic models for the Agentic Bug Hunter system."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BugCategory(str, Enum):
    """Categories of bugs that can be detected."""
    API_MISUSE = "API_MISUSE"
    LOGIC_ERROR = "LOGIC_ERROR"
    RESOURCE_MGMT = "RESOURCE_MGMT"
    CONCURRENCY = "CONCURRENCY"
    CONFIG_ERROR = "CONFIG_ERROR"
    ERROR_HANDLING = "ERROR_HANDLING"
    TYPE_ERROR = "TYPE_ERROR"
    SECURITY = "SECURITY"
    BUFFER_OVERFLOW = "BUFFER_OVERFLOW"
    UNKNOWN = "UNKNOWN"


# CWE (Common Weakness Enumeration) mapping for industry-standard classification
CWE_MAPPING: dict[str, dict[str, str]] = {
    "API_MISUSE": {"id": "CWE-252", "name": "Unchecked Return Value"},
    "LOGIC_ERROR": {"id": "CWE-682", "name": "Incorrect Calculation"},
    "RESOURCE_MGMT": {"id": "CWE-404", "name": "Improper Resource Shutdown or Release"},
    "CONCURRENCY": {"id": "CWE-362", "name": "Race Condition"},
    "CONFIG_ERROR": {"id": "CWE-16", "name": "Configuration"},
    "ERROR_HANDLING": {"id": "CWE-754", "name": "Improper Check for Unusual Conditions"},
    "TYPE_ERROR": {"id": "CWE-681", "name": "Incorrect Conversion between Numeric Types"},
    "SECURITY": {"id": "CWE-89", "name": "SQL Injection"},
    "BUFFER_OVERFLOW": {"id": "CWE-120", "name": "Buffer Copy without Checking Size"},
    "UNKNOWN": {"id": "CWE-398", "name": "Indicator of Poor Code Quality"},
}


class Severity(str, Enum):
    """Bug severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RawBug(BaseModel):
    """Raw bug hypothesis from the Reasoning Agent."""
    line: int = Field(..., ge=1, description="1-indexed line number")
    summary: str = Field(..., description="Short bug description")
    category: BugCategory = Field(default=BugCategory.UNKNOWN)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class DocumentChunk(BaseModel):
    """A retrieved documentation chunk from MCP."""
    text: str
    score: float = Field(default=0.0)


class BugReport(BaseModel):
    """Final structured bug report."""
    id: str = Field(..., description="Sample ID")
    bug_line: int = Field(..., ge=1, description="Line number of the bug")
    category: BugCategory = Field(default=BugCategory.UNKNOWN)
    severity: Severity = Field(default=Severity.MEDIUM)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    explanation: str = Field(..., description="Refined explanation")
    raw_summary: str = Field(default="", description="Original LLM summary")
    docs_context: str = Field(default="", description="MCP documentation used")
    code_line: str = Field(default="", description="The actual code at bug line")
    cwe_id: str = Field(default="", description="CWE identifier")
    cwe_name: str = Field(default="", description="CWE vulnerability name")

    def model_post_init(self, __context) -> None:
        """Auto-populate CWE fields from category if not set."""
        if not self.cwe_id and self.category:
            cwe = CWE_MAPPING.get(self.category.value, {})
            if cwe:
                object.__setattr__(self, 'cwe_id', cwe['id'])
                object.__setattr__(self, 'cwe_name', cwe['name'])


class AnalysisResult(BaseModel):
    """Complete analysis result for a single code sample."""
    sample_id: str
    code: str
    bugs: list[BugReport] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_trace: list[AgentEvent] = Field(default_factory=list)
    processing_time_ms: float = 0.0

    class Config:
        arbitrary_types_allowed = True


class AgentEvent(BaseModel):
    """Trace event from an agent execution step."""
    agent_name: str
    action: str
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: float = 0.0
    input_summary: str = ""
    output_summary: str = ""
    status: str = "success"  # success, error, skipped


# Rebuild AnalysisResult to resolve forward reference
AnalysisResult.model_rebuild()


class AnalysisSummary(BaseModel):
    """High-level summary statistics for a batch analysis."""
    total_samples: int = 0
    total_bugs: int = 0
    bugs_by_severity: dict[str, int] = Field(default_factory=dict)
    bugs_by_category: dict[str, int] = Field(default_factory=dict)
    avg_bugs_per_sample: float = 0.0
    processing_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
