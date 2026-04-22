# schema.py
# ──────────────────────────────────────────────────────────────────
# Pydantic schemas for structured subagent outputs
# ──────────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class Finding(BaseModel):
    """A single research finding with full provenance."""
    claim: str = Field(..., description="The factual claim or finding")
    evidence_excerpt: str = Field(..., description="Verbatim or summarised excerpt supporting the claim")
    source_url_or_doc: str = Field(..., description="URL or document name where the evidence was found")
    publication_date: str = Field(..., description="Publication or retrieval date (ISO-8601 or human-readable)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    finding_type: Literal["established", "contested", "partial"] = Field(
        "established", description="Whether the finding is well-established, contested, or partial"
    )


class SubagentResult(BaseModel):
    """Structured output returned by each subagent."""
    agent_id: str
    agent_type: Literal["web_search", "document_analysis"]
    query: str
    findings: List[Finding] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    success: bool = True
    error: Optional[SubagentError] = None


class SubagentError(BaseModel):
    """Structured error context propagated from subagents to coordinator."""
    failure_type: Literal["timeout", "api_error", "parse_error", "no_results"]
    attempted_query: str
    partial_results: List[Finding] = Field(default_factory=list)
    error_message: str
    timestamp: str


class SynthesisReport(BaseModel):
    """Final synthesised research report produced by the synthesis subagent."""
    title: str
    summary: str
    established_findings: List[Finding] = Field(default_factory=list)
    contested_findings: List[Finding] = Field(default_factory=list)
    coverage_gaps: List[str] = Field(default_factory=list,
                                     description="Topics that could not be fully covered due to errors")
    sources_used: List[str] = Field(default_factory=list)
    generated_at: str


# Resolve forward reference
SubagentResult.model_rebuild()

