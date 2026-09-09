from __future__ import annotations
from difflib import SequenceMatcher
import re
import unicodedata
import numpy as np
import pandas as pd

RRF_K = 60
LOCAL_BRANCH_DEPTH = 250

def clean_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def normalize_text(value):
    value = clean_text(
        value
    )

    if not value:
        return ""

    value = unicodedata.normalize(
        "NFKD",
        value.lower()
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(
            char
        )
    )

    return re.sub(
        r"\s+",
        " ",
        re.sub(
            r"[^a-z0-9]+",
            " ",
            value
        )
    ).strip()


def normalize_legend(value):
    value = normalize_text(
        value
    )

    value = (
        value
        .replace(
            "u",
            "v"
        )
        .replace(
            "j",
            "i"
        )
    )

    return re.sub(
        r"[^a-z0-9]",
        "",
        value
    )


MATERIAL_ALIASES = {
    "ar": "silver",
    "argentum": "silver",
    "silver": "silver",
    "argento": "silver",
    "ae": "bronze/copper alloy",
    "bronze": "bronze/copper alloy",
    "bronze copper alloy": "bronze/copper alloy",
    "copper alloy": "bronze/copper alloy",
    "copper": "bronze/copper alloy",
    "av": "gold",
    "au": "gold",
    "aurum": "gold",
    "gold": "gold",
    "billon": "billon"
}


MINT_ALIASES = {
    "antiocheia syria": "antioch",
    "antioch": "antioch",
    "antiochia": "antioch",
    "thessalonike": "thessalonica",
    "thessalonica": "thessalonica",
    "constantinopolis": "constantinople",
    "constantinople": "constantinople",
    "roma": "rome",
    "rome": "rome",
    "treveri": "trier",
    "trier": "trier",
    "lugdunum": "lyon",
    "lyon": "lyon",
    "arelate": "arles",
    "arles": "arles",
    "siscia": "siscia",
    "aquileia": "aquileia",
    "heraclea": "heraclea",
    "nicomedia": "nicomedia",
    "cyzicus": "cyzicus",
    "alexandria": "alexandria"
}


AUTHORITY_ALIASES = {
    "constantine the great": "constantine i",
    "constantine i the great": "constantine i",
    "constantinus i": "constantine i",
    "valentinianus i": "valentinian i",
    "theodosius i": "theodosius i",
    "theodosius ii": "theodosius ii"
}


DENOMINATION_ALIASES = {
    "nummus": "nummus/follis",
    "follis": "nummus/follis",
    "nummus follis": "nummus/follis",
    "siliqua": "siliqua",
    "half siliqua": "half siliqua",
    "solidus": "solidus",
    "2 solidus": "2-solidus",
    "4 solidus": "4-solidus",
    "ae1": "ae1",
    "ae2": "ae2",
    "ae3": "ae3",
    "ae4": "ae4",
    "miliarensis": "miliarensis",
    "heavy miliarensis": "heavy miliarensis"
}


def canonical_from_aliases(value, aliases):
    normalized = normalize_text(
        value
    )

    if not normalized:
        return ""

    if normalized in aliases:
        return aliases[
            normalized
        ]

    return normalized


def canonical_material(value):
    return canonical_from_aliases(
        value,
        MATERIAL_ALIASES
    )


def canonical_mint(value):
    normalized = normalize_text(
        value
    )

    if not normalized:
        return ""

    if normalized in MINT_ALIASES:
        return MINT_ALIASES[
            normalized
        ]

    # Contención para variantes con región entre paréntesis.
    for alias, canonical in MINT_ALIASES.items():
        if (
            alias in normalized
            or normalized in alias
        ):
            return canonical

    return normalized


def canonical_authority(value):
    normalized = normalize_text(
        value
    )

    return AUTHORITY_ALIASES.get(
        normalized,
        normalized
    )


def canonical_denomination(value):
    normalized = normalize_text(
        value
    )

    return DENOMINATION_ALIASES.get(
        normalized,
        normalized
    )


