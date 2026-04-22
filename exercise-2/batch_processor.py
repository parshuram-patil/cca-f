# batch_processor.py
# ──────────────────────────────────────────────────────────────────
# Step 4: Batch processing strategy using the Message Batches API.
#
# Strategy:
#   1. Submit up to BATCH_SIZE documents in one Batch API request
#   2. Poll until complete; track per-document success/failure by custom_id
#   3. On failure → categorise cause (oversized? error?), resubmit:
#        • oversized  → chunk into halves and resubmit each chunk
#        • other      → resubmit with reduced max_tokens / simpler prompt
#   4. Calculate wall-clock time vs SLA constraint
#
# Reference: https://docs.anthropic.com/en/docs/build-with-claude/message-batches
# ──────────────────────────────────────────────────────────────────

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import anthropic
from dotenv import load_dotenv

from config import (
    MODEL, MAX_TOKENS, BATCH_SIZE, MAX_DOCUMENT_CHARS,
    BATCH_POLL_INTERVAL_SECS, SLA_MINUTES
)
from schema import EXTRACTION_TOOL
from few_shot import build_few_shot_messages

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    sys.exit("❌  ANTHROPIC_API_KEY not set.")

client = anthropic.Anthropic(api_key=api_key)

SYSTEM_PROMPT = (
    "You are a precise bibliographic metadata extraction specialist. "
    "Extract ONLY information present in the document. Return null for absent fields. "
    "Always call the extract_document_metadata tool."
)


# ── Data structures ────────────────────────────────────────────────

@dataclass
class BatchDocument:
    doc_id: str
    text: str
    chunk_index: int = 0       # non-zero for chunked re-submissions

@dataclass
class BatchStats:
    total_submitted: int = 0
    total_succeeded: int = 0
    total_failed:    int = 0
    total_retried:   int = 0
    wall_time_secs:  float = 0.0
    sla_met:         bool  = False
    results:         dict[str, Any] = field(default_factory=dict)
    failures:        dict[str, str] = field(default_factory=dict)


# ── Helpers ────────────────────────────────────────────────────────

def _build_batch_request(doc: BatchDocument, few_shot_prefix: list[dict]) -> dict:
    """
    Build a single MessageBatchRequestParam for one document.

    custom_id format: "<doc_id>__chunk<chunk_index>" so failures can be
    matched back to originals even after chunking.

    Reference: https://docs.anthropic.com/en/docs/build-with-claude/message-batches#request-structure
    """
    custom_id = f"{doc.doc_id}__chunk{doc.chunk_index}"
    messages  = few_shot_prefix + [
        {
            "role": "user",
            "content": f"Extract metadata from the following document:\n\n{doc.text.strip()}"
        }
    ]
    return {
        "custom_id": custom_id,
        "params": {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "system": SYSTEM_PROMPT,
            "tools": [EXTRACTION_TOOL],
            "tool_choice": {"type": "any"},
            "messages": messages
        }
    }


def _chunk_document(doc: BatchDocument) -> list[BatchDocument]:
    """
    Split an oversized document into two halves.
    Each half is submitted as a separate BatchDocument with chunk_index set.
    """
    mid = len(doc.text) // 2
    return [
        BatchDocument(doc_id=doc.doc_id, text=doc.text[:mid], chunk_index=1),
        BatchDocument(doc_id=doc.doc_id, text=doc.text[mid:], chunk_index=2),
    ]


def _poll_until_done(batch_id: str):  # -> MessageBatch
    """
    Poll Message Batches API until processing_status == 'ended'.
    Reference: https://docs.anthropic.com/en/docs/build-with-claude/message-batches#polling
    """
    while True:
        batch = client.beta.messages.batches.retrieve(batch_id)
        status = batch.processing_status
        print(f"[BATCH] Status: {status}  "
              f"(in_progress={batch.request_counts.processing}, "
              f"succeeded={batch.request_counts.succeeded}, "
              f"errored={batch.request_counts.errored})")
        if status == "ended":
            return batch
        time.sleep(BATCH_POLL_INTERVAL_SECS)


# ── Main batch processor ───────────────────────────────────────────

