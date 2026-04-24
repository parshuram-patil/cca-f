# Simulated large document (normally this would be a real long document/system prompt)

import anthropic
from anthropic.types import TextBlockParam, MessageParam, CacheControlEphemeralParam
import time


from dotenv import load_dotenv
load_dotenv()

client = anthropic.Anthropic()


LARGE_DOCUMENT = """
You are an expert Python tutor. Your knowledge base includes:

TOPIC 1 - Data Structures:
Lists are ordered, mutable sequences. Tuples are ordered, immutable sequences.
Dictionaries are key-value stores with O(1) average lookup. Sets store unique elements.

TOPIC 2 - OOP Concepts:
Classes define blueprints for objects. Inheritance allows code reuse.
Encapsulation bundles data and methods. Polymorphism enables flexible interfaces.

TOPIC 3 - Error Handling:
Use try/except blocks to handle exceptions gracefully. Always catch specific
exception types rather than bare `except`. Use `finally` for cleanup code.
Custom exceptions should inherit from Exception or its subclasses.

TOPIC 4 - Decorators:
Decorators are functions that modify other functions using the @syntax.
Common built-ins: @property, @staticmethod, @classmethod. Use functools.wraps
to preserve metadata of the wrapped function.

TOPIC 5 - Generators & Iterators:
Generators use `yield` to lazily produce values, saving memory.
The iterator protocol requires __iter__ and __next__ methods.
Use `itertools` for advanced iteration patterns.
""" * 20  # Repeat to make it large enough to benefit from caching (needs ~1024+ tokens)


def make_request(question: str, turn: int) -> dict:
    """Send a request with the large system prompt cached."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=[
            TextBlockParam(
                type="text",
                text="You are a helpful technical assistant. Answer questions based on the documentation provided.",
            ),
            TextBlockParam(
                type="text",
                text=LARGE_DOCUMENT,
                cache_control=CacheControlEphemeralParam(type="ephemeral"),
            ),
        ],
        messages=[
            MessageParam(role="user", content=question),
        ],
    )

    usage = response.usage
    print(f"\n----------------- Turn {turn} ---------------------")
    print(f"Question: {question}")
    print(f"Answer:   {response.content[0].text[:200]}...")
    print(f"\n--------------------------------------------------")
    print(f"\nToken usage:")
    print(f"  Input tokens (not cached):  {usage.input_tokens}")
    print(f"  Cache WRITE tokens:         {usage.cache_creation_input_tokens}")
    print(f"  Cache READ tokens:          {usage.cache_read_input_tokens}")
    print(f"\n__________________________________________________")

    return {
        "input": usage.input_tokens,
        "cache_write": usage.cache_creation_input_tokens,
        "cache_read": usage.cache_read_input_tokens,
    }


def main():
    questions = [
        "What is the difference between a list and a tuple?",
        "Explain how decorators work in Python.",
        "How should I handle exceptions in Python?",
    ]

    print("=" * 55)
    print("  Claude Prompt Caching Demo")
    print("=" * 55)
    print(f"System prompt size: ~{len(LARGE_DOCUMENT.split())} words")
    print("\nFirst request writes to cache. Subsequent requests")
    print("read from cache at ~10x lower cost.\n")

    results = []
    for i, question in enumerate(questions, 1):
        stats = make_request(question, i)
        results.append(stats)
        if i < len(questions):
            time.sleep(1)  # Small delay between requests

    # Summary
    print("\n" + "=" * 55)
    print("  Summary")
    print("=" * 55)
    total_write = sum(r["cache_write"] for r in results)
    total_read = sum(r["cache_read"] for r in results)
    print(f"Total cache WRITE tokens: {total_write}  (charged at 1.25x)")
    print(f"Total cache READ tokens:  {total_read}   (charged at 0.1x)")
    if total_read > 0:
        savings_pct = round((1 - 0.1) * 100)
        print(f"\n✓ Cache reads saved ~{savings_pct}% on {total_read} tokens!")
    else:
        print("\n(Run again immediately to see cache hits on turns 2 & 3)")


if __name__ == "__main__":
    main()
