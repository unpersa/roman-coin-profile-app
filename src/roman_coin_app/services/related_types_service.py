from __future__ import annotations

from roman_coin_app.profile_schemas import (
    ProfileInference,
    RelatedTypeSuggestion,
)
from roman_coin_app.schemas import (
    CoinHypothesis,
    IdentificationResult,
    VisualEvidence,
)


class RelatedTypesService:
    def __init__(
        self,
        retrieval_service,
        max_related_types: int = 5,
    ):
        self.retrieval_service = retrieval_service
        self.max_related_types = int(
            max_related_types
        )

    @staticmethod
    def _as_v1_identification(
        inference: ProfileInference,
    ) -> IdentificationResult:
        return IdentificationResult(
            evidence=VisualEvidence(
                visible_obverse_fragments=list(
                    inference.evidence.visible_obverse_fragments
                ),
                visible_reverse_fragments=list(
                    inference.evidence.visible_reverse_fragments
                ),
                exergue_or_mintmark=
                    inference.evidence.exergue_or_mintmark,
                observed_bust=
                    inference.evidence.observed_bust,
                observed_reverse_iconography=
                    inference.evidence.observed_reverse_iconography,
            ),
            hypothesis=CoinHypothesis(
                authority=inference.authority,
                period=inference.period,
                date_min=inference.date_min,
                date_max=inference.date_max,
                denomination=inference.denomination,
                material=inference.material,
                mint=inference.mint,
                obverse_legend=inference.obverse_legend,
                obverse_description=
                    inference.obverse_description,
                reverse_legend=inference.reverse_legend,
                reverse_description=
                    inference.reverse_description,
                possible_references=list(
                    inference.possible_references
                ),
                confidence=float(
                    inference.overall_confidence
                    or 0.0
                ),
                uncertainties=list(
                    inference.uncertainties
                ),
                identification_basis=list(
                    inference.identification_basis
                ),
            ),
            provider=inference.provider,
            raw_text=inference.raw_text,
            latency_seconds=inference.latency_seconds,
        )

    def suggest(
        self,
        inference: ProfileInference,
    ) -> list[RelatedTypeSuggestion]:
        identification = (
            self._as_v1_identification(
                inference
            )
        )

        candidates = (
            self.retrieval_service
            .retrieve(identification)
        )

        return [
            RelatedTypeSuggestion(
                type_id=candidate.type_id,
                rank=candidate.hybrid_rank,
                source=candidate.source,
                local_rank=candidate.local_rank,
                api_rank=candidate.api_rank,
                score=candidate.hybrid_score,
                metadata=candidate.metadata or {},
            )
            for candidate in candidates[
                :self.max_related_types
            ]
        ]
