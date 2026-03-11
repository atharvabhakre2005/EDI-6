"""Tests for Pydantic schemas and models."""

import pytest
from datetime import datetime

from src.models.schemas import (
    BugCategory,
    Severity,
    RawBug,
    DocumentChunk,
    BugReport,
    AnalysisResult,
    AgentEvent,
    AnalysisSummary,
)


class TestBugCategory:
    def test_all_categories_exist(self):
        expected = ["API_MISUSE", "LOGIC_ERROR", "RESOURCE_MGMT", "CONCURRENCY",
                     "CONFIG_ERROR", "ERROR_HANDLING", "TYPE_ERROR", "UNKNOWN"]
        for cat in expected:
            assert BugCategory(cat) is not None

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError):
            BugCategory("INVALID")


class TestSeverity:
    def test_all_levels(self):
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            assert Severity(level) is not None


class TestRawBug:
    def test_valid_creation(self):
        bug = RawBug(line=10, summary="BUG: test", category=BugCategory.LOGIC_ERROR, confidence=0.9)
        assert bug.line == 10
        assert bug.confidence == 0.9

    def test_default_values(self):
        bug = RawBug(line=1, summary="test")
        assert bug.category == BugCategory.UNKNOWN
        assert bug.confidence == 0.5

    def test_line_must_be_positive(self):
        with pytest.raises(Exception):
            RawBug(line=0, summary="test")


class TestBugReport:
    def test_full_creation(self):
        report = BugReport(
            id="S1",
            bug_line=5,
            category=BugCategory.API_MISUSE,
            severity=Severity.HIGH,
            confidence=0.85,
            explanation="BUG: wrong API usage",
            raw_summary="wrong API",
            docs_context="doc text",
            code_line="foo(bar);",
        )
        assert report.id == "S1"
        assert report.severity == Severity.HIGH

    def test_minimal_creation(self):
        report = BugReport(id="S1", bug_line=1, explanation="test")
        assert report.category == BugCategory.UNKNOWN
        assert report.severity == Severity.MEDIUM


class TestAnalysisResult:
    def test_creation_with_bugs(self):
        bug = BugReport(id="S1", bug_line=1, explanation="test")
        result = AnalysisResult(sample_id="S1", code="int main() {}", bugs=[bug])
        assert len(result.bugs) == 1
        assert result.sample_id == "S1"

    def test_empty_bugs(self):
        result = AnalysisResult(sample_id="S1", code="")
        assert result.bugs == []


class TestAgentEvent:
    def test_creation(self):
        event = AgentEvent(
            agent_name="TestAgent",
            action="execute",
            duration_ms=150.5,
            status="success",
        )
        assert event.agent_name == "TestAgent"
        assert event.duration_ms == 150.5


class TestAnalysisSummary:
    def test_default_values(self):
        summary = AnalysisSummary()
        assert summary.total_samples == 0
        assert summary.total_bugs == 0
        assert summary.avg_bugs_per_sample == 0.0
