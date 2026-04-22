# main.py
# ──────────────────────────────────────────────────────────────────
# Entry point for Exercise 3: Multi-Agent Research Pipeline
# ──────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import sys
from pathlib import Path

from coordinator import CoordinatorAgent
from config import REPORT_OUTPUT_FILE


RESEARCH_TOPIC = (
    "Enterprise AI adoption rates and productivity impact in 2024: "
    "statistics, investment figures, risks, and strategic recommendations"
)


def print_report(report, latency_log: dict):
    """Pretty-print the synthesis report to stdout."""
    divider = "─" * 60

    print(f"\n{'='*60}")
    print("  FINAL RESEARCH REPORT")
    print(f"{'='*60}")
    print(f"Title : {report.title}")
    print(f"Generated : {report.generated_at}")
    print(f"\nSummary:\n{report.summary}")

    print(f"\n{divider}")
    print("ESTABLISHED FINDINGS")
    print(divider)
    for i, f in enumerate(report.established_findings, 1):
        print(f"\n[{i}] {f.claim}")
        print(f"    Evidence : {f.evidence_excerpt[:120]}...")
        print(f"    Source   : {f.source_url_or_doc}")
        print(f"    Date     : {f.publication_date}")
        print(f"    Confidence: {f.confidence:.0%}")

    print(f"\n{divider}")
    print("CONTESTED FINDINGS  (conflicting sources — both preserved)")
    print(divider)
    for i, f in enumerate(report.contested_findings, 1):
        print(f"\n[{i}] {f.claim}")
        print(f"    Evidence : {f.evidence_excerpt[:120]}...")
        print(f"    Source   : {f.source_url_or_doc}")
        print(f"    Date     : {f.publication_date}")
        print(f"    Confidence: {f.confidence:.0%}")

    if report.coverage_gaps:
        print(f"\n{divider}")
        print("COVERAGE GAPS  (due to subagent errors)")
        print(divider)
        for gap in report.coverage_gaps:
            print(f"  ⚠  {gap}")

    print(f"\n{divider}")
    print("SOURCES USED")
    print(divider)
    for src in report.sources_used:
        print(f"  • {src}")

    print(f"\n{divider}")
    print("LATENCY BENCHMARKS")
    print(divider)
    print(f"  Parallel execution  : {latency_log.get('parallel_secs', 'N/A')}s")
    print(f"  Sequential baseline : {latency_log.get('sequential_secs', 'N/A')}s")
    print(f"  Improvement         : {latency_log.get('improvement_secs', 'N/A')}s")
    print(f"  Speedup factor      : {latency_log.get('speedup_factor', 'N/A')}x")
    print()


def main():
    # Run the pipeline WITH simulated timeout (tests Step 4)
    print("Running pipeline WITH simulated timeout (error propagation test)...")
    agent = CoordinatorAgent(topic=RESEARCH_TOPIC, simulate_timeout=True)
    report = agent.run()

    # Save full report to JSON
    output = {
        "report": report.model_dump(),
        "latency": agent.latency_log,
        "subagent_results": [r.model_dump() for r in agent.subagent_results],
        "coverage_gaps": agent.coverage_gaps,
    }
    Path(REPORT_OUTPUT_FILE).write_text(json.dumps(output, indent=2))
    print(f"[Main] Full report saved to: {REPORT_OUTPUT_FILE}")

    print_report(report, agent.latency_log)

    return 0


if __name__ == "__main__":
    sys.exit(main())