def token_jaccard(left, right):
    left_tokens = set(
        normalize_text(
            left
        ).split()
    )

    right_tokens = set(
        normalize_text(
            right
        ).split()
    )

    if (
        not left_tokens
        or not right_tokens
    ):
        return 0.0

    return (
        len(
            left_tokens
            & right_tokens
        )
        / len(
            left_tokens
            | right_tokens
        )
    )


def text_similarity(left, right):
    left_norm = normalize_text(
        left
    )

    right_norm = normalize_text(
        right
    )

    if (
        not left_norm
        or not right_norm
    ):
        return np.nan

    if left_norm == right_norm:
        return 1.0

    # La contención ya no equivale a identidad.
    # Evita casos como "constantine i" dentro de "constantine iii".
    containment = (
        0.88
        if (
            left_norm in right_norm
            or right_norm in left_norm
        )
        else 0.0
    )

    sequence = SequenceMatcher(
        None,
        left_norm,
        right_norm
    ).ratio()

    jaccard = token_jaccard(
        left_norm,
        right_norm
    )

    return max(
        containment,
        0.60 * sequence
        + 0.40 * jaccard
    )


ROMAN_ORDINALS = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10
}


def split_authority_ordinal(value):
    canonical = canonical_authority(value)
    if not canonical:
        return "", None
    tokens = canonical.split()
    if not tokens:
        return "", None
    last = tokens[-1]
    ordinal = None
    if last in ROMAN_ORDINALS:
        ordinal = ROMAN_ORDINALS[last]
        tokens = tokens[:-1]
    elif last.isdigit():
        ordinal = int(last)
        tokens = tokens[:-1]
    return " ".join(tokens).strip(), ordinal


def authority_similarity(left, right):
    left_norm = canonical_authority(left)
    right_norm = canonical_authority(right)
    if not left_norm or not right_norm:
        return np.nan
    if left_norm == right_norm:
        return 1.0

    left_core, left_ordinal = split_authority_ordinal(left_norm)
    right_core, right_ordinal = split_authority_ordinal(right_norm)

    # Mismo nombre imperial pero ordinal distinto:
    # Constantine I NO es Constantine III.
    if left_core and right_core and left_core == right_core:
        if (
            left_ordinal is not None
            and right_ordinal is not None
            and left_ordinal != right_ordinal
        ):
            return 0.15
        if left_ordinal is None or right_ordinal is None:
            return 0.82

    sequence = SequenceMatcher(None, left_norm, right_norm).ratio()
    jaccard = token_jaccard(left_norm, right_norm)
    return 0.65 * sequence + 0.35 * jaccard


def canonical_similarity(
    left,
    right,
    canonicalizer
):
    left_norm = canonicalizer(
        left
    )

    right_norm = canonicalizer(
        right
    )

    if (
        not left_norm
        or not right_norm
    ):
        return np.nan

    if left_norm == right_norm:
        return 1.0

    return text_similarity(
        left_norm,
        right_norm
    )


def legend_similarity(left, right):
    left_norm = normalize_legend(
        left
    )

    right_norm = normalize_legend(
        right
    )

    if (
        not left_norm
        or not right_norm
    ):
        return np.nan

    if left_norm == right_norm:
        return 1.0

    if (
        left_norm in right_norm
        or right_norm in left_norm
    ):
        return 0.95

    return SequenceMatcher(
        None,
        left_norm,
        right_norm
    ).ratio()


def parse_year(value):
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    try:
        return int(
            float(
                value
            )
        )
    except Exception:
        match = re.search(
            r"-?\d{1,4}",
            str(value)
        )

        return (
            int(
                match.group()
            )
            if match
            else None
        )


def chronology_similarity(
    pred_min,
    pred_max,
    cand_min,
    cand_max
):
    pred_min = parse_year(
        pred_min
    )
    pred_max = parse_year(
        pred_max
    )
    cand_min = parse_year(
        cand_min
    )
    cand_max = parse_year(
        cand_max
    )

    if (
        pred_min is None
        and pred_max is None
    ):
        return np.nan

    if (
        cand_min is None
        and cand_max is None
    ):
        return np.nan

    if pred_min is None:
        pred_min = pred_max

    if pred_max is None:
        pred_max = pred_min

    if cand_min is None:
        cand_min = cand_max

    if cand_max is None:
        cand_max = cand_min

    if pred_min > pred_max:
        pred_min, pred_max = (
            pred_max,
            pred_min
        )

    if cand_min > cand_max:
        cand_min, cand_max = (
            cand_max,
            cand_min
        )

    overlap = (
        max(
            pred_min,
            cand_min
        )
        <= min(
            pred_max,
            cand_max
        )
    )

    if overlap:
        return 1.0

    distance = min(
        abs(
            pred_min
            - cand_max
        ),
        abs(
            cand_min
            - pred_max
        )
    )

    return max(
        0.0,
        1.0
        - distance
        / 120.0
    )

def observed_obverse_text(
    identification_payload
):
    direct = (
        identification_payload.get(
            "visible_obverse_fragments",
            []
        )
        or []
    )

    direct_text = " ".join(
        str(value)
        for value in direct
        if str(value).strip()
    ).strip()

    return (
        direct_text
        or clean_text(
            identification_payload.get(
                "obverse_legend"
            )
        )
    )


def observed_reverse_text(
    identification_payload
):
    direct = (
        identification_payload.get(
            "visible_reverse_fragments",
            []
        )
        or []
    )

    direct_text = " ".join(
        str(value)
        for value in direct
        if str(value).strip()
    ).strip()

    return (
        direct_text
        or clean_text(
            identification_payload.get(
                "reverse_legend"
            )
        )
    )


def observed_exergue_text(
    identification_payload
):
    return clean_text(
        identification_payload.get(
            "exergue_or_mintmark"
        )
    )


def candidate_reverse_search_text(
    candidate
):
    return " ".join([
        clean_text(
            candidate.get(
                "reverse_legend"
            )
        ),
        clean_text(
            candidate.get(
                "reverse_description"
            )
        )
    ]).strip()


def candidate_mintmark_values(
    candidate
):
    values = []

    for field in [
        "mintmark",
        "officina_mark"
    ]:
        raw_value = clean_text(
            candidate.get(
                field
            )
        )

        if not raw_value:
            continue

        for piece in re.split(
            r"\s*\|\s*",
            raw_value
        ):
            piece = piece.strip()

            if (
                piece
                and piece.lower()
                not in {
                    "nan",
                    "none",
                    "null"
                }
            ):
                values.append(
                    piece
                )

    return list(
        dict.fromkeys(
            values
        )
    )


def normalize_mintmark(
    value
):
    # Convierte, por ejemplo, "-/-//TRPS•" en "trps".
    return normalize_legend(
        value
    )


def infer_mint_from_exergue(
    value
):
    """
    Inferencia secundaria y deliberadamente conservadora.
    Solo reconoce patrones suficientemente distintivos.
    """
    normalized = normalize_mintmark(
        value
    )

    if not normalized:
        return ""

    patterns = [
        (
            "trier",
            [
                r"^tr",
                r"trp",
                r"trps",
                r"smtr"
            ]
        ),
        (
            "thessalonica",
            [
                r"^tes",
                r"^thes",
                r"smts"
            ]
        ),
        (
            "antioch",
            [
                r"^ant",
                r"smant"
            ]
        ),
        (
            "siscia",
            [
                r"^sis",
                r"sis"
            ]
        ),
        (
            "constantinople",
            [
                r"^con",
                r"conob",
                r"cons"
            ]
        )
    ]

    for mint_name, regexes in patterns:
        if any(
            re.search(
                pattern,
                normalized
            )
            for pattern in regexes
        ):
            return mint_name

    return ""


