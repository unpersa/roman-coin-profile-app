from __future__ import annotations

from collections import Counter
import math

from roman_coin_app.config import Settings
from roman_coin_app.profile_schemas import (
    CoinProfile,
    EnrichmentSection,
    ProfileEnrichment,
)
from roman_coin_app.providers.attribute_enrichment_provider import (
    AttributeEnrichmentProvider,
)


class AttributeEnrichmentService:
    def __init__(
        self,
        provider: AttributeEnrichmentProvider | None = None,
        settings: Settings | None = None,
        max_specimens: int = 120,
        max_specimens_for_app: int = 30,
        max_geo_records: int = 50,
        max_ans_provenance_fetch: int = 8,
    ):
        self.settings = (
            settings
            or Settings.from_environment()
        )

        self.provider = (
            provider
            or AttributeEnrichmentProvider(
                settings=self.settings
            )
        )

        self.max_specimens = int(
            max_specimens
        )

        self.max_specimens_for_app = int(
            max_specimens_for_app
        )

        self.max_geo_records = int(
            max_geo_records
        )

        self.max_ans_provenance_fetch = int(
            max_ans_provenance_fetch
        )

    @staticmethod
    def _value(field):
        return str(
            getattr(
                field,
                "value",
                "",
            )
            or ""
        ).strip()

    @staticmethod
    def _confidence(field):
        value = getattr(
            field,
            "confidence",
            None,
        )

        try:
            return float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _collection_name(
        specimen: dict,
    ) -> str:
        value = (
            specimen.get(
                "collection"
            )
            or specimen.get(
                "collection_uri"
            )
            or specimen.get(
                "dataset_uri"
            )
            or ""
        )

        if value:
            return value

        uri = str(
            specimen.get(
                "object_uri",
                ""
            )
        )

        if "://" in uri:
            return uri.split(
                "/"
            )[2]

        return (
            "Unknown collection"
        )

    @classmethod
    def collection_summary(
        cls,
        specimens,
    ):
        grouped = {}

        for specimen in (
            specimens
            or []
        ):
            name = cls._collection_name(
                specimen
            )

            row = grouped.setdefault(
                name,
                {
                    "collection_display":
                        name,
                    "specimen_count":
                        0,
                    "collection_uri":
                        "",
                    "dataset_uri":
                        "",
                },
            )

            row[
                "specimen_count"
            ] += 1

            if (
                not row[
                    "collection_uri"
                ]
                and specimen.get(
                    "collection_uri"
                )
            ):
                row[
                    "collection_uri"
                ] = specimen[
                    "collection_uri"
                ]

            if (
                not row[
                    "dataset_uri"
                ]
                and specimen.get(
                    "dataset_uri"
                )
            ):
                row[
                    "dataset_uri"
                ] = specimen[
                    "dataset_uri"
                ]

        return sorted(
            grouped.values(),
            key=lambda row:
                (
                    -row[
                        "specimen_count"
                    ],
                    row[
                        "collection_display"
                    ],
                ),
        )

    @staticmethod
    def numeric_summary(
        specimens,
        key,
    ):
        values = []

        for row in (
            specimens
            or []
        ):
            try:
                value = float(
                    row.get(
                        key
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if math.isfinite(
                value
            ):
                values.append(
                    value
                )

        if not values:
            return {
                "n": 0,
                "mean": None,
                "min": None,
                "max": None,
            }

        return {
            "n":
                len(values),
            "mean":
                sum(values)
                / len(values),
            "min":
                min(values),
            "max":
                max(values),
        }

    def authority_context(
        self,
        resolutions,
        profile,
    ) -> tuple[
        EnrichmentSection,
        list[dict],
    ]:
        resolution = (
            resolutions.get(
                "authority",
                {}
            )
        )

        sources = []

        if not resolution.get(
            "accepted"
        ):
            return (
                EnrichmentSection(
                    status="not_available",
                    summary=(
                        profile
                        .historical_context
                        .summary
                    ),
                    source_scope=(
                        "multimodal_model_context_only"
                    ),
                    notes=[
                        (
                            "No se resolvió la autoridad "
                            "contra Nomisma."
                        )
                    ],
                ),
                sources,
            )

        candidate = (
            resolution[
                "candidate"
            ]
        )

        cid = candidate.get(
            "id",
            ""
        )

        concept_payload = (
            self.provider
            .concept_jsonld(
                cid
            )
        )

        concept = (
            self.provider
            .concept_summary(
                concept_payload
            )
        )

        qid = (
            self.provider
            .wikidata_id(
                concept.get(
                    "exact_matches",
                    [],
                )
            )
        )

        wikidata = {}
        wikipedia = {}

        if qid:
            try:
                wikidata = (
                    self.provider
                    .wikidata_context(
                        qid
                    )
                )
            except Exception:
                wikidata = {}

        eswiki = (
            wikidata.get(
                "eswiki_title",
                ""
            )
        )

        if eswiki:
            try:
                wikipedia = (
                    self.provider
                    .wikipedia_summary(
                        eswiki
                    )
                )
            except Exception:
                wikipedia = {}

        records = [{
            "nomisma": {
                "id":
                    cid,
                "uri":
                    candidate.get(
                        "uri"
                    ),
                "label":
                    concept.get(
                        "label"
                    ),
                "definition":
                    concept.get(
                        "definition"
                    ),
                "exact_matches":
                    concept.get(
                        "exact_matches",
                        [],
                    ),
            },
            "wikidata":
                wikidata,
            "wikipedia_es":
                wikipedia,
        }]

        sources.append({
            "name":
                "Nomisma.org",
            "url":
                candidate.get(
                    "uri"
                ),
            "role":
                "authority_concept",
        })

        if wikidata.get(
            "entity_url"
        ):
            sources.append({
                "name":
                    "Wikidata",
                "url":
                    wikidata[
                        "entity_url"
                    ],
                "role":
                    "historical_context",
            })

        if wikipedia.get(
            "url"
        ):
            sources.append({
                "name":
                    "Wikipedia ES",
                "url":
                    wikipedia[
                        "url"
                    ],
                "role":
                    "historical_summary",
            })

        summary = (
            wikipedia.get(
                "extract"
            )
            or wikidata.get(
                "description"
            )
            or profile
            .historical_context
            .summary
            or concept.get(
                "definition"
            )
        )

        return (
            EnrichmentSection(
                status="available",
                summary=
                    summary,
                records=
                    records,
                source_scope=(
                    "resolved_authority_context"
                ),
                is_exhaustive=False,
                notes=[
                    (
                        "La identificación de autoridad "
                        "procede del modelo y se ha "
                        "reconciliado contra Nomisma."
                    )
                ],
            ),
            sources,
        )

    def mint_context(
        self,
        resolutions,
        geography,
    ) -> tuple[
        EnrichmentSection,
        list[dict],
    ]:
        resolution = (
            resolutions.get(
                "mint",
                {}
            )
        )

        sources = []

        if not resolution.get(
            "accepted"
        ):
            return (
                EnrichmentSection(
                    status="not_available",
                    source_scope=(
                        "mint_not_resolved"
                    ),
                    notes=[
                        "No se resolvió la ceca contra Nomisma."
                    ],
                ),
                sources,
            )

        candidate = (
            resolution[
                "candidate"
            ]
        )

        cid = candidate.get(
            "id"
        )

        try:
            concept = (
                self.provider
                .concept_summary(
                    self.provider
                    .concept_jsonld(
                        cid
                    )
                )
            )
        except Exception:
            concept = {}

        records = [{
            "nomisma_id":
                cid,
            "nomisma_uri":
                candidate.get(
                    "uri"
                ),
            "label": (
                concept.get(
                    "label"
                )
                or candidate.get(
                    "name"
                )
            ),
            "definition":
                concept.get(
                    "definition"
                ),
            "geography":
                geography.get(
                    "mint_features",
                    [],
                ),
        }]

        sources.append({
            "name":
                "Nomisma.org",
            "url":
                candidate.get(
                    "uri"
                ),
            "role":
                "mint_context",
        })

        return (
            EnrichmentSection(
                status="available",
                summary=(
                    concept.get(
                        "definition"
                    )
                    or (
                        "Ceca reconciliada con "
                        "Nomisma.org."
                    )
                ),
                records=
                    records,
                source_scope=(
                    "resolved_mint_context"
                ),
                is_exhaustive=False,
                notes=[
                    (
                        "La ceca procede del análisis "
                        "multimodal y se reconcilia "
                        "contra Nomisma."
                    )
                ],
            ),
            sources,
        )

    def museum_section(
        self,
        comparable,
    ) -> tuple[
        EnrichmentSection,
        list[dict],
    ]:
        specimens = (
            comparable.get(
                "records",
                []
            )
            or []
        )

        collections = (
            self.collection_summary(
                specimens
            )
        )

        records = [
            {
                **row,
                "relationship":
                    "attribute_comparable",
            }
            for row in specimens[
                :self.max_specimens_for_app
            ]
        ]

        notes = [
            (
                "No son necesariamente ejemplares "
                "del mismo RIC exacto."
            ),
            (
                "Coinciden con los atributos "
                "resueltos indicados en match_roles."
            ),
            (
                "Los datasets enlazados en Nomisma "
                "no constituyen un censo exhaustivo "
                "de todas las colecciones."
            ),
        ]

        sources = [{
            "name":
                "Nomisma SPARQL",
            "url":
                self.provider.NOMISMA_QUERY_URL,
            "role":
                "comparable_specimens",
        }]

        return (
            EnrichmentSection(
                status=(
                    "available"
                    if specimens
                    else "no_records"
                ),
                summary=(
                    f"{len(specimens)} ejemplares "
                    f"comparables recuperados en "
                    f"{len(collections)} "
                    "colecciones/conjuntos de datos."
                ),
                records=[
                    {
                        "collections":
                            collections,
                        "specimens":
                            records,
                        "query_strategy":
                            comparable.get(
                                "chosen_roles",
                                [],
                            ),
                        "query_attempts":
                            comparable.get(
                                "attempts",
                                [],
                            ),
                    }
                ],
                source_scope=(
                    "attribute_matched_ric_types"
                ),
                is_exhaustive=False,
                notes=notes,
            ),
            sources,
        )

    def archaeological_section(
        self,
        geography,
    ) -> tuple[
        EnrichmentSection,
        list[dict],
    ]:
        context_role = (
            geography.get(
                "context_role"
            )
        )

        context_id = (
            geography.get(
                "context_id"
            )
        )

        findspots = (
            geography.get(
                "findspots",
                []
            )
        )

        hoards = (
            geography.get(
                "hoards",
                []
            )
        )

        sources = []

        if context_id:
            sources.extend([
                {
                    "name":
                        "Nomisma getFindspots",
                    "url": (
                        self.provider
                        .NOMISMA_FINDSPOTS_URL
                    ),
                    "role":
                        "contextual_findspots",
                },
                {
                    "name":
                        "Nomisma getHoards",
                    "url": (
                        self.provider
                        .NOMISMA_HOARDS_URL
                    ),
                    "role":
                        "contextual_hoards",
                },
            ])

        return (
            EnrichmentSection(
                status=(
                    "available"
                    if (
                        findspots
                        or hoards
                    )
                    else "no_records"
                ),
                summary=(
                    f"{len(findspots)} hallazgos "
                    f"y {len(hoards)} tesoros "
                    "recuperados para contextualizar "
                    "la distribución del concepto "
                    "numismático seleccionado."
                    if context_id
                    else (
                        "No se pudo resolver un "
                        "concepto adecuado para "
                        "contextualizar hallazgos."
                    )
                ),
                records=[{
                    "context_role":
                        context_role,
                    "context_nomisma_id":
                        context_id,
                    "findspots":
                        findspots,
                    "hoards":
                        hoards,
                }],
                source_scope=(
                    "contextual_distribution_by_nomisma_concept"
                ),
                is_exhaustive=False,
                notes=[
                    (
                        "Estos registros contextualizan "
                        "la circulación del concepto "
                        "seleccionado (preferentemente "
                        "la autoridad), no del RIC "
                        "exacto de la moneda."
                    )
                ]
                + list(
                    geography.get(
                        "errors",
                        [],
                    )
                ),
            ),
            sources,
        )

    def metrology_section(
        self,
        metrology,
        specimens,
    ) -> tuple[
        EnrichmentSection,
        list[dict],
    ]:
        specimen_stats = {
            "weight_g":
                self.numeric_summary(
                    specimens,
                    "weight_g",
                ),
            "diameter_mm":
                self.numeric_summary(
                    specimens,
                    "diameter_mm",
                ),
            "axis":
                self.numeric_summary(
                    specimens,
                    "axis",
                ),
        }

        records = [{
            "nomisma_api":
                metrology,
            "retrieved_specimen_stats":
                specimen_stats,
        }]

        sources = [{
            "name":
                "Nomisma metrical APIs",
            "url":
                "https://nomisma.org/documentation/apis/",
            "role":
                "comparative_metrology",
        }]

        return (
            EnrichmentSection(
                status=(
                    "available"
                    if metrology.get(
                        "status"
                    ) == "completed"
                    else "not_available"
                ),
                summary=(
                    "Estadísticas metrológicas "
                    "calculadas sobre restricciones "
                    "numismáticas comparables."
                ),
                records=
                    records,
                source_scope=(
                    "comparable_attribute_metrology"
                ),
                is_exhaustive=False,
                notes=[
                    (
                        "Los valores describen "
                        "ejemplares comparables y no "
                        "constituyen una medida de la "
                        "moneda subida por el usuario."
                    )
                ],
            ),
            sources,
        )

    def market_section(
        self,
        provenance,
    ) -> tuple[
        EnrichmentSection,
        list[dict],
    ]:
        auction_mentions = (
            self.provider
            .auction_mentions(
                provenance
            )
        )

        sources = []

        if provenance:
            sources.append({
                "name":
                    "American Numismatic Society",
                "url":
                    self.provider.ANS_SEARCH_ID_BASE,
                "role":
                    "published_provenance",
            })

        return (
            EnrichmentSection(
                status=(
                    "available"
                    if (
                        provenance
                        or auction_mentions
                    )
                    else "no_records"
                ),
                summary=(
                    f"{len(provenance)} registros ANS "
                    f"revisados; "
                    f"{len(auction_mentions)} "
                    "menciones abiertas de "
                    "venta/subasta detectadas."
                ),
                records=[{
                    "ans_provenance":
                        provenance,
                    "auction_mentions":
                        auction_mentions,
                }],
                source_scope=(
                    "open_published_provenance_only"
                ),
                is_exhaustive=False,
                notes=[
                    (
                        "No se realiza scraping de "
                        "plataformas comerciales."
                    ),
                    (
                        "Las menciones de subasta "
                        "proceden únicamente de "
                        "procedencias publicadas y "
                        "trazables de los ejemplares "
                        "comparables recuperados."
                    ),
                ],
            ),
            sources,
        )

    def enrich(
        self,
        profile: CoinProfile,
    ) -> ProfileEnrichment:
        authority = self._value(
            profile.authority
        )

        mint = self._value(
            profile.mint
        )

        denomination = self._value(
            profile.denomination
        )

        material = self._value(
            profile.material
        )

        resolutions = (
            self.provider
            .resolve_profile_concepts(
                authority=
                    authority,
                mint=
                    mint,
                denomination=
                    denomination,
                material=
                    material,
            )
        )

        comparable = (
            self.provider
            .comparable_specimens(
                resolutions,
                max_specimens=
                    self.max_specimens,
            )
        )

        specimens = (
            comparable.get(
                "records",
                []
            )
        )

        metrology = (
            self.provider
            .metrology(
                resolutions
            )
        )

        geography = (
            self.provider
            .contextual_geography(
                resolutions,
                max_records=
                    self.max_geo_records,
            )
        )

        provenance = (
            self.provider
            .ans_provenance(
                specimens,
                max_fetch=
                    self.max_ans_provenance_fetch,
            )
        )

        (
            authority_section,
            authority_sources,
        ) = self.authority_context(
            resolutions,
            profile,
        )

        (
            mint_section,
            mint_sources,
        ) = self.mint_context(
            resolutions,
            geography,
        )

        (
            museum_section,
            museum_sources,
        ) = self.museum_section(
            comparable
        )

        (
            archaeology_section,
            archaeology_sources,
        ) = self.archaeological_section(
            geography
        )

        (
            metrology_section,
            metrology_sources,
        ) = self.metrology_section(
            metrology,
            specimens,
        )

        (
            market_section,
            market_sources,
        ) = self.market_section(
            provenance
        )

        resolution_source = [{
            "name":
                "Nomisma Reconciliation Service",
            "url":
                self.provider.NOMISMA_RECONCILE_URL,
            "role":
                "attribute_normalization",
            "resolved_concepts": {
                role: (
                    result.get(
                        "candidate"
                    )
                    if result.get(
                        "accepted"
                    )
                    else None
                )
                for role, result
                in resolutions.items()
            },
        }]

        all_sources = (
            resolution_source
            + authority_sources
            + mint_sources
            + museum_sources
            + archaeology_sources
            + metrology_sources
            + market_sources
        )

        # Deduplicate by name/url/role.
        seen = set()
        deduped = []

        for item in all_sources:
            key = (
                item.get(
                    "name"
                ),
                item.get(
                    "url"
                ),
                item.get(
                    "role"
                ),
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            deduped.append(
                item
            )

        return ProfileEnrichment(
            authority_context=
                authority_section,
            mint_context=
                mint_section,
            museum_presence=
                museum_section,
            archaeological_context=
                archaeology_section,
            metrology=
                metrology_section,
            market_and_auctions=
                market_section,
            sources=
                deduped,
        )
