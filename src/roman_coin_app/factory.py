from roman_coin_app.config import Settings
from roman_coin_app.pipeline import RomanCoinPipeline
from roman_coin_app.providers.gemini_provider import GeminiProvider
from roman_coin_app.providers.ocre_provider import OCREProvider
from roman_coin_app.providers.nomisma_provider import NomismaProvider
from roman_coin_app.services.identification_service import IdentificationService
from roman_coin_app.services.retrieval_service import RetrievalService
from roman_coin_app.services.verification_service import VerificationService
from roman_coin_app.services.enrichment_service import EnrichmentService
from roman_coin_app.services.frozen_local_retriever import FrozenLocalRetriever

def build_default_pipeline(local_retriever=None, settings: Settings | None = None):
    settings = settings or Settings.from_environment()

    if local_retriever is None:
        local_retriever = FrozenLocalRetriever(settings=settings)

    gemini = GeminiProvider(settings)
    ocre = OCREProvider(settings)
    nomisma = NomismaProvider(settings)

    return RomanCoinPipeline(
        IdentificationService(gemini),
        RetrievalService(ocre, local_retriever, settings),
        VerificationService(gemini),
        EnrichmentService(ocre, nomisma),
    )