def exergue_similarity(
    observed_exergue,
    candidate
):
    """
    Devuelve (score, match_mode).

    match_mode:
      - explicit_ocre_mintmark
      - inferred_mint_from_exergue
      - unavailable
    """
    observed_exergue = clean_text(
        observed_exergue
    )

    if not observed_exergue:
        return np.nan, "unavailable"

    candidate_marks = candidate_mintmark_values(
        candidate
    )

    if candidate_marks:
        observed_norm = normalize_mintmark(
            observed_exergue
        )

        scores = []

        for candidate_mark in candidate_marks:
            candidate_norm = normalize_mintmark(
                candidate_mark
            )

            if not observed_norm or not candidate_norm:
                continue

            if observed_norm == candidate_norm:
                scores.append(1.0)

            elif (
                observed_norm in candidate_norm
                or candidate_norm in observed_norm
            ):
                scores.append(0.95)

            else:
                sequence = SequenceMatcher(
                    None,
                    observed_norm,
                    candidate_norm
                ).ratio()

                # Para mintmarks cortos una similitud de caracteres
                # moderada puede ser engañosa (p. ej. TRPS vs TES).
                # Se discretiza de forma conservadora.
                if sequence >= 0.85:
                    scores.append(0.85)
                elif sequence >= 0.70:
                    scores.append(0.55)
                else:
                    scores.append(0.0)

        if scores:
            return (
                float(max(scores)),
                "explicit_ocre_mintmark"
            )

    # Fallback: el exergo sugiere una ceca, pero se limita a 0.72.
    inferred_mint = infer_mint_from_exergue(
        observed_exergue
    )

    candidate_mint = canonical_mint(
        candidate.get("mint")
    )

    if inferred_mint and candidate_mint:
        mint_match = canonical_similarity(
            inferred_mint,
            candidate_mint,
            canonical_mint
        )

        if not pd.isna(mint_match):
            return (
                min(
                    0.72,
                    0.72 * float(mint_match)
                ),
                "inferred_mint_from_exergue"
            )

    return np.nan, "unavailable"

def joined_fragments(
    fragments
):
    return " ".join(
        [
            clean_text(
                value
            )
            for value in (
                fragments
                or []
            )
            if clean_text(
                value
            )
        ]
    ).strip()


def evidence_branch_scores(
    evidence,
    candidate
):
    obverse_text = joined_fragments(
        evidence.get(
            "obverse_fragments"
        )
    )

    reverse_text = joined_fragments(
        evidence.get(
            "reverse_fragments"
        )
    )

    exergue_score, (
        exergue_mode
    ) = exergue_similarity(
        evidence.get(
            "exergue"
        ),
        candidate
    )

    return {
        "authority": (
            authority_similarity(
                evidence.get(
                    "authority"
                ),
                candidate.get(
                    "authority"
                )
            )
        ),
        "mint": (
            canonical_similarity(
                evidence.get(
                    "mint"
                ),
                candidate.get(
                    "mint"
                ),
                canonical_mint
            )
        ),
        "denomination": (
            canonical_similarity(
                evidence.get(
                    "denomination"
                ),
                candidate.get(
                    "denomination"
                ),
                canonical_denomination
            )
        ),
        "material": (
            canonical_similarity(
                evidence.get(
                    "material"
                ),
                candidate.get(
                    "material"
                ),
                canonical_material
            )
        ),
        "obverse_legend": (
            legend_similarity(
                obverse_text,
                candidate.get(
                    "obverse_legend"
                )
            )
        ),
        "reverse_legend": (
            legend_similarity(
                reverse_text,
                candidate.get(
                    "reverse_legend"
                )
            )
        ),
        "exergue": (
            exergue_score
        ),
        "exergue_mode": (
            exergue_mode
        )
    }


BRANCH_WEIGHTS = {
    # Evidencia directamente visible.
    "reverse_legend": 1.40,
    "obverse_legend": 1.20,
    "exergue": 1.30,

    # Hipótesis semántica.
    "mint": 1.10,
    "authority": 1.00,
    "denomination": 0.65,
    "material": 0.45
}


def score_candidate_universe(
    evidence,
    candidate_universe_df
):
    rows = []

    for _, row in (
        candidate_universe_df
        .iterrows()
    ):
        candidate = row.to_dict()

        scores = evidence_branch_scores(
            evidence,
            candidate
        )

        rows.append({
            "type_id": (
                candidate[
                    "type_id"
                ]
            ),
            **scores
        })

    return pd.DataFrame(
        rows
    )


