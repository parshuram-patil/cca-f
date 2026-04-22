# main.py
# ──────────────────────────────────────────────────────────────────
# Exercise 2: Structured Data Extraction Pipeline — Demo Runner
#
# Runs all 5 steps in sequence with clear console annotations:
#
#   Step 1: Single-document extraction with null-field verification
#   Step 2: Validation-retry loop demonstration
#   Step 3: Few-shot examples (structural variety)
#   Step 4: Batch processing (Message Batches API)
#   Step 5: Human review routing with accuracy analysis
# ──────────────────────────────────────────────────────────────────

import argparse

from documents import SAMPLE_DOCUMENTS, generate_batch_corpus
from extractor import extract_document, ExtractionResult
from batch_processor import process_batch, BatchDocument
from human_review import route_for_review, print_review_report


def banner(title: str) -> None:
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")


# ════════════════════════════════════════════════════════════════════
# STEP 1 + 3: Single-document extraction with few-shot prefix
# ════════════════════════════════════════════════════════════════════
def run_step1_and_3():
    banner("STEP 1 + 3 — Extraction with Few-Shot Examples & Null Verification")

    results: list[ExtractionResult] = []

    for doc in SAMPLE_DOCUMENTS:
        result = extract_document(doc["text"], doc_id=doc["id"])
        results.append(result)

        if result.success and result.extraction:
            ext = result.extraction
            print(f"\n  📋 {doc['id']}")
            print(f"     Title           : {ext.title}")
            print(f"     Doc type        : {ext.document_type}"
                  + (f" [{ext.document_type_detail}]" if ext.document_type == "other" else ""))
            print(f"     Authors         : {[a.name for a in ext.authors]}")
            print(f"     Year            : {ext.publication_year}  (null={ext.publication_year is None})")
            print(f"     DOI             : {ext.doi}  (null={ext.doi is None})")
            print(f"     Abstract null?  : {ext.abstract is None}")
            print(f"     Min confidence  : {min(ext.confidence.model_dump().values()):.2f}")
        else:
            print(f"\n  ❌ {doc['id']} — extraction failed after {result.attempts} attempt(s)")
            if result.non_resolvable_errors:
                print(f"     Non-resolvable: {result.non_resolvable_errors}")

    return results


# ════════════════════════════════════════════════════════════════════
# STEP 2: Demonstrate validation-retry loop with a malformed document
# ════════════════════════════════════════════════════════════════════
def run_step2_demo():
    banner("STEP 2 — Validation-Retry Loop Demo")

    # Deliberately ambiguous document that might produce a bad DOI
    tricky_doc = """
    Paper: Deep Residual Learning
    By: He et al., Microsoft Research, 2015
    Published at CVPR 2015. DOI info: see ResearchGate page at doi.org/UNKNOWN.
    Abstract: We present a residual learning framework to ease training of deep networks.
    """

    print("[DEMO] Processing a document with an ambiguous/invalid DOI field ...")
    result = extract_document(tricky_doc, doc_id="doc_tricky_doi")

    print(f"\n  Attempts made       : {result.attempts}")
    print(f"  Resolvable errors   : {result.resolvable_errors}")
    print(f"  Non-resolvable errors: {result.non_resolvable_errors}")
    print(f"  Final success       : {result.success}")

    if result.extraction:
        print(f"  DOI (after retry)   : {result.extraction.doi}")
    return result


# ════════════════════════════════════════════════════════════════════
# STEP 4: Batch processing (small subset for demo; full batch=100)
# ════════════════════════════════════════════════════════════════════
def run_step4_demo(use_full_batch: bool = False):
    banner("STEP 4 — Message Batches API Demo")

    if use_full_batch:
        print("[BATCH] Generating 100-document corpus ...")
        corpus = generate_batch_corpus(100)
    else:
        # Use just the 8 sample docs for a quick demo
        corpus = SAMPLE_DOCUMENTS
        print(f"[BATCH] Using {len(corpus)} sample documents (pass use_full_batch=True for 100)")

    batch_docs = [BatchDocument(doc_id=d["id"], text=d["text"]) for d in corpus]
    stats = process_batch(batch_docs)

    print(f"\n  Batch summary:")
    print(f"    Total submitted  : {stats.total_submitted}")
    print(f"    Succeeded        : {stats.total_succeeded}")
    print(f"    Failed           : {stats.total_failed}")
    print(f"    Retried          : {stats.total_retried}")
    print(f"    Wall time        : {stats.wall_time_secs:.1f}s")
    print(f"    SLA met          : {'✅ Yes' if stats.sla_met else '❌ No'}")

    return stats


# ════════════════════════════════════════════════════════════════════
# STEP 5: Human review routing on Step 1 results
# ════════════════════════════════════════════════════════════════════
def run_step5(extraction_results: list[ExtractionResult]):
    banner("STEP 5 — Human Review Routing & Accuracy Analysis")
    decisions, report = route_for_review(extraction_results)
    print_review_report(decisions, report)
    return decisions, report


