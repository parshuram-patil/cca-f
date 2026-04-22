# documents.py
# ──────────────────────────────────────────────────────────────────
# Sample document corpus for testing all pipeline steps.
#
# Includes documents with:
#   • All fields present (journal article, APA style)
#   • Missing DOI / year / abstract (verify null, not fabrication)
#   • 'other' type requiring document_type_detail
#   • Varied formats (inline citations, bibliography, structured table, narrative)
#   • Oversized document (to trigger chunking in batch processor)
# ──────────────────────────────────────────────────────────────────

# ── Core test documents (Steps 1–3) ───────────────────────────────
SAMPLE_DOCUMENTS: list[dict] = [

    {
        "id": "doc_journal_full",
        "text": """
Nature Machine Intelligence
Title: Scaling Language Models: Methods, Analysis & Insights from Training Gopher
Authors: Jack W. Rae (DeepMind, jack@deepmind.com), Sebastian Borgeaud (DeepMind),
         Trevor Cai (DeepMind), Katie Millican (DeepMind), Jordan Hoffmann (DeepMind)
Year: 2022
Abstract: Language modelling provides a step-by-step objective where the model learns
to predict each successive token in a text. Here, we present an analysis of Transformer-based
language model performance across a wide range of model scales, from models with 44M to
280B parameters. We find consistent log-linear improvements for many downstream tasks.
Keywords: large language models, scaling laws, transformers, NLP
DOI: 10.48550/arXiv.2112.11446
Volume: 4, Issue: 3, Pages: 215-229
"""
    },

    {
        "id": "doc_biblio_no_abstract",
        "text": """
Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., &
Polosukhin, I. (2017). Attention is all you need. Advances in Neural Information Processing
Systems, 30, 5998–6008.
"""
    },

    {
        "id": "doc_missing_year_doi",
        "text": """
An Introduction to Quantum Computing for Software Engineers

By: Maria Santos and Raj Patel
Affiliation: Institute of Advanced Computing

This technical primer introduces quantum computing concepts relevant to software engineers,
covering qubits, superposition, entanglement, and quantum gates. The document was circulated
internally and has not been formally published.
"""
    },

    {
        "id": "doc_other_type",
        "text": """
MEMORANDUM

TO:   Engineering Leadership
FROM: AI Safety Team
RE:   Red-teaming Results for Production LLM System Q3 2024

Executive Summary: This memo summarises findings from a three-week red-teaming exercise
conducted on the production LLM inference system. Key vulnerabilities identified include
prompt injection vectors (severity: high) and context window manipulation (severity: medium).
Recommended mitigations are outlined in Section 4.

No external publication is planned for this document.
"""
    },

    {
        "id": "doc_table_format",
        "text": """
+-------------------+--------------------------------------------------------------+
| Title             | ImageNet Large Scale Visual Recognition Challenge            |
+-------------------+--------------------------------------------------------------+
| Authors           | Olga Russakovsky, Jia Deng, Hao Su, Jonathan Krause,         |
|                   | Sanjeev Satheesh, Sean Ma, Zhiheng Huang, Andrej Karpathy,   |
|                   | Aditya Khosla, Michael Bernstein, Alexander Berg, Li Fei-Fei |
+-------------------+--------------------------------------------------------------+
| Journal           | International Journal of Computer Vision                     |
| Volume / Issue    | 115 / 3                                                      |
| Pages             | 211–252                                                      |
| Year              | 2015                                                         |
| DOI               | 10.1007/s11263-015-0816-y                                    |
+-------------------+--------------------------------------------------------------+
"""
    },

    {
        "id": "doc_preprint_no_doi",
        "text": """
Constitutional AI: Harmlessness from AI Feedback

Yuntao Bai, Saurav Kadavath, Sandipan Kundu, Amanda Askell, Jackson Kernion, Andy Jones,
Anna Chen, Anna Goldie, Azalia Mirhoseini, Cameron McKinnon, Carol Chen, Catherine Olsson,
Christopher Olah, Danny Hernandez, Dawn Drain, Deep Ganguli, Dustin Li, Eli Tran-Johnson,
Ethan Perez, Jamie Kerr (Anthropic)

Abstract: As AI systems become more capable, we would like to enlist their help to supervise
other AIs. We experiment with methods for training a harmless AI assistant through self-
improvement, without any human labels identifying harmful outputs.

arXiv preprint, 2022. No DOI assigned at time of writing.
"""
    },

    {
        "id": "doc_thesis",
        "text": """
Reinforcement Learning from Human Feedback: Theory and Applications

A dissertation submitted to the Faculty of the Graduate School of
Stanford University in partial fulfilment of the requirements for the
degree of Doctor of Philosophy in Computer Science.

Author: Alexandra Kim
Advisor: Prof. Christopher Manning
Department: Computer Science
Year: 2023

Abstract: This thesis examines the theoretical foundations of Reinforcement Learning
from Human Feedback (RLHF) and presents three novel applications to language model
alignment. We provide convergence guarantees under mild assumptions and demonstrate
empirical effectiveness on two benchmark suites.
"""
    },

    {
        "id": "doc_no_title_no_authors",
        "text": """
This paper explores the relationship between batch size and generalisation in deep learning.
Experiments were conducted on CIFAR-10 and ImageNet. Results suggest that smaller batch
sizes implicitly regularise the model. No author information is provided in this copy.
"""
    },

]


# ── Batch corpus: 100 synthetic documents (Step 4) ────────────────

def generate_batch_corpus(n: int = 100) -> list[dict]:
    """
    Generate n synthetic document stubs for batch testing.
    Includes a few oversized documents to trigger chunking logic.
    """
    import random
    types = [
        "journal_article", "conference_paper", "book_chapter",
        "thesis", "technical_report", "preprint"
    ]
    venues = [
        "Nature", "Science", "NeurIPS", "ICML", "ICLR", "CVPR",
        "ACL", "EMNLP", "AAAI", "JMLR"
    ]
    topics = [
        "deep learning", "natural language processing", "computer vision",
        "reinforcement learning", "graph neural networks", "federated learning",
        "causal inference", "meta-learning", "self-supervised learning", "robotics"
    ]

    docs = []
    for i in range(n):
        doc_type  = random.choice(types)
        venue     = random.choice(venues)
        topic     = random.choice(topics)
        year      = random.randint(2015, 2026)
        author1   = f"Author{i}A Surname{i}"
        author2   = f"Author{i}B Coname{i}"

        # Make every 20th document oversized to trigger chunking
        padding = ""
        if i % 20 == 0:
            padding = "\n" + ("This is filler text to make the document oversized. " * 200)

        text = f"""
Title: Advances in {topic.title()} — Study {i+1}
Authors: {author1} (University {i}), {author2} (Institute {i})
Published in: {venue}, {year}
DOI: 10.9999/synthetic.{i:05d}
Abstract: This paper presents novel findings in {topic}. We propose method M{i}
and evaluate it on benchmark B{i}. Results show improvement over prior art.
Keywords: {topic}, machine learning, benchmark{padding}
""".strip()

        docs.append({"id": f"batch_doc_{i:03d}", "text": text})

    return docs

