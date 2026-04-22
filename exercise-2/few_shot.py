# few_shot.py
# ──────────────────────────────────────────────────────────────────
# Step 3: Few-shot examples for the extraction prompt.
#
# Demonstrates extraction from varied source formats:
#   A) Inline citation style (nature-style prose)
#   B) Bibliography / reference list style
#   C) Structured table / metadata block style
#   D) Narrative description (no explicit metadata)
#   E) Document with 'other' type + absent fields (null verification)
#
# Reference: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-examples
# ──────────────────────────────────────────────────────────────────

FEW_SHOT_EXAMPLES = [

    # ── Example A: Inline-citation / prose format ──────────────────
    {
        "document": """
Attention Is All You Need

Ashish Vaswani¹, Noam Shazeer¹, Niki Parmar¹, Jakob Uszkoreit¹,
Llion Jones¹, Aidan N. Gomez², Łukasz Kaiser¹, Illia Polosukhin¹

¹Google Brain  ²University of Toronto

Abstract: The dominant sequence transduction models are based on complex recurrent or
convolutional neural networks that include an encoder and a decoder. The best performing
models also connect the encoder and decoder through an attention mechanism. We propose a new
simple network architecture, the Transformer, based solely on attention mechanisms,
dispensing with recurrence and convolutions entirely. Experiments on two machine translation
tasks show these models to be superior in quality while being more parallelizable and requiring
significantly less time to train.

Keywords: transformer, attention mechanism, sequence-to-sequence, neural machine translation

Proceedings of NeurIPS 2017, pp. 5998–6008
DOI: 10.5555/3295222.3295349
""",
        "extraction": {
            "title": "Attention Is All You Need",
            "authors": [
                {"name": "Ashish Vaswani",   "affiliation": "Google Brain",           "email": None},
                {"name": "Noam Shazeer",     "affiliation": "Google Brain",           "email": None},
                {"name": "Niki Parmar",      "affiliation": "Google Brain",           "email": None},
                {"name": "Jakob Uszkoreit",  "affiliation": "Google Brain",           "email": None},
                {"name": "Llion Jones",      "affiliation": "Google Brain",           "email": None},
                {"name": "Aidan N. Gomez",   "affiliation": "University of Toronto",  "email": None},
                {"name": "Łukasz Kaiser",    "affiliation": "Google Brain",           "email": None},
                {"name": "Illia Polosukhin", "affiliation": "Google Brain",           "email": None}
            ],
            "document_type": "conference_paper",
            "document_type_detail": None,
            "publication_year": 2017,
            "abstract": (
                "The dominant sequence transduction models are based on complex recurrent or "
                "convolutional neural networks that include an encoder and a decoder. The best performing "
                "models also connect the encoder and decoder through an attention mechanism. We propose a new "
                "simple network architecture, the Transformer, based solely on attention mechanisms, "
                "dispensing with recurrence and convolutions entirely."
            ),
            "keywords": ["transformer", "attention mechanism", "sequence-to-sequence", "neural machine translation"],
            "doi": "10.5555/3295222.3295349",
            "journal_or_venue": "NeurIPS 2017",
            "volume": None,
            "issue": None,
            "pages": "5998–6008",
            "url": None,
            "confidence": {
                "title": 0.99, "authors": 0.95, "publication_year": 0.99,
                "document_type": 0.97, "abstract": 0.99, "keywords": 0.99,
                "doi": 0.99, "journal_or_venue": 0.97
            }
        }
    },

    # ── Example B: Bibliography / reference list format ────────────
    {
        "document": """
LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436–444.
https://doi.org/10.1038/nature14539
""",
        "extraction": {
            "title": "Deep learning",
            "authors": [
                {"name": "Yann LeCun",    "affiliation": None, "email": None},
                {"name": "Yoshua Bengio", "affiliation": None, "email": None},
                {"name": "Geoffrey Hinton","affiliation": None, "email": None}
            ],
            "document_type": "journal_article",
            "document_type_detail": None,
            "publication_year": 2015,
            "abstract": None,
            "keywords": None,
            "doi": "10.1038/nature14539",
            "journal_or_venue": "Nature",
            "volume": "521",
            "issue": "7553",
            "pages": "436–444",
            "url": "https://doi.org/10.1038/nature14539",
            "confidence": {
                "title": 0.99, "authors": 0.97, "publication_year": 0.99,
                "document_type": 0.98, "abstract": 0.10, "keywords": 0.10,
                "doi": 0.99, "journal_or_venue": 0.99
            }
        }
    },

    # ── Example C: Structured metadata table format ────────────────
    {
        "document": """
| Field        | Value                                                         |
|--------------|---------------------------------------------------------------|
| Title        | BERT: Pre-training of Deep Bidirectional Transformers         |
| Authors      | Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova  |
| Org          | Google AI Language                                            |
| Year         | 2019                                                          |
| Venue        | NAACL-HLT 2019                                                |
| Pages        | 4171–4186                                                     |
| DOI          | 10.18653/v1/N19-1423                                          |
""",
        "extraction": {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "authors": [
                {"name": "Jacob Devlin",      "affiliation": "Google AI Language", "email": None},
                {"name": "Ming-Wei Chang",    "affiliation": "Google AI Language", "email": None},
                {"name": "Kenton Lee",        "affiliation": "Google AI Language", "email": None},
                {"name": "Kristina Toutanova","affiliation": "Google AI Language", "email": None}
            ],
            "document_type": "conference_paper",
            "document_type_detail": None,
            "publication_year": 2019,
            "abstract": None,
            "keywords": None,
            "doi": "10.18653/v1/N19-1423",
            "journal_or_venue": "NAACL-HLT 2019",
            "volume": None,
            "issue": None,
            "pages": "4171–4186",
            "url": None,
            "confidence": {
                "title": 0.99, "authors": 0.97, "publication_year": 0.99,
                "document_type": 0.95, "abstract": 0.10, "keywords": 0.10,
                "doi": 0.99, "journal_or_venue": 0.99
            }
        }
    },

    # ── Example D: Narrative with absent fields — null not fabricated
    {
        "document": """
In a recent internal memo circulated among the ML team, engineers described a new
data-augmentation technique called MixStyle that improves domain generalisation.
The memo has not been formally published and no DOI has been assigned yet.
No author names were listed on the document.
""",
        "extraction": {
            "title": "MixStyle: A Data-Augmentation Technique for Domain Generalisation",
            "authors": [],
            "document_type": "other",
            "document_type_detail": "Internal engineering memo",
            "publication_year": None,
            "abstract": (
                "A new data-augmentation technique called MixStyle that improves "
                "domain generalisation."
            ),
            "keywords": None,
            "doi": None,
            "journal_or_venue": None,
            "volume": None,
            "issue": None,
            "pages": None,
            "url": None,
            "confidence": {
                "title": 0.60, "authors": 0.99, "publication_year": 0.10,
                "document_type": 0.75, "abstract": 0.65, "keywords": 0.10,
                "doi": 0.10, "journal_or_venue": 0.10
            }
        }
    }
]


def build_few_shot_messages() -> list[dict]:
    """
    Converts FEW_SHOT_EXAMPLES into alternating user/assistant messages
    that prepend the main extraction request.

    Each example is:
      user    → "Extract metadata from: <document>"
      assistant → tool_use block (the correct extraction)

    Reference: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-examples#few-shot-prompting-with-tools
    """
    import json
    messages = []
    for i, ex in enumerate(FEW_SHOT_EXAMPLES):
        messages.append({
            "role": "user",
            "content": f"Extract metadata from the following document:\n\n{ex['document'].strip()}"
        })
        messages.append({
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": f"few_shot_tool_{i}",
                    "name": "extract_document_metadata",
                    "input": ex["extraction"]
                }
            ]
        })
        # Acknowledge the tool result so conversation is valid
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": f"few_shot_tool_{i}",
                    "content": json.dumps({"status": "validated"})
                }
            ]
        })
    return messages

