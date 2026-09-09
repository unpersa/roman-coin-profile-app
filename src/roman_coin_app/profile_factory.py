from __future__ import annotations

from roman_coin_app.config import Settings
from roman_coin_app.profile_pipeline import RomanCoinProfilePipeline
from roman_coin_app.providers.attribute_enrichment_provider import (
    AttributeEnrichmentProvider,
)
from roman_coin_app.providers.gemini_profile_provider import (
    GeminiProfileProvider,
)
from roman_coin_app.providers.ocre_provider import OCREProvider
from roman_coin_app.services.attribute_enrichment_service import (
    AttributeEnrichmentService,
)
from roman_coin_app.services.frozen_local_retriever import (
    FrozenLocalRetriever,
)
from roman_coin_app.services.profile_builder_service import (
    ProfileBuilderService,
)
from roman_coin_app.services.related_types_service import (
    RelatedTypesService,
)
from roman_coin_app.services.retrieval_service import (
    RetrievalService,
)


def build_profile_pipeline(
    settings: Settings | None = None,
    local_retriever=None,
    enable_related_types: bool = True,
    max_related_types: int = 5,
    enrichment_service=None,
):
    settings = (
        settings
        or Settings.from_environment()
    )

    profile_provider = (
        GeminiProfileProvider(
            settings=settings
        )
    )

    profile_builder = (
        ProfileBuilderService()
    )

    related_types_service = None

    if enable_related_types:
        if local_retriever is None:
            local_retriever = (
                FrozenLocalRetriever(
                    settings=settings
                )
            )

        ocre = OCREProvider(
            settings=settings
        )

        retrieval_service = (
            RetrievalService(
                ocre_provider=ocre,
                local_retriever=
                    local_retriever,
                settings=settings,
            )
        )

        related_types_service = (
            RelatedTypesService(
                retrieval_service=
                    retrieval_service,
                max_related_types=
                    max_related_types,
            )
        )

    if enrichment_service is None:
        enrichment_provider = (
            AttributeEnrichmentProvider(
                settings=settings
            )
        )

        enrichment_service = (
            AttributeEnrichmentService(
                provider=
                    enrichment_provider,
                settings=settings,
            )
        )

    return RomanCoinProfilePipeline(
        profile_provider=
            profile_provider,
        profile_builder=
            profile_builder,
        related_types_service=
            related_types_service,
        enrichment_service=
            enrichment_service,
    )
