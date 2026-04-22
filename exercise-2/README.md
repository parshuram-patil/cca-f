# Exercise 2 — Structured Data Extraction Pipeline

## Overview
A production-quality pipeline for extracting structured bibliographic metadata
from academic and technical documents using Claude's tool-use, validation-retry,
few-shot prompting, Message Batches API, and human-review routing.

## File Structure
```
exercise-2/
├── config.py          # Central configuration (thresholds, model, SLA)
├── schema.py          # JSON Schema (EXTRACTION_TOOL) + Pydantic model
├── few_shot.py        # 4 few-shot examples across varied document formats
├── extractor.py       # Single-doc extraction + validation-retry loop
├── batch_processor.py # Message Batches API — 100 docs, failure handling
├── human_review.py    # Confidence-based routing + accuracy analysis
├── documents.py       # Sample corpus (8 labelled + 100 synthetic generator)
└── main.py            # Demo runner — all 5 steps
```

## Steps Implemented

| Step | Description | Key File(s) |
|------|-------------|-------------|
| 1 | Extraction tool with JSON schema (required/optional/nullable/enum+detail) | `schema.py` |
| 2 | Validation-retry loop; classifies resolvable vs non-resolvable errors | `extractor.py` |
| 3 | Few-shot examples for structural variety (prose, bibliography, table, narrative) | `few_shot.py` |
| 4 | Message Batches API — 100 docs, failure handling by custom_id, chunking oversized | `batch_processor.py` |
| 5 | Field-level confidence scores, human review routing, accuracy by type/field | `human_review.py` |

## Running

```bash
# Run all steps (uses sample 8-doc corpus for speed)
cd exercise-2
python main.py

# Run a specific step only
python main.py --step 1
python main.py --step 2
python main.py --step 4
python main.py --step 5

# Step 4 with full 100-document batch (costs more tokens)
python main.py --step 4 --batch
```

## Claude Features Used

| Feature | Documentation | File |
|---------|--------------|------|
| `tool_use` with JSON Schema | [Tool use overview](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview) | `schema.py` |
| `anyOf: [type, null]` nullable fields | [Tool input schema](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview#tool-input-schema) | `schema.py` |
| `tool_choice: {type: any}` | [Forcing tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview#forcing-tool-use) | `extractor.py`, `batch_processor.py` |
| Validation-retry with `is_error` | [Validation with retries](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/tool-use-examples) | `extractor.py` |
| Few-shot with prefilled tool turns | [Few-shot prompting](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-examples) | `few_shot.py` |
| Message Batches API | [Message Batches](https://docs.anthropic.com/en/docs/build-with-claude/message-batches) | `batch_processor.py` |
| Batch `custom_id` failure routing | [Batch request structure](https://docs.anthropic.com/en/docs/build-with-claude/message-batches#request-structure) | `batch_processor.py` |
| Pydantic structured output | [Structured data extraction](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview) | `schema.py` |
| Field-level confidence scores | [Human review routing](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview) | `schema.py`, `human_review.py` |
| System prompt rules | [System prompts](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts) | `extractor.py` |

