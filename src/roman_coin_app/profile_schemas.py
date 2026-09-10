from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class FieldAssessment:
    value: Any = ""
    confidence: float | None = None
    confidence_label: str = "unknown"
    source: str = "multimodal_inference"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProfileVisualEvidence:
    visible_obverse_fragments: list[str] = field(default_factory=list)
    visible_reverse_fragments: list[str] = field(default_factory=list)
    exergue_or_mintmark: str = ""
    observed_bust: str = ""
    observed_reverse_iconography: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HistoricalContextDraft:
    summary: str = ""
    authority_context: str = ""
    period_context: str = ""
    source: str = "multimodal_model_background_knowledge"
    externally_verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProfileInference:
    evidence: ProfileVisualEvidence

    authority: str = ""
    dynasty: str = ""
    period: str = ""
    date_min: int | None = None
    date_max: int | None = None
    denomination: str = ""
    material: str = ""
    mint: str = ""

    obverse_legend: str = ""
    obverse_description: str = ""
    reverse_legend: str = ""
    reverse_description: str = ""

    field_confidence: dict[str, float | None] = field(default_factory=dict)
    overall_confidence: float | None = None

    possible_references: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    identification_basis: list[str] = field(default_factory=list)

    historical_context: HistoricalContextDraft = field(
        default_factory=HistoricalContextDraft
    )

    provider: str = ""
    fallback_used: bool = False
    raw_text: str = ""
    latency_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoinProfile:
    authority: FieldAssessment
    dynasty: FieldAssessment
    period: FieldAssessment
    date_range: FieldAssessment
    denomination: FieldAssessment
    material: FieldAssessment
    mint: FieldAssessment

    obverse_legend: FieldAssessment
    reverse_legend: FieldAssessment

    obverse_description: str = ""
    reverse_description: str = ""

    evidence: ProfileVisualEvidence = field(
        default_factory=ProfileVisualEvidence
    )

    historical_context: HistoricalContextDraft = field(
        default_factory=HistoricalContextDraft
    )

    overall_confidence: float | None = None
    overall_confidence_label: str = "unknown"

    uncertainties: list[str] = field(default_factory=list)
    identification_basis: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RelatedTypeSuggestion:
    type_id: str
    rank: int | None = None
    source: str = ""
    local_rank: int | None = None
    api_rank: int | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    status: str = "related_reference_not_verified"
    disclaimer: str = (
        "Referencia tipológica compatible o relacionada; "
        "no constituye una identificación RIC definitiva."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EnrichmentSection:
    status: str = "not_available"
    summary: str = ""
    records: list[dict[str, Any]] = field(default_factory=list)
    source_scope: str = ""
    is_exhaustive: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProfileEnrichment:
    authority_context: EnrichmentSection = field(
        default_factory=EnrichmentSection
    )
    mint_context: EnrichmentSection = field(
        default_factory=EnrichmentSection
    )
    museum_presence: EnrichmentSection = field(
        default_factory=EnrichmentSection
    )
    archaeological_context: EnrichmentSection = field(
        default_factory=EnrichmentSection
    )
    metrology: EnrichmentSection = field(
        default_factory=EnrichmentSection
    )
    market_and_auctions: EnrichmentSection = field(
        default_factory=EnrichmentSection
    )
    sources: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CoinProfileResult:
    status: str
    profile: CoinProfile

    related_types: list[RelatedTypeSuggestion] = field(
        default_factory=list
    )

    enrichment: ProfileEnrichment = field(
        default_factory=ProfileEnrichment
    )

    exact_ric_status: str = "not_determined"
    exact_ric_type_id: str | None = None

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    model_used: str = ""
    fallback_used: bool = False

    schema_version: str = "roman_coin_profile_v2"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "model_used": self.model_used,
            "fallback_used": self.fallback_used,
            "profile": self.profile.to_dict(),
            "exact_ric_status": self.exact_ric_status,
            "exact_ric_type_id": self.exact_ric_type_id,
            "related_types": [
                x.to_dict()
                for x in self.related_types
            ],
            "enrichment": self.enrichment.to_dict(),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }
