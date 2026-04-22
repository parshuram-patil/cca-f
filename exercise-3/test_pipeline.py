# test_pipeline.py
# ──────────────────────────────────────────────────────────────────
# Test scenarios for Exercise 3: Multi-Agent Research Pipeline
#
# Covers:
#   Step 2 – Parallel vs Sequential latency
#   Step 4 – Error propagation with simulated timeout
#   Step 5 – Conflicting source data handling
# ──────────────────────────────────────────────────────────────────

from __future__ import annotations
import json
from coordinator import CoordinatorAgent
from schema import SubagentResult, SynthesisReport

TOPIC = (
    "Enterprise AI adoption rates and productivity impact in 2024"
)


def assert_(condition: bool, msg: str):
    status = "✓ PASS" if condition else "✗ FAIL"
    print(f"  {status}: {msg}")
    if not condition:
        raise AssertionError(msg)


# ─────────────────────────────────────────────────────────────────
# Test 1 – Parallel execution emits multiple tool calls + latency
# ─────────────────────────────────────────────────────────────────

def test_parallel_execution():
    print("\n[Test 1] Parallel execution & latency measurement")
    agent = CoordinatorAgent(topic=TOPIC, simulate_timeout=False)
    report = agent.run()

    ll = agent.latency_log
    assert_(ll["parallel_secs"] > 0, "Parallel elapsed > 0")
    assert_(ll["sequential_secs"] > 0, "Sequential elapsed > 0")
    assert_(ll["speedup_factor"] >= 1.0, "Parallel is at least as fast as sequential")
    print(f"  Speedup: {ll['speedup_factor']}x  "
          f"(parallel={ll['parallel_secs']}s vs sequential={ll['sequential_secs']}s)")


# ─────────────────────────────────────────────────────────────────
# Test 2 – Error propagation (simulated timeout)
# ─────────────────────────────────────────────────────────────────

def test_error_propagation():
    print("\n[Test 2] Error propagation – simulated timeout")
    agent = CoordinatorAgent(topic=TOPIC, simulate_timeout=True)
    report = agent.run()

    # At least one subagent should have failed
    failed = [r for r in agent.subagent_results if not r.success]
    assert_(len(failed) >= 1, "At least one subagent reported failure")

    for f in failed:
        assert_(f.error is not None, f"Error object present for {f.agent_id}")
        assert_(f.error.failure_type == "timeout", "Failure type is 'timeout'")
        assert_(len(f.error.partial_results) >= 1, "Partial results returned despite timeout")
        print(f"  Subagent '{f.agent_id}': {f.error.failure_type} – "
              f"{len(f.error.partial_results)} partial result(s)")

    # Coordinator must annotate coverage gaps
    assert_(len(agent.coverage_gaps) >= 1, "Coverage gaps populated by coordinator")
    assert_(len(report.coverage_gaps) >= 1, "Coverage gaps present in final report")
    print(f"  Coverage gaps: {report.coverage_gaps}")


# ─────────────────────────────────────────────────────────────────
# Test 3 – Conflicting sources produce contested findings
# ─────────────────────────────────────────────────────────────────

def test_conflicting_sources():
    print("\n[Test 3] Conflicting sources → both preserved with attribution")
    agent = CoordinatorAgent(topic=TOPIC, simulate_timeout=False)
    report = agent.run()

    assert_(len(report.contested_findings) >= 1,
            "At least one contested finding present (conflicting stats)")

    # Check that contested findings have different sources
    if len(report.contested_findings) >= 2:
        sources = {f.source_url_or_doc for f in report.contested_findings}
        assert_(len(sources) >= 2, "Contested findings reference at least 2 different sources")

    for f in report.contested_findings:
        assert_(f.source_url_or_doc, "Each contested finding has source attribution")
        assert_(f.publication_date, "Each contested finding has publication date")
        print(f"  Contested: '{f.claim[:60]}...'  → {f.source_url_or_doc}")

    # Verify synthesis did NOT arbitrarily drop either source
    web_sources = [f for f in report.contested_findings
                   if "techreport" in f.source_url_or_doc.lower()
                   or "marketwatch" in f.source_url_or_doc.lower()]
    assert_(len(web_sources) >= 1, "At least one contested finding from web sources retained")


# ─────────────────────────────────────────────────────────────────
# Test 4 – Structured output schema compliance
# ─────────────────────────────────────────────────────────────────

def test_structured_output():
    print("\n[Test 4] Structured output schema compliance")
    agent = CoordinatorAgent(topic=TOPIC, simulate_timeout=False)
    report = agent.run()

    all_findings = report.established_findings + report.contested_findings
    assert_(len(all_findings) >= 1, "Report contains at least one finding")

    for f in all_findings:
        assert_(bool(f.claim), "Finding has claim")
        assert_(bool(f.evidence_excerpt), "Finding has evidence_excerpt")
        assert_(bool(f.source_url_or_doc), "Finding has source_url_or_doc")
        assert_(bool(f.publication_date), "Finding has publication_date")
        assert_(0.0 <= f.confidence <= 1.0, "Confidence in [0,1]")
        assert_(f.finding_type in ("established", "contested", "partial"),
                "finding_type is valid enum value")
    print(f"  All {len(all_findings)} finding(s) pass schema checks.")


# ─────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    results = []
    tests = [
        test_error_propagation,       # Run timeout test first (fastest)
        test_conflicting_sources,
        test_structured_output,
        test_parallel_execution,      # Last (runs pipeline twice for latency)
    ]

    passed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  ASSERTION FAILED: {e}")
        except Exception as e:
            print(f"  ERROR in {test_fn.__name__}: {e}")

    print(f"\n{'='*40}")
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"{'='*40}\n")