def weighted_soft_score(
    row
):
    numerator = 0.0
    denominator = 0.0

    for branch, weight in (
        BRANCH_WEIGHTS.items()
    ):
        value = row.get(
            branch
        )

        if (
            value is None
            or pd.isna(
                value
            )
        ):
            continue

        numerator += (
            weight
            * float(
                value
            )
        )

        denominator += weight

    return (
        numerator
        / denominator
        if denominator > 0
        else 0.0
    )


def ranking_from_soft_scores(
    scored_df
):
    ranked = (
        scored_df
        .copy()
    )

    ranked[
        "soft_score"
    ] = ranked.apply(
        weighted_soft_score,
        axis=1
    )

    return (
        ranked
        .sort_values(
            [
                "soft_score",
                "reverse_legend",
                "obverse_legend",
                "mint",
                "authority"
            ],
            ascending=[
                False,
                False,
                False,
                False,
                False
            ],
            na_position="last"
        )
        [
            "type_id"
        ]
        .astype(str)
        .tolist()
    )


def rrf_from_branch_scores(
    scored_df,
    depth=LOCAL_BRANCH_DEPTH
):
    fused = {}

    for branch, weight in (
        BRANCH_WEIGHTS.items()
    ):
        branch_df = (
            scored_df[
                [
                    "type_id",
                    branch
                ]
            ]
            .dropna(
                subset=[
                    branch
                ]
            )
            .copy()
        )

        if branch_df.empty:
            continue

        branch_df = (
            branch_df
            .sort_values(
                branch,
                ascending=False
            )
            .head(
                depth
            )
            .reset_index(
                drop=True
            )
        )

        # Señales totalmente nulas no aportan candidatos.
        branch_df = branch_df.loc[
            branch_df[
                branch
            ] > 0
        ]

        for rank, type_id in enumerate(
            branch_df[
                "type_id"
            ].astype(str),
            start=1
        ):
            fused[
                type_id
            ] = (
                fused.get(
                    type_id,
                    0.0
                )
                + weight
                / (
                    RRF_K
                    + rank
                )
            )

    return [
        type_id
        for type_id, _
        in sorted(
            fused.items(),
            key=lambda item:
            (
                -item[1],
                item[0]
            )
        )
    ]

from pathlib import Path
from roman_coin_app.config import Settings
from roman_coin_app.schemas import IdentificationResult

class FrozenLocalRetriever:
    """
    Port de local_branch_rrf congelado en NB21.

    No descubre catálogos ni ajusta pesos. Carga el snapshot fijado en NB24
    y aplica exactamente las funciones de scoring de NB21.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_environment()
        self.snapshot_path = (
            self.settings.processed_dir
            / "phase26_hybrid_retrieval"
            / "frozen_local_candidate_universe.csv"
        )
        if not self.snapshot_path.exists():
            raise FileNotFoundError(
                "No existe el snapshot local congelado: "
                + str(self.snapshot_path)
                + ". Ejecuta Notebook 24."
            )
        self.candidate_universe_df = pd.read_csv(
            self.snapshot_path,
            low_memory=False
        )

    @staticmethod
    def _to_nb21_evidence(identification: IdentificationResult) -> dict:
        e = identification.evidence
        h = identification.hypothesis
        return {
            "authority": str(h.authority or "").strip(),
            "denomination": str(h.denomination or "").strip(),
            "material": str(h.material or "").strip(),
            "mint": str(h.mint or "").strip(),
            "obverse_fragments": [
                str(value).strip()
                for value in (e.visible_obverse_fragments or [])
                if str(value).strip()
            ],
            "reverse_fragments": [
                str(value).strip()
                for value in (e.visible_reverse_fragments or [])
                if str(value).strip()
            ],
            "exergue": str(e.exergue_or_mintmark or "").strip(),
        }

    def retrieve(
        self,
        identification: IdentificationResult,
        depth: int = LOCAL_BRANCH_DEPTH
    ) -> list[str]:
        evidence = self._to_nb21_evidence(identification)
        scored_df = score_candidate_universe(
            evidence,
            self.candidate_universe_df
        )
        return rrf_from_branch_scores(
            scored_df,
            depth=depth
        )
