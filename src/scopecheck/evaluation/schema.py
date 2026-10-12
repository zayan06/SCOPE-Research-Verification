"""Normalized benchmark record schema and validation."""

from __future__ import annotations

from collections.abc import Iterable
from pydantic import BaseModel, ConfigDict, Field, model_validator

from scopecheck.contracts import Relation


class BenchmarkPair(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    pair_id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    source_document_id: str = Field(min_length=1)
    source_location: str | None = None
    gold_label: str = Field(min_length=1)
    label_source: str = Field(min_length=1)
    annotation_status: str = Field(min_length=1)
    annotator: str | None = None
    notes: str | None = None
    split: str = Field(min_length=1)
    dataset_category: str = Field(min_length=1)
    original_label: str | None = None

    @model_validator(mode="after")
    def known_scoped_label(self) -> "BenchmarkPair":
        if self.label_source == "synthetic" and self.dataset_category != "development_fixture":
            raise ValueError("synthetic labels must belong to development_fixture category")
        if self.annotation_status == "human_reviewed" and not self.annotator:
            raise ValueError("human-reviewed records require annotator")
        return self


def validate_pairs(records: Iterable[BenchmarkPair]) -> list[BenchmarkPair]:
    pairs = list(records)
    ids = [row.pair_id for row in pairs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate pair_id values")
    valid = {relation.value for relation in Relation}
    for row in pairs:
        if row.gold_label not in valid:
            raise ValueError(f"invalid SCOPE gold_label {row.gold_label!r} for {row.pair_id}")
    return pairs
