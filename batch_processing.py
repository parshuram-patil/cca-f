import time
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from dotenv import load_dotenv
load_dotenv()

client = anthropic.Anthropic()

# ── 1. PREPARE REQUESTS ──────────────────────────────────────
documents = [
    {"id": "doc-1", "text": "Climate change is accelerating"},
    {"id": "doc-2", "text": "Renewable energy adoption"},
    {"id": "doc-3", "text": "Ocean plastic pollution"},
]

requests = [
    Request(
        custom_id=doc["id"],
        params=MessageCreateParamsNonStreaming(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": f"Summarize in 2 sentence:\n\n{doc['text']}"
            }]
        )
    )
    for doc in documents
]

# ── 2. SUBMIT ────────────────────────────────────────────────
batch = client.messages.batches.create(requests=requests)
print(f"Submitted batch: {batch.id}\n")

# ── 3. POLL UNTIL DONE ───────────────────────────────────────
while True:
    batch = client.messages.batches.retrieve(batch.id)

    if batch.processing_status == "ended":
        print("Batch complete!")
        break

    counts = batch.request_counts
    print(
        f"Still processing... "
        f"processing={counts.processing} "
        f"succeeded={counts.succeeded} "
        f"errored={counts.errored}\n"
    )
    time.sleep(30)

print(f"Done — succeeded={batch.request_counts.succeeded}, "
      f"errored={batch.request_counts.errored}")

# ── 4. RETRIEVE RESULTS ──────────────────────────────────────
results = {}
for result in client.messages.batches.results(batch.id):
    if result.result.type == "succeeded":
        results[result.custom_id] = result.result.message.content[0].text
    else:
        results[result.custom_id] = f"FAILED: {result.result.type}"

# ── 5. USE RESULTS ───────────────────────────────────────────
for doc in documents:
    print(f"\n{doc['id']}: {results.get(doc['id'], 'No result')}")
