from __future__ import annotations
import json, time
from roman_coin_app.config import Settings, get_secret
from roman_coin_app.schemas import CoinHypothesis, IdentificationResult, VisualEvidence, VerificationResult
from roman_coin_app.utils import extract_json_object, normalize_list, safe_int

INITIAL_SYSTEM_PROMPT = """
You are a multimodal assistant specialised in Roman numismatics.
You will ALWAYS receive two photographs of the SAME physical coin:
1. OBVERSE
2. REVERSE

STAGE A — DIRECT VISUAL OBSERVATION
Report only what is genuinely visible: legible letter fragments, exergue/mintmark/field marks,
bust features and reverse iconography. Do NOT autocomplete an inscription from memory.

STAGE B — NUMISMATIC HYPOTHESIS
Using the visual observations plus pretrained knowledge, propose authority, period/dates,
denomination, material, mint, reconstructed legends/descriptions and possible RIC-style references.

Rules:
- Do not browse the web.
- Do not use OCRE, Nomisma or external tools.
- Do not assume a corpus label.
- Do not invent unreadable letters.
- Separate visual observation from inference.
- Return ONLY JSON.
"""

INITIAL_USER_PROMPT = """
Return exactly:
{
  "visible_obverse_fragments": [],
  "visible_reverse_fragments": [],
  "exergue_or_mintmark": "",
  "observed_bust": "",
  "observed_reverse_iconography": "",
  "authority": "",
  "period": "",
  "date_min": null,
  "date_max": null,
  "denomination": "",
  "material": "",
  "mint": "",
  "obverse_legend": "",
  "obverse_description": "",
  "reverse_legend": "",
  "reverse_description": "",
  "possible_references": [],
  "confidence": 0.0,
  "uncertainties": [],
  "identification_basis": []
}
"""

class GeminiProvider:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_environment()
        api_key = get_secret("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("No está configurado GEMINI_API_KEY.")
        from google import genai
        self.client = genai.Client(api_key=api_key)

    @staticmethod
    def _part(data: bytes, mime_type: str):
        from google.genai import types
        return types.Part.from_bytes(data=data, mime_type=mime_type)

    def identify(self, obverse_bytes: bytes, reverse_bytes: bytes,
                 obverse_mime="image/jpeg", reverse_mime="image/jpeg") -> IdentificationResult:
        from google.genai import types
        started = time.perf_counter()
        response = self.client.models.generate_content(
            model=self.settings.gemini_model,
            contents=[
                INITIAL_SYSTEM_PROMPT,
                "OBVERSE:", self._part(obverse_bytes, obverse_mime),
                "REVERSE:", self._part(reverse_bytes, reverse_mime),
                INITIAL_USER_PROMPT,
            ],
            config=types.GenerateContentConfig(temperature=0),
        )
        raw = response.text or ""
        p = extract_json_object(raw)
        try:
            confidence = max(0.0, min(1.0, float(p.get("confidence", 0.0))))
        except Exception:
            confidence = 0.0
        evidence = VisualEvidence(
            visible_obverse_fragments=normalize_list(p.get("visible_obverse_fragments")),
            visible_reverse_fragments=normalize_list(p.get("visible_reverse_fragments")),
            exergue_or_mintmark=str(p.get("exergue_or_mintmark", "")).strip(),
            observed_bust=str(p.get("observed_bust", "")).strip(),
            observed_reverse_iconography=str(p.get("observed_reverse_iconography", "")).strip(),
        )
        hypothesis = CoinHypothesis(
            authority=str(p.get("authority", "")).strip(),
            period=str(p.get("period", "")).strip(),
            date_min=safe_int(p.get("date_min")),
            date_max=safe_int(p.get("date_max")),
            denomination=str(p.get("denomination", "")).strip(),
            material=str(p.get("material", "")).strip(),
            mint=str(p.get("mint", "")).strip(),
            obverse_legend=str(p.get("obverse_legend", "")).strip(),
            obverse_description=str(p.get("obverse_description", "")).strip(),
            reverse_legend=str(p.get("reverse_legend", "")).strip(),
            reverse_description=str(p.get("reverse_description", "")).strip(),
            possible_references=normalize_list(p.get("possible_references")),
            confidence=confidence,
            uncertainties=normalize_list(p.get("uncertainties")),
            identification_basis=normalize_list(p.get("identification_basis")),
        )
        return IdentificationResult(
            evidence=evidence,
            hypothesis=hypothesis,
            provider=f"Gemini:{self.settings.gemini_model}",
            raw_text=raw,
            latency_seconds=time.perf_counter()-started,
        )

    def verify(self, obverse_bytes: bytes, reverse_bytes: bytes, candidates: list[dict],
               obverse_mime="image/jpeg", reverse_mime="image/jpeg") -> VerificationResult:
        from google.genai import types
        ids = {str(x.get("type_id")) for x in candidates if x.get("type_id")}
        prompt = f"""
You are performing a SECOND, INDEPENDENT visual verification of a Roman coin.
The first image is the OBVERSE and the second is the REVERSE of the SAME physical coin.

Candidate OCRE types:
{json.dumps(candidates, ensure_ascii=False, indent=2, default=str)}

Return ONLY JSON:
{{
  "selected_type_id": null,
  "verdict": "supported|ambiguous|rejected",
  "confidence": 0.0,
  "matched_evidence": [],
  "conflicts": [],
  "visible_obverse_fragments": [],
  "visible_reverse_fragments": [],
  "exergue_or_mintmark": "",
  "notes": ""
}}

Rules:
- Candidates are NOT ordered by probability.
- Compare the photographs directly against every plausible candidate.
- selected_type_id must be exactly one supplied type_id or null.
- Do not autocomplete inscriptions from candidate metadata.
- Give special weight to reverse type and visible exergue/mintmark.
- A portrait resemblance alone is insufficient.
- If all candidates materially conflict, use rejected.
- If several remain plausible, use ambiguous.
- Use supported only with at least two independent visible matches and no major contradiction.
"""
        response = self.client.models.generate_content(
            model=self.settings.gemini_verifier_model,
            contents=[
                "OBVERSE:", self._part(obverse_bytes, obverse_mime),
                "REVERSE:", self._part(reverse_bytes, reverse_mime),
                prompt,
            ],
            config=types.GenerateContentConfig(temperature=0),
        )
        raw = response.text or ""
        p = extract_json_object(raw)
        selected = p.get("selected_type_id")
        if selected in {"", "null", "None"}:
            selected = None
        if selected is not None and str(selected) not in ids:
            selected = None
        try:
            confidence = max(0.0, min(1.0, float(p.get("confidence", 0.0))))
        except Exception:
            confidence = 0.0
        return VerificationResult(
            status="completed",
            selected_type_id=str(selected) if selected else None,
            verdict=str(p.get("verdict", "ambiguous")).strip().lower(),
            confidence=confidence,
            matched_evidence=normalize_list(p.get("matched_evidence")),
            conflicts=normalize_list(p.get("conflicts")),
            visible_obverse_fragments=normalize_list(p.get("visible_obverse_fragments")),
            visible_reverse_fragments=normalize_list(p.get("visible_reverse_fragments")),
            exergue_or_mintmark=str(p.get("exergue_or_mintmark", "")).strip(),
            notes=str(p.get("notes", "")).strip(),
            provider=f"Gemini:{self.settings.gemini_verifier_model}",
            raw_text=raw,
        )
