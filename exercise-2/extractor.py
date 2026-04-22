# extractor.py
# ──────────────────────────────────────────────────────────────────
# Step 1 + 2 + 3: Single-document extraction with validation-retry loop.
#
# Flow:
#   1. Build messages with few-shot prefix (Step 3)
#   2. Call Claude with extraction tool (Step 1)
#   3. Parse tool_use block → Pydantic validation (Step 2)
#   4. On failure → send retry request with error context (Step 2)
#   5. Track resolvable vs non-resolvable errors (Step 2)
#
# Reference: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview
# Reference: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/tool-use-examples#validation-with-retries
# ──────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import os
import sys

import anthropic
from pydantic import ValidationError

from config import MODEL, MAX_TOKENS, MAX_RETRY_TOKENS, MAX_VALIDATION_RETRIES
from schema import EXTRACTION_TOOL, DocumentExtraction
from few_shot import build_few_shot_messages
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    sys.exit("❌  ANTHROPIC_API_KEY not set. Add it to your .env file.")

client = anthropic.Anthropic(api_key=api_key)

# ── System Prompt ──────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a precise bibliographic metadata extraction specialist.

Rules:
1. Extract ONLY information explicitly present in the source document.
2. Return null for any field that is absent — NEVER fabricate or infer values.
3. When document_type is 'other', you MUST fill document_type_detail.
4. Provide honest field-level confidence scores (0.0 = no confidence, 1.0 = certain).
5. Authors with no listed affiliation or email must have null for those sub-fields.
6. Always call the extract_document_metadata tool — do not respond with plain text."""


# ── Result dataclass ───────────────────────────────────────────────
class ExtractionResult:
    def __init__(
        self,
        doc_id: str,
        extraction: DocumentExtraction | None,
        raw: dict,
        attempts: int,
        errors: list[str],
        resolvable_errors: list[str],
        non_resolvable_errors: list[str],
        success: bool
    ):
        self.doc_id               = doc_id
        self.extraction           = extraction
        self.raw                  = raw
        self.attempts             = attempts
        self.errors               = errors
        self.resolvable_errors    = resolvable_errors
        self.non_resolvable_errors= non_resolvable_errors
        self.success              = success


def extract_document(document_text: str, doc_id: str = "doc_0") -> ExtractionResult:
    """
    Extract metadata from a single document with validation-retry loop.

    Step 3: Prepend few-shot examples to guide structural variety.
    Step 2: Retry on validation failure with error context.

    Args:
        document_text: Raw text of the document to process.
        doc_id:        Identifier for logging.

    Returns:
        ExtractionResult with extraction data and error tracking.
    """
    print(f"\n{'─' * 60}")
    print(f"[EXTRACTOR] 📄 Processing: {doc_id}")

    # ── Step 3: Build message history with few-shot prefix ─────────
    # Reference: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-examples
    messages = build_few_shot_messages()

    # Add the actual extraction request
    messages.append({
        "role": "user",
        "content": f"Extract metadata from the following document:\n\n{document_text.strip()}"
    })

    attempts           = 0
    errors             = []
    resolvable_errors  = []
    non_resolvable_errors = []
    last_raw: dict     = {}

    # ── Step 2: Validation-Retry Loop ─────────────────────────────
    # Reference: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/tool-use-examples#validation-with-retries
    while attempts <= MAX_VALIDATION_RETRIES:
        attempts += 1
        print(f"[EXTRACTOR]  Attempt {attempts}/{MAX_VALIDATION_RETRIES + 1}")

        # ── API Call ───────────────────────────────────────────────
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS if attempts == 1 else MAX_RETRY_TOKENS,
            system=SYSTEM_PROMPT,
            tools=[EXTRACTION_TOOL],
            tool_choice=anthropic.types.ToolChoiceAnyParam(type="any"),  # Force tool use
            messages=messages  # type: ignore[arg-type]
        )

        # ── Extract tool_use block ─────────────────────────────────
        tool_use_block = next(
            (b for b in response.content if b.type == "tool_use"),
            None
        )

        if tool_use_block is None:
            error_msg = "Claude did not call the extraction tool."
            errors.append(error_msg)
            non_resolvable_errors.append(error_msg)
            print(f"[EXTRACTOR] ❌ {error_msg}")
            break

        last_raw = tool_use_block.input
        tool_use_id = tool_use_block.id

        # ── Pydantic Validation ────────────────────────────────────
        try:
            extraction = DocumentExtraction(**last_raw)
            print(f"[EXTRACTOR] ✅ Validation passed on attempt {attempts}")
            return ExtractionResult(
                doc_id=doc_id,
                extraction=extraction,
                raw=last_raw,
                attempts=attempts,
                errors=errors,
                resolvable_errors=resolvable_errors,
                non_resolvable_errors=non_resolvable_errors,
                success=True
            )

        except ValidationError as ve:
            error_str = str(ve)
            errors.append(error_str)
            print(f"[EXTRACTOR] ⚠️  Validation error: {error_str[:200]}...")

            # ── Classify: resolvable vs non-resolvable ─────────────
            # Resolvable  → format mismatches (DOI format, year range, missing detail)
            # Non-resolvable → information genuinely absent from document
            resolvable, non_resolvable = _classify_errors(ve)
            resolvable_errors.extend(resolvable)
            non_resolvable_errors.extend(non_resolvable)

            if non_resolvable:
                print(f"[EXTRACTOR] 🚫 Non-resolvable error — stopping retries: {non_resolvable}")
                break

            if attempts > MAX_VALIDATION_RETRIES:
                print(f"[EXTRACTOR] ❌ Max retries reached")
                break

            # ── Append assistant + tool_result + retry request ─────
            # Reference: "Send the failed result back so Claude can self-correct"
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps({
                            "status": "validation_failed",
                            "errors": error_str
                        }),
                        "is_error": True
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Your previous extraction failed validation with these errors:\n\n"
                            f"{error_str}\n\n"
                            f"Please re-extract the metadata from the original document, "
                            f"fixing ONLY the fields with errors. "
                            f"If a value is genuinely absent, use null — do not guess."
                        )
                    }
                ]
            })

    # ── All retries exhausted ──────────────────────────────────────
    return ExtractionResult(
        doc_id=doc_id,
        extraction=None,
        raw=last_raw,
        attempts=attempts,
        errors=errors,
        resolvable_errors=resolvable_errors,
        non_resolvable_errors=non_resolvable_errors,
        success=False
    )


def _classify_errors(ve: ValidationError) -> tuple[list[str], list[str]]:
    """
    Classify Pydantic validation errors into:
      - resolvable   : format/constraint mismatches Claude can fix on retry
      - non_resolvable: information structurally absent from source document

    Heuristic keywords that indicate non-resolvable errors:
      'absent', 'not found', 'missing required field' when field is nullable
    """
    resolvable    = []
    non_resolvable = []

    for err in ve.errors():
        loc   = " → ".join(str(l) for l in err["loc"])
        msg   = err["msg"]
        etype = err["type"]

        # Non-resolvable: field fundamentally missing or cannot be inferred
        if etype in ("missing",) and err["loc"][-1] in ("title", "authors", "document_type"):
            non_resolvable.append(f"[{loc}] {msg}")
        else:
            # Format mismatches, range errors, conditional validators → resolvable
            resolvable.append(f"[{loc}] {msg}")

    return resolvable, non_resolvable

