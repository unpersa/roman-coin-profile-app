from roman_coin_app.schemas import CoinImages, PipelineResult

class RomanCoinPipeline:
    def __init__(self,identification_service,retrieval_service,verification_service,enrichment_service):
        self.identification_service=identification_service
        self.retrieval_service=retrieval_service
        self.verification_service=verification_service
        self.enrichment_service=enrichment_service

    def run(self,images: CoinImages) -> PipelineResult:
        identification=self.identification_service.identify(images)
        candidates=self.retrieval_service.retrieve(identification)
        verification=self.verification_service.verify(images,candidates)
        decision=self.verification_service.decide(verification,candidates)
        enrichment=self.enrichment_service.enrich(decision.final_candidate_type_id) if decision.is_verified else None
        return PipelineResult(
            status="completed_verified" if decision.is_verified else "completed_unverified",
            identification=identification,candidates=candidates,
            verification=verification,decision=decision,enrichment=enrichment
        )