# ════════════════════════════════════════════════════════════════════
# FEATURE / DOCUMENTATION TABLE
# ════════════════════════════════════════════════════════════════════
REFERENCE_TABLE = """
╔══════════════════════════════════╦═══════════════════════════════════════════════════════════════╦══════════════════════════════╗
║  Claude Feature Used             ║  Documentation Reference                                      ║  Implementation File         ║
╠══════════════════════════════════╬═══════════════════════════════════════════════════════════════╬══════════════════════════════╣
║  Tool Use (tool_use)             ║  https://docs.anthropic.com/en/docs/build-with-claude/        ║  schema.py, extractor.py     ║
║                                  ║  tool-use/overview                                            ║                              ║
╠══════════════════════════════════╬═══════════════════════════════════════════════════════════════╬══════════════════════════════╣
║  JSON Schema (input_schema)      ║  https://docs.anthropic.com/en/docs/build-with-claude/        ║  schema.py                   ║
║  required / nullable / enum      ║  tool-use/overview#tool-input-schema                          ║                              ║
╠══════════════════════════════════╬═══════════════════════════════════════════════════════════════╬══════════════════════════════╣
║  tool_choice: any                ║  https://docs.anthropic.com/en/docs/build-with-claude/        ║  extractor.py                ║
║  (force tool call)               ║  tool-use/overview#forcing-tool-use                           ║  batch_processor.py          ║
╠══════════════════════════════════╬═══════════════════════════════════════════════════════════════╬══════════════════════════════╣
║  Validation-Retry Loop           ║  https://docs.anthropic.com/en/docs/build-with-claude/        ║  extractor.py                ║
║  (tool_result with is_error)     ║  tool-use/tool-use-examples#validation-with-retries            ║  (_classify_errors)          ║
╠══════════════════════════════════╬═══════════════════════════════════════════════════════════════╬══════════════════════════════╣
║  Few-Shot Prompting with Tools   ║  https://docs.anthropic.com/en/docs/build-with-claude/        ║  few_shot.py                 ║
║  (prefilled assistant turns)     ║  prompt-engineering/use-examples                              ║  (build_few_shot_messages)   ║
╠══════════════════════════════════╬═══════════════════════════════════════════════════════════════╬══════════════════════════════╣
║  Message Batches API             ║  https://docs.anthropic.com/en/docs/build-with-claude/        ║  batch_processor.py          ║
║  (async bulk processing)         ║  message-batches                                              ║                              ║
╠══════════════════════════════════╬═══════════════════════════════════════════════════════════════╬══════════════════════════════╣
║  Batch custom_id                 ║  https://docs.anthropic.com/en/docs/build-with-claude/        ║  batch_processor.py          ║
║  (failure tracking + resubmit)   ║  message-batches#request-structure                            ║  (_build_batch_request)      ║
╠══════════════════════════════════╬═══════════════════════════════════════════════════════════════╬══════════════════════════════╣
║  Pydantic Structured Output      ║  https://docs.anthropic.com/en/docs/build-with-claude/        ║  schema.py                   ║
║  (DocumentExtraction model)      ║  tool-use/overview#extracting-structured-data                 ║  (DocumentExtraction)        ║
╠══════════════════════════════════╬═══════════════════════════════════════════════════════════════╬══════════════════════════════╣
║  Field-level Confidence Scores   ║  https://docs.anthropic.com/en/docs/build-with-claude/        ║  schema.py, human_review.py  ║
║  (human review routing)          ║  tool-use/overview#confidence-and-human-review                ║                              ║
╠══════════════════════════════════╬═══════════════════════════════════════════════════════════════╬══════════════════════════════╣
║  System Prompt (persona +        ║  https://docs.anthropic.com/en/docs/build-with-claude/        ║  extractor.py                ║
║  null-not-fabricate rule)        ║  prompt-engineering/system-prompts                            ║  batch_processor.py          ║
╚══════════════════════════════════╩═══════════════════════════════════════════════════════════════╩══════════════════════════════╝
"""


# ════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exercise 2: Structured Data Extraction Pipeline")
    parser.add_argument("--step",   type=int, default=0,
                        help="Run a specific step (1–5). 0=run all.")
    parser.add_argument("--batch",  action="store_true",
                        help="Step 4: use full 100-doc batch corpus (slow & costs tokens)")
    args = parser.parse_args()

    run_all = args.step == 0

    extraction_results: list[ExtractionResult] = []

    if run_all or args.step in (1, 3):
        extraction_results = run_step1_and_3()

    if run_all or args.step == 2:
        demo = run_step2_demo()
        extraction_results.append(demo)

    if run_all or args.step == 4:
        run_step4_demo(use_full_batch=args.batch)

    if run_all or args.step == 5:
        if not extraction_results:
            print("[WARN] No extraction results for Step 5 — running Step 1+3 first")
            extraction_results = run_step1_and_3()
        run_step5(extraction_results)

    print(REFERENCE_TABLE)

