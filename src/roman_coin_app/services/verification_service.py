from roman_coin_app.schemas import Candidate, CoinImages, SystemDecision, VerificationResult

class VerificationService:
    def __init__(self, verifier_provider):
        self.provider=verifier_provider

    def verify(self, images: CoinImages, candidates: list[Candidate]) -> VerificationResult:
        candidate_views=[{
            "type_id":c.type_id,
            "hybrid_rank":c.hybrid_rank,
            "local_rank":c.local_rank,
            "api_rank":c.api_rank,
            "metadata":(c.metadata or {}).get("jsonld",c.metadata or {}),
        } for c in candidates]
        return self.provider.verify(
            obverse_bytes=images.obverse_bytes,
            reverse_bytes=images.reverse_bytes,
            candidates=candidate_views,
            obverse_mime=images.obverse_mime,
            reverse_mime=images.reverse_mime,
        )

    def decide(self, verification: VerificationResult, candidates: list[Candidate]) -> SystemDecision:
        ids={c.type_id for c in candidates}
        selected=verification.selected_type_id
        if verification.status!="completed":
            return SystemDecision("not_evaluated",None,caution_reasons=["verification_not_completed"])
        if verification.verdict=="rejected":
            return SystemDecision("unverified",None,caution_reasons=["gemini_rejected_all_candidates"])
        if (verification.verdict=="supported" and selected and selected in ids
            and len(verification.matched_evidence)>=2 and len(verification.conflicts)<=1):
            return SystemDecision(
                "visually_supported_candidate",selected,selected,
                support_reasons=["independent_grounded_visual_verification","candidate_from_frozen_retrieval"]
            )
        return SystemDecision(
            "ambiguous_candidate",None,selected,
            recommended_alternative_type_ids=[c.type_id for c in candidates[:5]],
            caution_reasons=["insufficient_support_for_final_acceptance"]
        )
