from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class CoinImages:
    obverse_bytes: bytes
    reverse_bytes: bytes
    obverse_mime: str = "image/jpeg"
    reverse_mime: str = "image/jpeg"

@dataclass
class VisualEvidence:
    visible_obverse_fragments: list[str] = field(default_factory=list)
    visible_reverse_fragments: list[str] = field(default_factory=list)
    exergue_or_mintmark: str = ""
    observed_bust: str = ""
    observed_reverse_iconography: str = ""

@dataclass
class CoinHypothesis:
    authority: str = ""
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
    possible_references: list[str] = field(default_factory=list)
    confidence: float = 0.0
    uncertainties: list[str] = field(default_factory=list)
    identification_basis: list[str] = field(default_factory=list)

@dataclass
class IdentificationResult:
    evidence: VisualEvidence
    hypothesis: CoinHypothesis
    provider: str
    raw_text: str = ""
    latency_seconds: float | None = None
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class Candidate:
    type_id: str
    source: str = ""
    local_rank: int | None = None
    api_rank: int | None = None
    hybrid_rank: int | None = None
    hybrid_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class VerificationResult:
    status: str
    selected_type_id: str | None = None
    verdict: str = "ambiguous"
    confidence: float = 0.0
    matched_evidence: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    visible_obverse_fragments: list[str] = field(default_factory=list)
    visible_reverse_fragments: list[str] = field(default_factory=list)
    exergue_or_mintmark: str = ""
    notes: str = ""
    provider: str = ""
    raw_text: str = ""
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class SystemDecision:
    decision_status: str
    final_candidate_type_id: str | None
    provisional_candidate_type_id: str | None = None
    recommended_alternative_type_ids: list[str] = field(default_factory=list)
    support_reasons: list[str] = field(default_factory=list)
    caution_reasons: list[str] = field(default_factory=list)
    @property
    def is_verified(self) -> bool:
        return self.decision_status == "visually_supported_candidate" and bool(self.final_candidate_type_id)
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class EnrichmentResult:
    type_id: str
    payload: dict[str, Any]
    def to_dict(self) -> dict[str, Any]:
        return {"type_id": self.type_id, "payload": self.payload}

@dataclass
class PipelineResult:
    status: str
    identification: IdentificationResult
    candidates: list[Candidate]
    verification: VerificationResult
    decision: SystemDecision
    enrichment: EnrichmentResult | None = None
    errors: list[str] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "identification": self.identification.to_dict(),
            "candidates": [x.to_dict() for x in self.candidates],
            "verification": self.verification.to_dict(),
            "decision": self.decision.to_dict(),
            "enrichment": self.enrichment.to_dict() if self.enrichment else None,
            "errors": self.errors,
        }
