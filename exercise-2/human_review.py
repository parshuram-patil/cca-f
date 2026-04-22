# human_review.py
# ──────────────────────────────────────────────────────────────────
# Step 5: Human review routing based on field-level confidence scores.
#
# Strategy:
#   1. Inspect confidence scores on each ExtractionResult
#   2. Route to human review if ANY key field is below CONFIDENCE_LOW_THRESHOLD
#   3. Log routed items to HUMAN_REVIEW_QUEUE (JSON file)
#   4. Generate accuracy analysis by document_type and field
#
# Reference: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview#confidence-scores
# ──────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any  # noqa: F401 (kept for downstream type hints)

from config import CONFIDENCE_LOW_THRESHOLD, CONFIDENCE_HIGH_THRESHOLD, HUMAN_REVIEW_QUEUE
from extractor import ExtractionResult


# ── Key fields analysed for confidence ───────────────────────────
KEY_CONFIDENCE_FIELDS = [
    "title", "authors", "publication_year",
    "document_type", "abstract", "keywords",
    "doi", "journal_or_venue"
]


@dataclass
class ReviewDecision:
    doc_id:           str
    needs_review:     bool
    low_conf_fields:  list[str]
    confidence_scores: dict[str, float]
    document_type:    str | None
    extraction:       dict


@dataclass
class AccuracyReport:
    total_docs:             int = 0
    auto_approved:          int = 0
    routed_to_human:        int = 0
    avg_confidence_by_field: dict[str, float] = field(default_factory=dict)
    low_conf_rate_by_field:  dict[str, float] = field(default_factory=dict)
    docs_by_type:            dict[str, int]   = field(default_factory=dict)
    human_rate_by_type:      dict[str, float] = field(default_factory=dict)


# ── Core routing function ──────────────────────────────────────────

def route_for_review(results: list[ExtractionResult]) -> tuple[list[ReviewDecision], AccuracyReport]:
    """
    Evaluate confidence scores for each extraction result and decide
    whether to route to human review.

    Routing rules:
      • If any KEY_CONFIDENCE_FIELDS score < CONFIDENCE_LOW_THRESHOLD  → human review
      • If all scores >= CONFIDENCE_HIGH_THRESHOLD                     → auto-approve
      • In between                                                     → auto-approve with flag

    Returns:
        decisions: list of ReviewDecision for every document
        report:    AccuracyReport with aggregated statistics
    """
    decisions: list[ReviewDecision] = []
    human_queue: list[dict] = []

    # Aggregation helpers
    conf_sum:       dict[str, float] = defaultdict(float)
    low_conf_count: dict[str, int]   = defaultdict(int)
    type_count:     dict[str, int]   = defaultdict(int)
    type_human:     dict[str, int]   = defaultdict(int)

    for res in results:
        if not res.success or res.extraction is None:
            # Failed extraction → always route to human
            decision = ReviewDecision(
                doc_id=res.doc_id,
                needs_review=True,
                low_conf_fields=["EXTRACTION_FAILED"],
                confidence_scores={},
                document_type=None,
                extraction=res.raw
            )
            decisions.append(decision)
            human_queue.append(_to_queue_entry(decision, res))
            continue

        extraction    = res.extraction
        conf          = extraction.confidence
        conf_dict     = conf.model_dump()
        doc_type      = extraction.document_type

        # Find low-confidence fields
        low_fields = [
            f for f in KEY_CONFIDENCE_FIELDS
            if conf_dict.get(f, 1.0) < CONFIDENCE_LOW_THRESHOLD
        ]

        needs_review = len(low_fields) > 0
        decision = ReviewDecision(
            doc_id=res.doc_id,
            needs_review=needs_review,
            low_conf_fields=low_fields,
            confidence_scores=conf_dict,
            document_type=doc_type,
            extraction=res.raw
        )
        decisions.append(decision)

        if needs_review:
            human_queue.append(_to_queue_entry(decision, res))
            type_human[doc_type] += 1

        # Aggregate for report
        type_count[doc_type] += 1
        for f in KEY_CONFIDENCE_FIELDS:
            score = conf_dict.get(f, 0.0)
            conf_sum[f] += score
            if score < CONFIDENCE_LOW_THRESHOLD:
                low_conf_count[f] += 1

    # ── Persist human review queue ─────────────────────────────────
    _write_queue(human_queue)

    # ── Build accuracy report ──────────────────────────────────────
    n = len(results)
    report = AccuracyReport(
        total_docs      = n,
        auto_approved   = sum(1 for d in decisions if not d.needs_review),
        routed_to_human = sum(1 for d in decisions if d.needs_review),
        avg_confidence_by_field = {
            f: round(conf_sum[f] / n, 3) if n else 0.0
            for f in KEY_CONFIDENCE_FIELDS
        },
        low_conf_rate_by_field = {
            f: round(low_conf_count[f] / n, 3) if n else 0.0
            for f in KEY_CONFIDENCE_FIELDS
        },
        docs_by_type = dict(type_count),
        human_rate_by_type = {
            t: round(type_human[t] / cnt, 3) if cnt else 0.0
            for t, cnt in type_count.items()
        }
    )

    return decisions, report


def print_review_report(decisions: list[ReviewDecision], report: AccuracyReport) -> None:
    """Pretty-print the human-review routing analysis."""
    print(f"\n{'═' * 60}")
    print("HUMAN REVIEW ROUTING ANALYSIS")
    print(f"{'═' * 60}")
    print(f"  Total documents  : {report.total_docs}")
    print(f"  Auto-approved    : {report.auto_approved}")
    print(f"  Routed to human  : {report.routed_to_human} "
          f"({100 * report.routed_to_human / max(report.total_docs, 1):.1f}%)")

    print(f"\n  Average confidence by field:")
    for f, avg in report.avg_confidence_by_field.items():
        low_rate = report.low_conf_rate_by_field.get(f, 0.0)
        bar = "█" * int(avg * 20)
        print(f"    {f:<22} {avg:.2f}  {bar:<20}  low-conf rate: {low_rate:.1%}")

    print(f"\n  Human review rate by document type:")
    for t, rate in report.human_rate_by_type.items():
        count = report.docs_by_type.get(t, 0)
        print(f"    {t:<22} {rate:.1%}  ({count} docs)")

    print(f"\n  Routed documents:")
    for d in decisions:
        if d.needs_review:
            print(f"    ⚠️  {d.doc_id:<30} low fields: {d.low_conf_fields}")

    print(f"\n  Human review queue written to: {HUMAN_REVIEW_QUEUE}")


# ── Helpers ────────────────────────────────────────────────────────

def _to_queue_entry(decision: ReviewDecision, res: ExtractionResult) -> dict:
    return {
        "doc_id":          decision.doc_id,
        "low_conf_fields": decision.low_conf_fields,
        "confidence":      decision.confidence_scores,
        "document_type":   decision.document_type,
        "extraction":      decision.extraction,
        "attempts":        res.attempts,
        "errors":          res.errors,
    }


def _write_queue(entries: list[dict]) -> None:
    """Append new review items to the human review queue JSON file."""
    existing: list[dict] = []
    if os.path.exists(HUMAN_REVIEW_QUEUE):
        with open(HUMAN_REVIEW_QUEUE) as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    existing.extend(entries)
    with open(HUMAN_REVIEW_QUEUE, "w") as f:
        json.dump(existing, f, indent=2)

