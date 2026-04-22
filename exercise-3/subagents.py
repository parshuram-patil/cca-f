# subagents.py
# ──────────────────────────────────────────────────────────────────
# Individual subagent implementations:
#   - WebSearchSubagent   (simulates web search with conflicting data)
#   - DocumentAnalysisSubagent
#   - SynthesisSubagent
# ──────────────────────────────────────────────────────────────────

from __future__ import annotations
import json, time
from datetime import datetime, timezone

import anthropic

from config import MODEL, SUBAGENT_MAX_TOKENS
from schema import Finding, SubagentResult, SubagentError, SynthesisReport


# ── Shared Anthropic client ────────────────────────────────────────
client = anthropic.Anthropic()


# ── Simulated knowledge bases ──────────────────────────────────────
# Two authoritative-but-conflicting web sources (for Step 5)
WEB_DOCUMENTS = [
    {
        "url": "https://techreport.example.com/ai-adoption-2024",
        "title": "AI Adoption Report 2024 – TechReport",
        "date": "2024-03-15",
        "content": (
            "According to TechReport's 2024 survey of 5,000 enterprises, "
            "global AI adoption reached 72% of Fortune 500 companies by Q1 2024. "
            "Productivity gains averaged 34% across knowledge-worker roles. "
            "Investment in generative AI tools grew by $120 billion year-over-year."
        ),
    },
    {
        "url": "https://marketwatch-ai.example.com/enterprise-ai-stats",
        "title": "Enterprise AI Statistics – MarketWatch AI",
        "date": "2024-04-02",
        "content": (
            "MarketWatch AI's independent analysis of SEC filings and earnings calls "
            "found that only 41% of Fortune 500 companies reported active AI deployments "
            "as of Q1 2024. Productivity gains cited in investor reports ranged from 8–15%. "
            "Generative AI investment totalled $67 billion in 2023, a 210% increase YoY."
        ),
    },
]

INTERNAL_DOCUMENTS = [
    {
        "name": "internal_ai_strategy_memo_Q1_2024.pdf",
        "date": "2024-02-20",
        "content": (
            "Internal memo – Q1 AI Strategy Review:\n"
            "Our competitive analysis shows peers are investing heavily in LLM-based automation. "
            "ROI models suggest 18–25% efficiency gains are achievable within 18 months. "
            "Key risk: vendor lock-in with proprietary model APIs. "
            "Recommended action: adopt multi-vendor strategy with open-weight fallbacks."
        ),
    },
    {
        "name": "ai_risk_assessment_2024.pdf",
        "date": "2024-01-10",
        "content": (
            "AI Risk Assessment 2024:\n"
            "Primary risks identified: data privacy (high), model hallucination (medium-high), "
            "regulatory non-compliance (medium). Mitigation strategies include RLHF fine-tuning, "
            "retrieval-augmented generation, and human-in-the-loop review for high-stakes decisions."
        ),
    },
]


# ─────────────────────────────────────────────────────────────────
# Helper: call Claude and parse JSON output
# ─────────────────────────────────────────────────────────────────

def _call_claude(system_prompt: str, user_message: str) -> str:
    """Make a single Claude API call and return the text response."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=SUBAGENT_MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# ─────────────────────────────────────────────────────────────────
# Web Search Subagent
# ─────────────────────────────────────────────────────────────────

def run_web_search_subagent(
    agent_id: str,
    query: str,
    simulate_timeout: bool = False,
) -> SubagentResult:
    """
    Subagent that "searches the web" (uses simulated documents) and
    returns structured findings with source attribution.

    If simulate_timeout=True, raises a structured error after returning
    any partial results collected so far.
    """
    start = time.time()
    partial_findings: list[Finding] = []

    # --- simulate partial work before timeout ---
    system_prompt = """You are a web research analyst. Given a research query and web document excerpts,
extract structured findings. For EACH document, output a JSON object with keys:
  claim, evidence_excerpt, source_url_or_doc, publication_date, confidence (0-1), finding_type.

