# test_pipeline.py — smoke tests for all Exercise 2 modules (no API calls)

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from config import MODEL, CONFIDENCE_LOW_THRESHOLD, BATCH_SIZE, SLA_MINUTES
from schema import EXTRACTION_TOOL, DocumentExtraction, ConfidenceScores
from few_shot import FEW_SHOT_EXAMPLES, build_few_shot_messages
from documents import SAMPLE_DOCUMENTS, generate_batch_corpus
from extractor import ExtractionResult, _classify_errors
from batch_processor import BatchDocument, _chunk_document
from human_review import route_for_review, KEY_CONFIDENCE_FIELDS
from pydantic import ValidationError

def ok(msg): print(f"  ✅ {msg}")
def fail(msg): print(f"  ❌ {msg}"); sys.exit(1)

print("=" * 60)
print("Exercise 2 — Pipeline Smoke Tests")
print("=" * 60)

# ── Config ─────────────────────────────────────────────────────────
ok(f"Config  MODEL={MODEL}  threshold={CONFIDENCE_LOW_THRESHOLD}  batch={BATCH_SIZE}  SLA={SLA_MINUTES}min")

# ── Schema ─────────────────────────────────────────────────────────
assert EXTRACTION_TOOL["name"] == "extract_document_metadata"
req = EXTRACTION_TOOL["input_schema"]["required"]
for f in ["title", "authors", "document_type", "confidence"]:
    assert f in req, f"{f} not in required"
ok(f"EXTRACTION_TOOL  required={req}")

# ── Pydantic: valid model ──────────────────────────────────────────
conf = ConfidenceScores(title=0.99, authors=0.8, publication_year=0.7,
                        document_type=0.9, abstract=0.5, keywords=0.5,
                        doi=0.99, journal_or_venue=0.3)
d = DocumentExtraction(
    title="Test Paper", authors=[], document_type="journal_article",
    document_type_detail=None, doi="10.1234/test.001", confidence=conf)
ok(f"Valid model accepted  doi={d.doi}")

# ── Pydantic: null fields accepted (not fabricated) ────────────────
d2 = DocumentExtraction(
    title="Memo", authors=[], document_type="other",
    document_type_detail="Internal memo", doi=None,
    publication_year=None, abstract=None,
    confidence=ConfidenceScores(title=0.8, authors=0.99, publication_year=0.1,
                                document_type=0.75, abstract=0.1, keywords=0.1,
                                doi=0.1, journal_or_venue=0.1))
assert d2.doi is None and d2.publication_year is None and d2.abstract is None
ok("Nullable fields accept None correctly")

# ── Pydantic: bad DOI rejected ─────────────────────────────────────
try:
    DocumentExtraction(
        title="X", authors=[], document_type="journal_article",
        document_type_detail=None, doi="INVALID",
        confidence=conf)
    fail("Bad DOI should have been rejected")
except ValidationError:
    ok("Bad DOI correctly rejected by validator")

# ── Pydantic: year out of range ────────────────────────────────────
try:
    DocumentExtraction(
        title="X", authors=[], document_type="journal_article",
        document_type_detail=None, publication_year=999,
        confidence=conf)
    fail("Year 999 should have been rejected")
except ValidationError:
    ok("Out-of-range year correctly rejected")

# ── Few-shot messages ──────────────────────────────────────────────
msgs = build_few_shot_messages()
# Each example = 3 messages (user, assistant tool_use, user tool_result)
assert len(msgs) == len(FEW_SHOT_EXAMPLES) * 3
ok(f"Few-shot messages: {len(msgs)} msgs for {len(FEW_SHOT_EXAMPLES)} examples")

# Check alternating roles
for i, m in enumerate(msgs):
    expected_role = ["user", "assistant", "user"][i % 3]
    assert m["role"] == expected_role, f"msg {i} wrong role"
ok("Few-shot message roles alternate correctly (user/assistant/user)")

# ── Documents corpus ───────────────────────────────────────────────
assert len(SAMPLE_DOCUMENTS) == 8
corpus = generate_batch_corpus(100)
assert len(corpus) == 100
ok(f"SAMPLE_DOCUMENTS={len(SAMPLE_DOCUMENTS)}, batch corpus=100")

# ── Batch chunking ─────────────────────────────────────────────────
big_doc = BatchDocument(doc_id="big", text="X" * 20000, chunk_index=0)
chunks = _chunk_document(big_doc)
assert len(chunks) == 2
assert chunks[0].chunk_index == 1 and chunks[1].chunk_index == 2
assert len(chunks[0].text) + len(chunks[1].text) == 20000
ok(f"Oversized doc chunked into 2 parts: {[len(c.text) for c in chunks]}")

# ── Human review routing logic (no API) ───────────────────────────
# Build synthetic ExtractionResult objects
low_conf_result = ExtractionResult(
    doc_id="low_conf_doc",
    extraction=DocumentExtraction(
        title="Low Confidence Paper", authors=[], document_type="preprint",
        document_type_detail=None,
        confidence=ConfidenceScores(title=0.5, authors=0.4, publication_year=0.3,
                                    document_type=0.6, abstract=0.3, keywords=0.2,
                                    doi=0.2, journal_or_venue=0.2)),
    raw={}, attempts=1, errors=[], resolvable_errors=[], non_resolvable_errors=[], success=True)

high_conf_result = ExtractionResult(
    doc_id="high_conf_doc",
    extraction=DocumentExtraction(
        title="High Confidence Paper", authors=[], document_type="journal_article",
        document_type_detail=None, doi="10.9999/hc.001",
        confidence=ConfidenceScores(title=0.99, authors=0.97, publication_year=0.95,
                                    document_type=0.99, abstract=0.95, keywords=0.90,
                                    doi=0.99, journal_or_venue=0.98)),
    raw={}, attempts=1, errors=[], resolvable_errors=[], non_resolvable_errors=[], success=True)

failed_result = ExtractionResult(
    doc_id="failed_doc", extraction=None, raw={},
    attempts=3, errors=["No tool_use block"], resolvable_errors=[], non_resolvable_errors=["No tool_use block"], success=False)

decisions, report = route_for_review([low_conf_result, high_conf_result, failed_result])

assert report.total_docs == 3
assert report.routed_to_human == 2   # low_conf + failed
assert report.auto_approved == 1     # high_conf
ok(f"Human review routing: total={report.total_docs}, human={report.routed_to_human}, approved={report.auto_approved}")

assert "preprint" in report.human_rate_by_type
assert report.human_rate_by_type["preprint"] == 1.0
ok(f"Preprint human rate = {report.human_rate_by_type['preprint']:.0%}")

print()
print("=" * 60)
print("ALL SMOKE TESTS PASSED ✅")
print("=" * 60)
print()
print("To run the full pipeline against the Claude API:")
print("  cd exercise-2 && python main.py")
print("  cd exercise-2 && python main.py --step 1")
print("  cd exercise-2 && python main.py --step 4 --batch")

