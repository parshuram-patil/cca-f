# schema.py
# ──────────────────────────────────────────────────────────────────
# Step 1: Define the extraction tool JSON schema and Pydantic model.
#
# Schema design patterns used:
#   • required vs optional fields
#   • enum with "other" + free-text detail (discriminated union pattern)
#   • nullable fields (anyOf: [type, null]) for absent information
#   • additionalProperties: false — strict mode
#
# Reference: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview
# Reference: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/tool-use-examples
# ──────────────────────────────────────────────────────────────────

from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
import re

# ── Pydantic Models ────────────────────────────────────────────────

class Author(BaseModel):
    name: str
    affiliation: Optional[str] = None          # nullable — may not be in document
    email: Optional[str] = None                # nullable

class ConfidenceScores(BaseModel):
    """
    Step 5: Field-level confidence scores (0.0 – 1.0) for human-review routing.
    Reference: Structured output with confidence scores pattern.
    """
    title:          float = Field(ge=0.0, le=1.0)
    authors:        float = Field(ge=0.0, le=1.0)
    publication_year: float = Field(ge=0.0, le=1.0)
    document_type:  float = Field(ge=0.0, le=1.0)
    abstract:       float = Field(ge=0.0, le=1.0)
    keywords:       float = Field(ge=0.0, le=1.0)
    doi:            float = Field(ge=0.0, le=1.0)
    journal_or_venue: float = Field(ge=0.0, le=1.0)

class DocumentExtraction(BaseModel):
    """
    Pydantic model mirroring the extraction_tool JSON schema.
    Used for validation after Claude returns tool_use results.
    """

    # ── Required fields ────────────────────────────────────────────
    title: str = Field(description="Full title of the document")

    authors: List[Author] = Field(
        description="List of authors. Use empty list [] if no authors found."
    )

    publication_year: Optional[int] = Field(
        default=None,
        description="4-digit publication year, or null if not found"
    )

    # ── Enum with 'other' + detail pattern ─────────────────────────
    document_type: Literal[
        "journal_article", "conference_paper", "book_chapter",
        "thesis", "technical_report", "preprint", "other"
    ] = Field(description="Type of the document")

    document_type_detail: Optional[str] = Field(
        default=None,
        description="Required when document_type='other'. Free-text description."
    )

    # ── Nullable optional fields ───────────────────────────────────
    abstract:        Optional[str]       = Field(default=None)
    keywords:        Optional[List[str]] = Field(default=None)
    doi:             Optional[str]       = Field(default=None)
    journal_or_venue: Optional[str]      = Field(default=None)
    volume:          Optional[str]       = Field(default=None)
    issue:           Optional[str]       = Field(default=None)
    pages:           Optional[str]       = Field(default=None)
    url:             Optional[str]       = Field(default=None)

    # ── Step 5: Confidence scores ──────────────────────────────────
    confidence: ConfidenceScores = Field(
        description="Field-level confidence scores between 0.0 and 1.0"
    )

    @field_validator("publication_year")
    @classmethod
    def year_range(cls, v):
        if v is not None and not (1000 <= v <= 2100):
            raise ValueError(f"publication_year {v} is out of valid range 1000–2100")
        return v

    @field_validator("doi")
    @classmethod
    def doi_format(cls, v):
        if v is not None and not re.match(r"^10\.\d{4,}", v):
            raise ValueError(f"DOI '{v}' does not match expected format 10.XXXX/...")
        return v

    @field_validator("document_type_detail")
    @classmethod
    def detail_required_for_other(cls, v, info):
        # Only validate if document_type is already set in values
        if hasattr(info, 'data') and info.data.get("document_type") == "other" and not v:
            raise ValueError("document_type_detail is required when document_type='other'")
        return v


# ── Tool definition for Claude (JSON Schema) ──────────────────────
# Reference: https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview#tool-input-schema

EXTRACTION_TOOL = {
    "name": "extract_document_metadata",
    "description": (
        "Extract structured bibliographic metadata from an academic or technical document. "
        "For fields that are NOT present in the source document, return null — do NOT fabricate values. "
        "Provide field-level confidence scores (0.0–1.0) reflecting certainty of each extracted value. "
        "When document_type is 'other', you MUST populate document_type_detail."
    ),
    "input_schema": {
        "type": "object",
        "properties": {

            # ── Required ───────────────────────────────────────────
            "title": {
                "type": "string",
                "description": "Full title of the document"
            },

            "authors": {
                "type": "array",
                "description": "List of authors. Use empty array if none found.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name":        {"type": "string"},
                        "affiliation": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        "email":       {"anyOf": [{"type": "string"}, {"type": "null"}]}
                    },
                    "required": ["name", "affiliation", "email"],
                    "additionalProperties": False
                }
            },

            "document_type": {
                "type": "string",
                "enum": [
                    "journal_article", "conference_paper", "book_chapter",
                    "thesis", "technical_report", "preprint", "other"
                ],
                "description": "Document classification. Use 'other' for unrecognised types."
            },

            "document_type_detail": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Required when document_type='other'. Describe the type."
            },

            # ── Nullable optional ──────────────────────────────────
            "publication_year": {
                "anyOf": [{"type": "integer", "minimum": 1000, "maximum": 2100}, {"type": "null"}],
                "description": "4-digit publication year, or null if absent"
            },
            "abstract": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Abstract text, or null if absent"
            },
            "keywords": {
                "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}],
                "description": "List of keywords, or null if absent"
            },
            "doi": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "DOI in format 10.XXXX/..., or null if absent"
            },
            "journal_or_venue": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Journal name or conference venue, or null if absent"
            },
            "volume":  {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "issue":   {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "pages":   {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "url":     {"anyOf": [{"type": "string"}, {"type": "null"}]},

            # ── Step 5: Field-level confidence scores ─────────────
            "confidence": {
                "type": "object",
                "description": "Confidence scores (0.0–1.0) for each major field",
                "properties": {
                    "title":            {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "authors":          {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "publication_year": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "document_type":    {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "abstract":         {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "keywords":         {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "doi":              {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "journal_or_venue": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                },
                "required": [
                    "title", "authors", "publication_year", "document_type",
                    "abstract", "keywords", "doi", "journal_or_venue"
                ],
                "additionalProperties": False
            }
        },

        "required": ["title", "authors", "document_type", "document_type_detail", "confidence"],
        "additionalProperties": False
    }
}