Return a JSON array of such objects. finding_type must be one of: established, contested, partial.
If two documents make conflicting claims about the same statistic, mark BOTH as "contested".
Output ONLY the JSON array, no other text."""

    documents_text = "\n\n".join(
        f"[Source {i+1}]\nURL: {d['url']}\nDate: {d['date']}\nContent: {d['content']}"
        for i, d in enumerate(WEB_DOCUMENTS)
    )
    user_message = f"Research query: {query}\n\nDocuments to analyse:\n{documents_text}"

    if simulate_timeout:
        # Simulate partial processing: only include first document finding
        partial_finding = Finding(
            claim="Global AI adoption among Fortune 500 companies was estimated at 72% by Q1 2024",
            evidence_excerpt=WEB_DOCUMENTS[0]["content"][:120],
            source_url_or_doc=WEB_DOCUMENTS[0]["url"],
            publication_date=WEB_DOCUMENTS[0]["date"],
            confidence=0.7,
            finding_type="contested",
        )
        partial_findings.append(partial_finding)

        error = SubagentError(
            failure_type="timeout",
            attempted_query=query,
            partial_results=partial_findings,
            error_message=f"Web search subagent timed out after {time.time() - start:.1f}s. "
                          f"Only 1 of 2 sources processed.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return SubagentResult(
            agent_id=agent_id,
            agent_type="web_search",
            query=query,
            findings=partial_findings,
            success=False,
            error=error,
        )

    # --- normal execution ---
    raw = _call_claude(system_prompt, user_message)
    # strip potential markdown fences
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    findings_data = json.loads(raw)
    findings = [Finding(**f) for f in findings_data]

    elapsed = time.time() - start
    return SubagentResult(
        agent_id=agent_id,
        agent_type="web_search",
        query=query,
        findings=findings,
        metadata={"elapsed_secs": round(elapsed, 2), "sources_consulted": len(WEB_DOCUMENTS)},
    )


# ─────────────────────────────────────────────────────────────────
# Document Analysis Subagent
# ─────────────────────────────────────────────────────────────────

def run_document_analysis_subagent(
    agent_id: str,
    query: str,
) -> SubagentResult:
    """
    Subagent that analyses internal documents and returns structured findings.
    Research findings are passed directly in the prompt (no automatic context inheritance).
    """
    start = time.time()

    system_prompt = """You are an internal document analyst. Given a research query and document excerpts,
extract structured findings. For EACH document, output a JSON object with keys:
  claim, evidence_excerpt, source_url_or_doc (use document name), publication_date,
  confidence (0-1), finding_type.

Return a JSON array of such objects. finding_type must be one of: established, contested, partial.
Output ONLY the JSON array, no other text."""

    documents_text = "\n\n".join(
        f"[Document {i+1}]\nName: {d['name']}\nDate: {d['date']}\nContent: {d['content']}"
        for i, d in enumerate(INTERNAL_DOCUMENTS)
    )
    user_message = f"Research query: {query}\n\nInternal documents to analyse:\n{documents_text}"

    raw = _call_claude(system_prompt, user_message)
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    findings_data = json.loads(raw)
    findings = [Finding(**f) for f in findings_data]

    elapsed = time.time() - start
    return SubagentResult(
        agent_id=agent_id,
        agent_type="document_analysis",
        query=query,
        findings=findings,
        metadata={"elapsed_secs": round(elapsed, 2), "documents_analysed": len(INTERNAL_DOCUMENTS)},
    )


# ─────────────────────────────────────────────────────────────────
# Synthesis Subagent
# ─────────────────────────────────────────────────────────────────

def run_synthesis_subagent(
    query: str,
    subagent_results: list[SubagentResult],
    coverage_gaps: list[str],
) -> SynthesisReport:
    """
    Synthesis subagent: receives ALL prior findings directly in its prompt,
    combines them while preserving source attribution, and distinguishes
    established vs contested findings.
    """
    # Serialise all findings explicitly into the prompt
    findings_payload = []
    for result in subagent_results:
        for f in result.findings:
            findings_payload.append({
                "agent": result.agent_id,
                "agent_type": result.agent_type,
                **f.model_dump(),
            })

    system_prompt = """You are a research synthesis specialist. You receive a list of findings from
multiple research agents and must produce a structured synthesis report.

Rules:
1. Preserve ALL source attributions (source_url_or_doc, publication_date) in your output.
2. If two findings make CONFLICTING claims about the same topic, include BOTH in
   'contested_findings' with their respective sources — never arbitrarily pick one.
3. Place uncontested, well-supported findings in 'established_findings'.
4. Output ONLY a JSON object with keys:
   title, summary, established_findings (array), contested_findings (array),
   coverage_gaps (array of strings), sources_used (array of strings), generated_at (ISO-8601).
5. Each item in established_findings / contested_findings must have:
   claim, evidence_excerpt, source_url_or_doc, publication_date, confidence, finding_type."""

    user_message = (
        f"Research topic: {query}\n\n"
        f"Coverage gaps (agents that failed): {json.dumps(coverage_gaps)}\n\n"
        f"All research findings (JSON):\n{json.dumps(findings_payload, indent=2)}"
    )

    raw = _call_claude(system_prompt, user_message)
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    report_data = json.loads(raw)

    # Ensure generated_at is present
    report_data.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    return SynthesisReport(**report_data)


