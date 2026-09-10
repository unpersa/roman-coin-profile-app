from __future__ import annotations

from roman_coin_app.profile_schemas import (
    CoinProfileResult,
    ProfileEnrichment,
)
from roman_coin_app.schemas import CoinImages


class RomanCoinProfilePipeline:
    def __init__(
        self,
        profile_provider,
        profile_builder,
        related_types_service=None,
        enrichment_service=None,
    ):
        self.profile_provider = profile_provider
        self.profile_builder = profile_builder
        self.related_types_service = (
            related_types_service
        )
        self.enrichment_service = (
            enrichment_service
        )

    def run(
        self,
        images: CoinImages,
    ) -> CoinProfileResult:
        warnings = []
        errors = []

        inference = (
            self.profile_provider
            .analyze(
                obverse_bytes=
                    images.obverse_bytes,
                reverse_bytes=
                    images.reverse_bytes,
                obverse_mime=
                    images.obverse_mime,
                reverse_mime=
                    images.reverse_mime,
            )
        )

        profile = (
            self.profile_builder
            .build(inference)
        )

        related_types = []

        if self.related_types_service is not None:
            try:
                related_types = (
                    self.related_types_service
                    .suggest(inference)
                )
            except Exception as exc:
                warnings.append(
                    "related_types_unavailable: "
                    f"{type(exc).__name__}: "
                    f"{str(exc)[:240]}"
                )

        enrichment = ProfileEnrichment()

        if self.enrichment_service is not None:
            try:
                enrichment = (
                    self.enrichment_service
                    .enrich(profile)
                )
            except Exception as exc:
                warnings.append(
                    "attribute_enrichment_unavailable: "
                    f"{type(exc).__name__}: "
                    f"{str(exc)[:240]}"
                )

        status = "completed_profile"

        if (
            profile.overall_confidence_label
            == "low"
        ):
            status = (
                "completed_profile_low_confidence"
            )

        return CoinProfileResult(
            status=status,
            profile=profile,
            related_types=related_types,
            enrichment=enrichment,
            exact_ric_status="not_determined",
            exact_ric_type_id=None,
            warnings=warnings,
            errors=errors,
            model_used=inference.provider,
            fallback_used=inference.fallback_used,
        )
