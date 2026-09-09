from __future__ import annotations

from roman_coin_app.profile_schemas import (
    CoinProfile,
    FieldAssessment,
    ProfileInference,
)


def confidence_label(
    confidence: float | None,
) -> str:
    if confidence is None:
        return "unknown"

    if confidence >= 0.80:
        return "high"

    if confidence >= 0.60:
        return "medium"

    return "low"


def _assessment(
    value,
    key: str,
    inference: ProfileInference,
    notes: list[str] | None = None,
):
    confidence = (
        inference
        .field_confidence
        .get(key)
    )

    return FieldAssessment(
        value=value,
        confidence=confidence,
        confidence_label=confidence_label(
            confidence
        ),
        source="multimodal_inference",
        notes=list(notes or []),
    )


class ProfileBuilderService:
    def build(
        self,
        inference: ProfileInference,
    ) -> CoinProfile:
        date_value = {
            "from": inference.date_min,
            "to": inference.date_max,
        }

        return CoinProfile(
            authority=_assessment(
                inference.authority,
                "authority",
                inference,
            ),
            dynasty=_assessment(
                inference.dynasty,
                "dynasty",
                inference,
            ),
            period=_assessment(
                inference.period,
                "period",
                inference,
            ),
            date_range=_assessment(
                date_value,
                "date_range",
                inference,
            ),
            denomination=_assessment(
                inference.denomination,
                "denomination",
                inference,
            ),
            material=_assessment(
                inference.material,
                "material",
                inference,
            ),
            mint=_assessment(
                inference.mint,
                "mint",
                inference,
            ),
            obverse_legend=_assessment(
                inference.obverse_legend,
                "obverse_legend",
                inference,
                notes=[
                    "Leyenda reconstruida: puede incluir inferencia numismática."
                ],
            ),
            reverse_legend=_assessment(
                inference.reverse_legend,
                "reverse_legend",
                inference,
                notes=[
                    "Leyenda reconstruida: puede incluir inferencia numismática."
                ],
            ),
            obverse_description=
                inference.obverse_description,
            reverse_description=
                inference.reverse_description,
            evidence=inference.evidence,
            historical_context=
                inference.historical_context,
            overall_confidence=
                inference.overall_confidence,
            overall_confidence_label=
                confidence_label(
                    inference.overall_confidence
                ),
            uncertainties=list(
                inference.uncertainties
            ),
            identification_basis=list(
                inference.identification_basis
            ),
        )