def process_batch(documents: list[BatchDocument]) -> BatchStats:
    """
    Submit documents in batches of BATCH_SIZE, handle failures,
    resubmit with chunking where needed, track SLA compliance.

    Steps:
      1. Validate and cap batch size
      2. Build requests with few-shot prefix
      3. Submit via Message Batches API
      4. Poll for completion
      5. Parse results — collect failures by custom_id
      6. Resubmit failures (chunked if oversized, else retry as-is)
      7. Calculate wall-clock time vs SLA

    Reference: https://docs.anthropic.com/en/docs/build-with-claude/message-batches
    """
    stats     = BatchStats()
    start_time = time.time()

    # Build few-shot prefix once (shared across all requests in batch)
    few_shot_prefix = build_few_shot_messages()

    # Work queue: list of documents still to be submitted
    pending = list(documents[:BATCH_SIZE])   # cap at batch size limit

    round_num = 0

    while pending:
        round_num += 1
        print(f"\n{'═' * 60}")
        print(f"[BATCH] Round {round_num}: Submitting {len(pending)} document(s)")

        # ── Step 3: Build request list ─────────────────────────────
        requests = [_build_batch_request(doc, few_shot_prefix) for doc in pending]
        stats.total_submitted += len(requests)

        # ── Step 4: Submit batch ───────────────────────────────────
        # Reference: https://docs.anthropic.com/en/docs/build-with-claude/message-batches#creating-a-batch
        batch = client.beta.messages.batches.create(requests=requests)  # type: ignore[arg-type]
        batch_id = batch.id
        print(f"[BATCH] Batch ID: {batch_id}")

        # ── Step 5: Poll ───────────────────────────────────────────
        completed_batch = _poll_until_done(batch_id)

        # ── Step 6: Collect results and failures ───────────────────
        failed_docs: list[BatchDocument] = []
        doc_map = {f"{d.doc_id}__chunk{d.chunk_index}": d for d in pending}

        for result in client.beta.messages.batches.results(batch_id):
            cid = result.custom_id
            doc = doc_map.get(cid)

            if result.result.type == "succeeded":
                # Extract tool_use block
                content = result.result.message.content
                tool_block = next((b for b in content if b.type == "tool_use"), None)
                if tool_block:
                    stats.results[cid] = tool_block.input
                    stats.total_succeeded += 1
                    print(f"[BATCH] ✅ {cid}")
                else:
                    stats.failures[cid] = "No tool_use block in response"
                    stats.total_failed += 1
                    if doc:
                        failed_docs.append(doc)

            elif result.result.type == "errored":
                err_msg = str(result.result.error)
                stats.failures[cid] = err_msg
                stats.total_failed += 1
                print(f"[BATCH] ❌ {cid}: {err_msg[:100]}")

                if doc:
                    # ── Resubmit strategy ──────────────────────────
                    if len(doc.text) > MAX_DOCUMENT_CHARS:
                        # Oversized → chunk into halves
                        print(f"[BATCH] ✂️  Oversized doc ({len(doc.text)} chars) → chunking")
                        failed_docs.extend(_chunk_document(doc))
                        stats.total_retried += 1
                    else:
                        # Other error → resubmit as-is (transient API error)
                        print(f"[BATCH] 🔄 Resubmitting {cid} as-is")
                        failed_docs.append(doc)
                        stats.total_retried += 1

        # Next round processes only failures
        pending = failed_docs
        if pending:
            print(f"[BATCH] 🔁 {len(pending)} document(s) queued for retry")

    # ── Step 7: Wall-clock time vs SLA ────────────────────────────
    stats.wall_time_secs = time.time() - start_time
    sla_secs = SLA_MINUTES * 60
    stats.sla_met = stats.wall_time_secs <= sla_secs

    print(f"\n[BATCH] {'✅ SLA MET' if stats.sla_met else '❌ SLA BREACHED'} — "
          f"{stats.wall_time_secs:.1f}s / {sla_secs}s limit")
    print(f"[BATCH] Submitted={stats.total_submitted}  "
          f"Succeeded={stats.total_succeeded}  "
          f"Failed={stats.total_failed}  "
          f"Retried={stats.total_retried}")

    return stats

