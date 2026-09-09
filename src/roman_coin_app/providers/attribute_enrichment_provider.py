from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import hashlib
import json
import re
import time
import unicodedata
import xml.etree.ElementTree as ET

import requests

from roman_coin_app.config import Settings


class AttributeEnrichmentProvider:
    NOMISMA_RECONCILE_URL = "https://nomisma.org/apis/reconcile"
    NOMISMA_QUERY_URL = "https://nomisma.org/query"
    NOMISMA_CANONICAL_ID_BASE = "http://nomisma.org/id/"
    NOMISMA_WEB_ID_BASE = "https://nomisma.org/id/"
    NOMISMA_FINDSPOTS_URL = "https://nomisma.org/apis/getFindspots"
    NOMISMA_HOARDS_URL = "https://nomisma.org/apis/getHoards"
    NOMISMA_MINTS_URL = "https://nomisma.org/apis/getMints"
    NOMISMA_AVG_WEIGHT_URL = "https://nomisma.org/apis/avgWeight"
    NOMISMA_AVG_DIAMETER_URL = "https://nomisma.org/apis/avgDiameter"
    NOMISMA_AVG_AXIS_URL = "https://nomisma.org/apis/avgAxis"

    WIKIDATA_ENTITY_BASE = (
        "https://www.wikidata.org/wiki/Special:EntityData/"
    )

    WIKIPEDIA_ES_SUMMARY_BASE = (
        "https://es.wikipedia.org/api/rest_v1/page/summary/"
    )

    WIKIPEDIA_ES_ACTION_API = (
        "https://es.wikipedia.org/w/api.php"
    )

    ANS_SEARCH_ID_BASE = (
        "https://numismatics.org/search/id/"
    )

    TYPE_HINTS = {
        "authority": "foaf:Person",
        "mint": "nmo:Mint",
        "denomination": "nmo:Denomination",
        "material": "nmo:Material",
    }

    # Controlled aliases for common Roman numismatic materials.
    # These avoid ambiguous reconciliation results such as
    # "Silver" -> "Nickel silver".
    CONTROLLED_ALIASES = {
        "material": {
            "silver": {
                "id": "ar",
                "name": "Silver",
            },
            "plata": {
                "id": "ar",
                "name": "Silver",
            },
            "ar": {
                "id": "ar",
                "name": "Silver",
            },
            "gold": {
                "id": "av",
                "name": "Gold",
            },
            "oro": {
                "id": "av",
                "name": "Gold",
            },
            "av": {
                "id": "av",
                "name": "Gold",
            },
            "bronze": {
                "id": "ae",
                "name": "Bronze",
            },
            "bronce": {
                "id": "ae",
                "name": "Bronze",
            },
            "copper alloy": {
                "id": "ae",
                "name": "Bronze / copper alloy",
            },
            "copper-alloy": {
                "id": "ae",
                "name": "Bronze / copper alloy",
            },
            "ae": {
                "id": "ae",
                "name": "Bronze / copper alloy",
            },
        },
    }

    def __init__(
        self,
        settings: Settings | None = None,
        cache_dir: Path | None = None,
        request_retries: int = 3,
        request_backoff: float = 1.0,
    ):
        self.settings = (
            settings
            or Settings.from_environment()
        )

        project_cache = (
            self.settings.cache_dir
            / "profile_enrichment_v2"
        )

        self.cache_dir = Path(
            cache_dir
            or project_cache
        )

        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.cache_path = (
            self.cache_dir
            / "http_cache.json"
        )

        if self.cache_path.exists():
            try:
                self.cache = json.loads(
                    self.cache_path.read_text(
                        encoding="utf-8"
                    )
                )
            except Exception:
                self.cache = {}
        else:
            self.cache = {}

        self.request_retries = int(
            request_retries
        )

        self.request_backoff = float(
            request_backoff
        )

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "RomanCoinTFM/1.0 "
                "(academic profile-first enrichment)"
            )
        })

    # ---------------------------------------------------------
    # Generic utilities
    # ---------------------------------------------------------
    @staticmethod
    def clean_text(value) -> str:
        return re.sub(
            r"\s+",
            " ",
            str(value or "").strip(),
        )

    @staticmethod
    def local_name(tag: str) -> str:
        return (
            tag.split("}")[-1]
            if "}" in tag
            else tag.split(":")[-1]
        )

    @staticmethod
    def _ascii(value) -> str:
        value = unicodedata.normalize(
            "NFKD",
            str(value or ""),
        )

        return (
            value
            .encode("ascii", "ignore")
            .decode("ascii")
            .lower()
        )

    @staticmethod
    def _binding(binding, key):
        return str(
            binding.get(
                key,
                {},
            ).get(
                "value",
                "",
            )
            or ""
        ).strip()

    @staticmethod
    def _cache_key(
        method: str,
        url: str,
        params=None,
        data=None,
        accept: str | None = None,
    ) -> str:
        payload = {
            "method": method.upper(),
            "url": url,
            "params": params or {},
            "data": data or {},
            "accept": accept or "",
        }

        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")

        return hashlib.sha256(
            encoded
        ).hexdigest()

    def _save_cache(self):
        tmp = self.cache_path.with_suffix(
            ".tmp"
        )

        tmp.write_text(
            json.dumps(
                self.cache,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        tmp.replace(
            self.cache_path
        )

    def request(
        self,
        method: str,
        url: str,
        params=None,
        data=None,
        accept: str | None = None,
        use_cache: bool = True,
    ):
        key = self._cache_key(
            method,
            url,
            params=params,
            data=data,
            accept=accept,
        )

        if (
            use_cache
            and key in self.cache
        ):
            item = self.cache[key]

            return {
                "status_code":
                    item["status_code"],
                "text":
                    item["text"],
                "url":
                    item["url"],
                "from_cache":
                    True,
            }

        headers = {}

        if accept:
            headers[
                "Accept"
            ] = accept

        last_exc = None

        for attempt in range(
            1,
            self.request_retries + 1,
        ):
            try:
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    data=data,
                    headers=headers,
                    timeout=self.settings.request_timeout,
                )

                if (
                    response.status_code == 429
                    or response.status_code >= 500
                ):
                    if (
                        attempt
                        < self.request_retries
                    ):
                        time.sleep(
                            self.request_backoff
                            * attempt
                        )
                        continue

                response.raise_for_status()

                item = {
                    "status_code":
                        response.status_code,
                    "text":
                        response.text,
                    "url":
                        response.url,
                    "cached_at_utc":
                        datetime.now(
                            timezone.utc
                        ).isoformat(),
                }

                if use_cache:
                    self.cache[
                        key
                    ] = item

                    self._save_cache()

                return {
                    **item,
                    "from_cache":
                        False,
                }

            except Exception as exc:
                last_exc = exc

                if (
                    attempt
                    < self.request_retries
                ):
                    time.sleep(
                        self.request_backoff
                        * attempt
                    )
                    continue

        raise last_exc

    # ---------------------------------------------------------
    # Nomisma concept reconciliation
    # ---------------------------------------------------------
    def reconcile(
        self,
        value: str,
        role: str,
        limit: int = 5,
    ) -> dict:
        value = self.clean_text(
            value
        )

        if not value:
            return {
                "input": "",
                "role": role,
                "status": "empty",
                "accepted": False,
                "candidate": None,
                "candidates": [],
            }

        normalized_value = self._ascii(
            value
        ).strip()

        alias = (
            self.CONTROLLED_ALIASES
            .get(
                role,
                {},
            )
            .get(
                normalized_value
            )
        )

        if alias:
            candidate = {
                "id":
                    alias["id"],
                "name":
                    alias["name"],
                "score":
                    1.0,
                "match":
                    True,
                "type": [
                    self.TYPE_HINTS.get(
                        role,
                        "",
                    )
                ],
                "uri": (
                    self.NOMISMA_CANONICAL_ID_BASE
                    + alias["id"]
                ),
                "resolution_source":
                    "controlled_numismatic_alias",
            }

            return {
                "input":
                    value,
                "role":
                    role,
                "status":
                    "resolved_controlled_alias",
                "accepted":
                    True,
                "candidate":
                    candidate,
                "candidates": [
                    candidate
                ],
            }

        query = {
            "query": value,
            "limit": int(limit),
        }

        type_hint = self.TYPE_HINTS.get(
            role
        )

        if type_hint:
            query[
                "type"
            ] = type_hint

        # The reconciliation protocol's primary transport is a
        # form-encoded POST with a JSON batch in the ``queries`` field.
        # Nomisma also historically accepted GET ?query=..., but the
        # batch POST is more robust and matches current OpenRefine specs.
        batch_key = "q0"

        query_batch = {
            batch_key: query,
        }

        response = self.request(
            "POST",
            self.NOMISMA_RECONCILE_URL,
            data={
                "queries": json.dumps(
                    query_batch,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            },
            accept="application/json",
        )

        raw_text = str(
            response.get(
                "text",
                ""
            )
            or ""
        ).lstrip("\ufeff").strip()

        try:
            payload = json.loads(
                raw_text
            )
        except json.JSONDecodeError as exc:
            preview = raw_text[:300].replace(
                "\n",
                " "
            )

            raise RuntimeError(
                "Nomisma reconciliation returned a non-JSON "
                f"response for {role}={value!r}. "
                f"HTTP={response.get('status_code')}; "
                f"preview={preview!r}"
            ) from exc

        result_block = (
            payload.get(
                batch_key,
                {}
            )
            if isinstance(
                payload,
                dict,
            )
            else {}
        )

        # Compatibility fallback for legacy single-query responses.
        if (
            isinstance(
                result_block,
                dict,
            )
            and "result" in result_block
        ):
            candidates = (
                result_block.get(
                    "result",
                    []
                )
                or []
            )
        elif (
            isinstance(
                payload,
                dict,
            )
            and "result" in payload
        ):
            candidates = (
                payload.get(
                    "result",
                    []
                )
                or []
            )
        else:
            candidates = []

        best = (
            candidates[0]
            if candidates
            else None
        )

        if best:
            score = best.get(
                "score"
            )

            try:
                score = float(
                    score
                )
            except (
                TypeError,
                ValueError,
            ):
                score = 0.0

            best_name = self._ascii(
                best.get(
                    "name",
                    "",
                )
            ).strip()

            exact_label = (
                best_name
                == normalized_value
            )

            # Nomisma currently returns exact reconciliation scores
            # on a 0..1 scale for the tested concepts. We accept an
            # explicit service match, an exact normalized label, or a
            # high-confidence candidate.
            accepted = bool(
                best.get(
                    "match",
                    False
                )
                or exact_label
                or score >= 0.85
            )
        else:
            score = 0.0
            accepted = False

        candidate = None

        if best:
            candidate = {
                "id":
                    best.get("id"),
                "name":
                    best.get("name"),
                "score":
                    score,
                "match":
                    bool(
                        best.get(
                            "match",
                            False,
                        )
                    ),
                "type":
                    best.get(
                        "type",
                        [],
                    ),
                "uri": (
                    self.NOMISMA_CANONICAL_ID_BASE
                    + str(
                        best.get(
                            "id",
                            "",
                        )
                    )
                    if best.get("id")
                    else ""
                ),
            }

        return {
            "input":
                value,
            "role":
                role,
            "status": (
                "resolved"
                if accepted
                else (
                    "candidate_below_threshold"
                    if candidate
                    else "not_found"
                )
            ),
            "accepted":
                accepted,
            "candidate":
                candidate,
            "candidates":
                candidates[:limit],
        }


    @classmethod
    def normalize_profile_value_for_reconciliation(
        cls,
        value: str,
        role: str,
    ) -> str:
        value = cls.clean_text(value)

        if role != "authority":
            return value

        value = re.sub(
            r"\(\s*(?:or|o|possibly|perhaps|maybe|probably)\b[^)]*\)",
            "",
            value,
            flags=re.IGNORECASE,
        )

        parts = re.split(
            r"\s+(?:or|o|possibly|perhaps|maybe|probably)\s+|\s*/\s*",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )

        return cls.clean_text(parts[0])

    @classmethod
    def authority_candidate_compatible(
        cls,
        query_value: str,
        candidate_name: str,
    ) -> bool:
        query = cls._ascii(query_value)
        candidate = cls._ascii(candidate_name)
        token_pattern = re.compile(r"[a-z0-9]+")

        stop = {
            "roman", "emperor", "empress",
            "caesar", "augustus", "augusta", "the"
        }

        query_tokens = {
            token
            for token in token_pattern.findall(query)
            if token not in stop and len(token) >= 3
        }

        candidate_tokens = {
            token
            for token in token_pattern.findall(candidate)
            if token not in stop and len(token) >= 3
        }

        if not query_tokens:
            return False

        return bool(query_tokens & candidate_tokens)

    def resolve_profile_concepts(
        self,
        authority: str,
        mint: str,
        denomination: str,
        material: str,
    ) -> dict:
        raw_values = {
            "authority": authority,
            "mint": mint,
            "denomination": denomination,
            "material": material,
        }

        values = {
            role: self.normalize_profile_value_for_reconciliation(value, role)
            for role, value in raw_values.items()
        }

        results = {}

        for role, value in values.items():
            result = self.reconcile(value, role)
            result["profile_input"] = raw_values[role]
            result["reconciliation_input"] = value

            if role == "authority" and result.get("accepted"):
                candidate = result.get("candidate", {}) or {}

                compatible = self.authority_candidate_compatible(
                    value,
                    candidate.get("name", ""),
                )

                result["authority_lexically_compatible"] = compatible

                if not compatible:
                    result["accepted"] = False
                    result["status"] = "rejected_authority_lexical_mismatch"
                    result["rejection_reason"] = (
                        "Nomisma candidate label is not lexically compatible "
                        "with the multimodal authority."
                    )

            results[role] = result

        return results

    # ---------------------------------------------------------
    # Nomisma concept JSON-LD
    # ---------------------------------------------------------
    def concept_jsonld(
        self,
        nomisma_id: str,
    ) -> dict:
        nomisma_id = self.clean_text(
            nomisma_id
        )

        if not nomisma_id:
            return {}

        response = self.request(
            "GET",
            (
                self.NOMISMA_WEB_ID_BASE
                + nomisma_id
                + ".jsonld"
            ),
            accept="application/ld+json",
        )

        return json.loads(
            response["text"]
        )

    @staticmethod
    def _jsonld_values(
        payload,
        local_predicate: str,
    ):
        values = []

        def local_key(key: str) -> str:
            key = str(key or "")
            key = key.split("#")[-1]
            key = key.split("/")[-1]
            key = key.split(":")[-1]
            return key

        def collect(value):
            items = value if isinstance(value, list) else [value]

            for item in items:
                if isinstance(item, dict):
                    if "@value" in item:
                        values.append({
                            "value": item["@value"],
                            "lang": item.get("@language", ""),
                        })
                    elif "@id" in item:
                        values.append({
                            "value": item["@id"],
                            "lang": "",
                        })
                    else:
                        visit(item)
                elif item is not None:
                    values.append({
                        "value": str(item),
                        "lang": "",
                    })

        def visit(node):
            if isinstance(node, list):
                for item in node:
                    visit(item)
                return

            if not isinstance(node, dict):
                return

            for key, value in node.items():
                if local_key(key) == local_predicate:
                    collect(value)
                elif isinstance(value, (dict, list)):
                    visit(value)

        visit(payload)

        deduped = []
        seen = set()

        for item in values:
            item_key = (
                str(item.get("value", "")),
                str(item.get("lang", "")),
            )

            if item_key in seen:
                continue

            seen.add(item_key)
            deduped.append(item)

        return deduped

    @classmethod
    def concept_summary(
        cls,
        payload,
    ) -> dict:
        def choose_lang(values):
            for lang in [
                "es",
                "en",
                "",
            ]:
                for item in values:
                    if (
                        str(
                            item.get(
                                "lang",
                                "",
                            )
                        ).lower()
                        == lang
                    ):
                        return item.get(
                            "value",
                            ""
                        )

            return (
                values[0].get(
                    "value",
                    ""
                )
                if values
                else ""
            )

        pref = cls._jsonld_values(
            payload,
            "prefLabel",
        )

        definition = (
            cls._jsonld_values(
                payload,
                "definition",
            )
        )

        exact = (
            cls._jsonld_values(
                payload,
                "exactMatch",
            )
        )

        return {
            "label":
                choose_lang(pref),
            "definition":
                choose_lang(
                    definition
                ),
            "exact_matches": [
                item[
                    "value"
                ]
                for item in exact
                if str(
                    item.get(
                        "value",
                        ""
                    )
                ).startswith(
                    "http"
                )
            ],
        }

    # ---------------------------------------------------------
    # Wikidata + Wikipedia
    # ---------------------------------------------------------
    @staticmethod
    def wikidata_id(
        exact_matches,
    ) -> str:
        for uri in (
            exact_matches
            or []
        ):
            match = re.search(
                r"wikidata\.org/(?:entity|wiki)/(Q\d+)",
                str(uri),
                re.I,
            )

            if match:
                return match.group(1)

        return ""

    @staticmethod
    def _claim_time(
        entity,
        prop: str,
    ):
        claims = (
            entity.get(
                "claims",
                {}
            )
            .get(
                prop,
                [],
            )
        )

        for claim in claims:
            try:
                value = (
                    claim[
                        "mainsnak"
                    ][
                        "datavalue"
                    ][
                        "value"
                    ][
                        "time"
                    ]
                )

                return value
            except Exception:
                continue

        return None

    def wikidata_context(
        self,
        qid: str,
    ) -> dict:
        if not qid:
            return {}

        response = self.request(
            "GET",
            (
                self.WIKIDATA_ENTITY_BASE
                + qid
                + ".json"
            ),
            accept="application/json",
        )

        payload = json.loads(
            response["text"]
        )

        entity = (
            payload.get(
                "entities",
                {}
            )
            .get(
                qid,
                {}
            )
        )

        labels = entity.get(
            "labels",
            {}
        )

        descriptions = entity.get(
            "descriptions",
            {}
        )

        sitelinks = entity.get(
            "sitelinks",
            {}
        )

        def lang_value(
            mapping,
            lang,
        ):
            return (
                mapping
                .get(
                    lang,
                    {}
                )
                .get(
                    "value",
                    "",
                )
            )

        eswiki = (
            sitelinks
            .get(
                "eswiki",
                {}
            )
            .get(
                "title",
                "",
            )
        )

        return {
            "qid":
                qid,
            "label":
                (
                    lang_value(
                        labels,
                        "es",
                    )
                    or lang_value(
                        labels,
                        "en",
                    )
                ),
            "description":
                (
                    lang_value(
                        descriptions,
                        "es",
                    )
                    or lang_value(
                        descriptions,
                        "en",
                    )
                ),
            "birth":
                self._claim_time(
                    entity,
                    "P569",
                ),
            "death":
                self._claim_time(
                    entity,
                    "P570",
                ),
            "eswiki_title":
                eswiki,
            "entity_url":
                (
                    "https://www.wikidata.org/wiki/"
                    + qid
                ),
        }

    def wikipedia_summary(
        self,
        title: str,
    ) -> dict:
        title = self.clean_text(
            title
        )

        if not title:
            return {}

        try:
            response = self.request(
                "GET",
                (
                    self.WIKIPEDIA_ES_SUMMARY_BASE
                    + quote(
                        title,
                        safe="",
                    )
                ),
                accept="application/json",
            )

            payload = json.loads(
                response["text"]
            )

            return {
                "title":
                    payload.get(
                        "title",
                        title,
                    ),
                "description":
                    payload.get(
                        "description",
                        "",
                    ),
                "extract":
                    payload.get(
                        "extract",
                        "",
                    ),
                "url":
                    (
                        payload
                        .get(
                            "content_urls",
                            {},
                        )
                        .get(
                            "desktop",
                            {},
                        )
                        .get(
                            "page",
                            "",
                        )
                    ),
                "source":
                    "wikipedia_rest_summary",
            }

        except Exception:
            response = self.request(
                "GET",
                self.WIKIPEDIA_ES_ACTION_API,
                params={
                    "action": "query",
                    "prop": "extracts",
                    "exintro": 1,
                    "explaintext": 1,
                    "redirects": 1,
                    "titles": title,
                    "format": "json",
                    "formatversion": 2,
                },
                accept="application/json",
            )

            payload = json.loads(
                response["text"]
            )

            pages = (
                payload.get(
                    "query",
                    {}
                )
                .get(
                    "pages",
                    [],
                )
            )

            page = (
                pages[0]
                if pages
                else {}
            )

            resolved = page.get(
                "title",
                title,
            )

            return {
                "title":
                    resolved,
                "description":
                    "",
                "extract":
                    page.get(
                        "extract",
                        "",
                    ),
                "url": (
                    "https://es.wikipedia.org/wiki/"
                    + quote(
                        resolved.replace(
                            " ",
                            "_",
                        ),
                        safe="()_",
                    )
                ),
                "source":
                    "wikipedia_action_api_fallback",
            }

    # ---------------------------------------------------------
    # SPARQL
    # ---------------------------------------------------------
    def sparql(
        self,
        query: str,
    ) -> dict:
        response = self.request(
            "GET",
            self.NOMISMA_QUERY_URL,
            params={
                "query": query
            },
            accept=(
                "application/"
                "sparql-results+json"
            ),
        )

        return json.loads(
            response["text"]
        )

    @staticmethod
    def accepted_uri(
        resolutions: dict,
        role: str,
    ) -> str:
        result = resolutions.get(
            role,
            {}
        )

        if not result.get(
            "accepted"
        ):
            return ""

        return (
            result
            .get(
                "candidate",
                {}
            )
            .get(
                "uri",
                "",
            )
        )

    @staticmethod
    def accepted_id(
        resolutions: dict,
        role: str,
    ) -> str:
        result = resolutions.get(
            role,
            {}
        )

        if not result.get(
            "accepted"
        ):
            return ""

        return (
            result
            .get(
                "candidate",
                {}
            )
            .get(
                "id",
                "",
            )
        )

    @classmethod
    def build_type_constraints(
        cls,
        resolutions: dict,
        roles: list[str],
    ) -> list[str]:
        predicates = {
            "authority":
                "nmo:hasAuthority",
            "mint":
                "nmo:hasMint",
            "denomination":
                "nmo:hasDenomination",
            "material":
                "nmo:hasMaterial",
        }

        constraints = []

        for role in roles:
            uri = cls.accepted_uri(
                resolutions,
                role,
            )

            predicate = predicates.get(
                role
            )

            if uri and predicate:
                constraints.append(
                    f"?type {predicate} <{uri}> ."
                )

        return constraints

    @classmethod
    def specimen_query(
        cls,
        resolutions: dict,
        roles: list[str],
        limit: int,
    ) -> str:
        constraints = (
            cls.build_type_constraints(
                resolutions,
                roles,
            )
        )

        constraint_block = "\n".join(
            "  " + x
            for x in constraints
        )

        return f"""
PREFIX rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX nmo:     <http://nomisma.org/ontology#>
PREFIX nm:      <http://nomisma.org/id/>
PREFIX skos:    <http://www.w3.org/2004/02/skos/core#>
PREFIX foaf:    <http://xmlns.com/foaf/0.1/>
PREFIX void:    <http://rdfs.org/ns/void#>

SELECT DISTINCT
  ?object ?type ?identifier
  ?collection ?collectionUri ?dataset
  ?weight ?diameter ?axis
  ?obvThumb ?revThumb ?obvRef ?revRef
  ?comThumb ?comRef
WHERE {{
  ?type dcterms:source nm:ric .
{constraint_block}

  ?object nmo:hasTypeSeriesItem ?type ;
          rdf:type nmo:NumismaticObject .

  OPTIONAL {{ ?object dcterms:identifier ?identifier }}

  OPTIONAL {{
    ?object nmo:hasCollection ?collectionUri .
    OPTIONAL {{
      ?collectionUri skos:prefLabel ?collection .
      FILTER(
        lang(?collection) = ""
        || langMatches(lang(?collection), "EN")
      )
    }}
  }}

  OPTIONAL {{ ?object void:inDataset ?dataset }}
  OPTIONAL {{ ?object nmo:hasWeight ?weight }}
  OPTIONAL {{ ?object nmo:hasDiameter ?diameter }}
  OPTIONAL {{ ?object nmo:hasAxis ?axis }}

  OPTIONAL {{ ?object foaf:thumbnail ?comThumb }}
  OPTIONAL {{ ?object foaf:depiction ?comRef }}

  OPTIONAL {{
    ?object nmo:hasObverse ?obverse .
    OPTIONAL {{ ?obverse foaf:thumbnail ?obvThumb }}
    OPTIONAL {{ ?obverse foaf:depiction ?obvRef }}
  }}

  OPTIONAL {{
    ?object nmo:hasReverse ?reverse .
    OPTIONAL {{ ?reverse foaf:thumbnail ?revThumb }}
    OPTIONAL {{ ?reverse foaf:depiction ?revRef }}
  }}
}}
LIMIT {int(limit)}
"""

    def comparable_specimens(
        self,
        resolutions: dict,
        max_specimens: int = 120,
        minimum_desired: int = 8,
    ) -> dict:
        strategies = [
            [
                "authority",
                "denomination",
                "mint",
                "material",
            ],
            [
                "authority",
                "denomination",
                "mint",
            ],
            [
                "authority",
                "denomination",
                "material",
            ],
            [
                "authority",
                "denomination",
            ],
            [
                "authority",
                "mint",
            ],
            [
                "authority",
            ],
            [
                "denomination",
                "mint",
            ],
        ]

        attempts = []
        chosen = None
        rows = []

        for roles in strategies:
            usable_roles = [
                role
                for role in roles
                if self.accepted_uri(
                    resolutions,
                    role,
                )
            ]

            if len(
                usable_roles
            ) != len(roles):
                continue

            query = self.specimen_query(
                resolutions,
                roles,
                max_specimens,
            )

            payload = self.sparql(
                query
            )

            current = []

            for b in (
                payload.get(
                    "results",
                    {}
                )
                .get(
                    "bindings",
                    [],
                )
            ):
                current.append({
                    "object_uri":
                        self._binding(
                            b,
                            "object",
                        ),
                    "type_uri":
                        self._binding(
                            b,
                            "type",
                        ),
                    "identifier":
                        self._binding(
                            b,
                            "identifier",
                        ),
                    "collection":
                        self._binding(
                            b,
                            "collection",
                        ),
                    "collection_uri":
                        self._binding(
                            b,
                            "collectionUri",
                        ),
                    "dataset_uri":
                        self._binding(
                            b,
                            "dataset",
                        ),
                    "weight_g":
                        self._binding(
                            b,
                            "weight",
                        ),
                    "diameter_mm":
                        self._binding(
                            b,
                            "diameter",
                        ),
                    "axis":
                        self._binding(
                            b,
                            "axis",
                        ),
                    "obverse_thumbnail":
                        self._binding(
                            b,
                            "obvThumb",
                        ),
                    "reverse_thumbnail":
                        self._binding(
                            b,
                            "revThumb",
                        ),
                    "obverse_image":
                        self._binding(
                            b,
                            "obvRef",
                        ),
                    "reverse_image":
                        self._binding(
                            b,
                            "revRef",
                        ),
                    "combined_thumbnail":
                        self._binding(
                            b,
                            "comThumb",
                        ),
                    "combined_image":
                        self._binding(
                            b,
                            "comRef",
                        ),
                    "match_roles":
                        list(roles),
                })

            # deduplicate
            seen = set()
            current = [
                row
                for row in current
                if (
                    row[
                        "object_uri"
                    ]
                    and not (
                        row[
                            "object_uri"
                        ] in seen
                        or seen.add(
                            row[
                                "object_uri"
                            ]
                        )
                    )
                )
            ]

            attempts.append({
                "roles":
                    list(roles),
                "count":
                    len(current),
            })

            if current:
                chosen = list(
                    roles
                )
                rows = current

            if (
                len(current)
                >= minimum_desired
            ):
                break

        return {
            "records":
                rows,
            "chosen_roles":
                chosen or [],
            "attempts":
                attempts,
        }

    # ---------------------------------------------------------
    # Metrical REST APIs
    # ---------------------------------------------------------
    @classmethod
    def metrology_constraints(
        cls,
        resolutions: dict,
        roles: list[str],
    ) -> str:
        prefix_map = {
            "authority":
                "nmo:hasAuthority",
            "mint":
                "nmo:hasMint",
            "denomination":
                "nmo:hasDenomination",
            "material":
                "nmo:hasMaterial",
        }

        parts = [
            "dcterms:source nm:ric"
        ]

        for role in roles:
            cid = cls.accepted_id(
                resolutions,
                role,
            )

            predicate = (
                prefix_map.get(
                    role
                )
            )

            if cid and predicate:
                parts.append(
                    f"{predicate} nm:{cid}"
                )

        return " AND ".join(
            parts
        )

    @staticmethod
    def _extract_numeric_payload(
        text: str,
    ):
        text = str(
            text or ""
        ).strip()

        try:
            payload = json.loads(
                text
            )
        except Exception:
            payload = None

        candidates = []

        def walk(value):
            if isinstance(
                value,
                dict,
            ):
                for item in (
                    value.values()
                ):
                    walk(item)

            elif isinstance(
                value,
                list,
            ):
                for item in value:
                    walk(item)

            elif isinstance(
                value,
                (
                    int,
                    float,
                ),
            ):
                candidates.append(
                    float(value)
                )

            elif isinstance(
                value,
                str,
            ):
                match = re.search(
                    r"-?\d+(?:\.\d+)?",
                    value,
                )

                if match:
                    try:
                        candidates.append(
                            float(
                                match.group()
                            )
                        )
                    except Exception:
                        pass

        if payload is not None:
            walk(payload)
        else:
            walk(text)

        return (
            candidates[0]
            if candidates
            else None
        )

    def metrology(
        self,
        resolutions: dict,
    ) -> dict:
        roles = [
            role
            for role in [
                "authority",
                "denomination",
                "mint",
                "material",
            ]
            if self.accepted_id(
                resolutions,
                role,
            )
        ]

        if not roles:
            return {
                "status":
                    "no_resolved_concepts",
                "filters":
                    [],
            }

        constraints = (
            self.metrology_constraints(
                resolutions,
                roles,
            )
        )

        outputs = {}

        for key, url in {
            "average_weight_g":
                self.NOMISMA_AVG_WEIGHT_URL,
            "average_diameter_mm":
                self.NOMISMA_AVG_DIAMETER_URL,
            "average_axis":
                self.NOMISMA_AVG_AXIS_URL,
        }.items():
            try:
                response = self.request(
                    "GET",
                    url,
                    params={
                        "constraints":
                            constraints,
                        "format":
                            "json",
                    },
                    accept="application/json",
                )

                outputs[
                    key
                ] = (
                    self._extract_numeric_payload(
                        response["text"]
                    )
                )

            except Exception as exc:
                outputs[
                    key
                ] = None

                outputs[
                    key + "_error"
                ] = (
                    f"{type(exc).__name__}: "
                    f"{str(exc)[:180]}"
                )

        return {
            "status":
                "completed",
            "filters":
                roles,
            "constraints":
                constraints,
            **outputs,
        }

    # ---------------------------------------------------------
    # GeoJSON APIs
    # ---------------------------------------------------------
    def geojson_by_id(
        self,
        endpoint: str,
        nomisma_id: str,
    ) -> dict:
        if not nomisma_id:
            return {}

        response = self.request(
            "GET",
            endpoint,
            params={
                "id": nomisma_id
            },
            accept=(
                "application/geo+json"
            ),
        )

        return json.loads(
            response["text"]
        )

    @staticmethod
    def geojson_records(
        payload: dict,
        max_records: int = 50,
    ) -> list[dict]:
        rows = []

        for feature in (
            payload.get(
                "features",
                []
            )
            or []
        )[:max_records]:
            properties = (
                feature.get(
                    "properties",
                    {}
                )
                or {}
            )

            geometry = (
                feature.get(
                    "geometry",
                    {}
                )
                or {}
            )

            rows.append({
                "name": (
                    properties.get(
                        "toponym"
                    )
                    or properties.get(
                        "gazetteer_label"
                    )
                    or properties.get(
                        "label"
                    )
                    or properties.get(
                        "name"
                    )
                    or ""
                ),
                "coordinates":
                    geometry.get(
                        "coordinates"
                    ),
                "geometry_type":
                    geometry.get(
                        "type"
                    ),
                "properties":
                    properties,
            })

        return rows

    def contextual_geography(
        self,
        resolutions: dict,
        max_records: int = 50,
    ) -> dict:
        # Authority is the preferred circulation context.
        context_role = None
        context_id = ""

        for role in [
            "authority",
            "denomination",
            "mint",
        ]:
            cid = self.accepted_id(
                resolutions,
                role,
            )

            if cid:
                context_role = role
                context_id = cid
                break

        result = {
            "context_role":
                context_role,
            "context_id":
                context_id,
            "findspots":
                [],
            "hoards":
                [],
            "mint_features":
                [],
            "errors":
                [],
        }

        if context_id:
            try:
                find_payload = (
                    self.geojson_by_id(
                        self.NOMISMA_FINDSPOTS_URL,
                        context_id,
                    )
                )

                result[
                    "findspots"
                ] = (
                    self.geojson_records(
                        find_payload,
                        max_records,
                    )
                )
            except Exception as exc:
                result[
                    "errors"
                ].append(
                    "findspots: "
                    f"{type(exc).__name__}: "
                    f"{str(exc)[:180]}"
                )

            try:
                hoard_payload = (
                    self.geojson_by_id(
                        self.NOMISMA_HOARDS_URL,
                        context_id,
                    )
                )

                result[
                    "hoards"
                ] = (
                    self.geojson_records(
                        hoard_payload,
                        max_records,
                    )
                )
            except Exception as exc:
                result[
                    "errors"
                ].append(
                    "hoards: "
                    f"{type(exc).__name__}: "
                    f"{str(exc)[:180]}"
                )

        mint_id = self.accepted_id(
            resolutions,
            "mint",
        )

        if mint_id:
            try:
                mint_payload = (
                    self.geojson_by_id(
                        self.NOMISMA_MINTS_URL,
                        mint_id,
                    )
                )

                result[
                    "mint_features"
                ] = (
                    self.geojson_records(
                        mint_payload,
                        10,
                    )
                )
            except Exception as exc:
                result[
                    "errors"
                ].append(
                    "mints: "
                    f"{type(exc).__name__}: "
                    f"{str(exc)[:180]}"
                )

        return result

    # ---------------------------------------------------------
    # ANS provenance, adapted from NB22
    # ---------------------------------------------------------
    @staticmethod
    def is_ans_uri(uri: str) -> bool:
        uri = str(
            uri or ""
        ).lower()

        return (
            "numismatics.org/collection/"
            in uri
        )

    @staticmethod
    def ans_identifier(
        uri: str,
        fallback: str = "",
    ) -> str:
        uri = str(
            uri or ""
        )

        patterns = [
            r"numismatics\.org/collection/([^/?#]+)",
            r"numismatics\.org/search/id/([^/?#]+)",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                uri,
                re.I,
            )

            if match:
                return match.group(1)

        return str(
            fallback or ""
        ).strip()

    @classmethod
    def node_text(cls, node):
        values = []

        for item in node.iter():
            if (
                item.text
                and item.text.strip()
            ):
                values.append(
                    item.text.strip()
                )

        return " ".join(
            values
        )

    @classmethod
    def provenance_sections(
        cls,
        root,
    ):
        tokens = [
            "provenance",
            "acquisition",
            "previous",
            "auction",
            "sale",
        ]

        out = []
        seen = set()

        for node in root.iter():
            name = (
                cls.local_name(
                    node.tag
                )
                .lower()
            )

            if not any(
                token in name
                for token in tokens
            ):
                continue

            text = cls.node_text(
                node
            )

            if (
                text
                and text not in seen
            ):
                seen.add(
                    text
                )

                out.append({
                    "section":
                        name,
                    "text":
                        text,
                })

        return out

    def ans_provenance(
        self,
        specimens: list[dict],
        max_fetch: int = 8,
    ) -> list[dict]:
        candidates = [
            specimen
            for specimen in specimens
            if self.is_ans_uri(
                specimen.get(
                    "object_uri",
                    ""
                )
            )
        ][:max_fetch]

        rows = []

        for specimen in candidates:
            identifier = (
                self.ans_identifier(
                    specimen.get(
                        "object_uri",
                        ""
                    ),
                    specimen.get(
                        "identifier",
                        "",
                    ),
                )
            )

            if not identifier:
                continue

            xml_url = (
                self.ANS_SEARCH_ID_BASE
                + identifier
                + ".xml"
            )

            try:
                response = self.request(
                    "GET",
                    xml_url,
                    accept="application/xml",
                )

                root = ET.fromstring(
                    response["text"]
                )

                sections = (
                    self.provenance_sections(
                        root
                    )
                )

                rows.append({
                    "identifier":
                        identifier,
                    "object_uri":
                        specimen.get(
                            "object_uri",
                            "",
                        ),
                    "record_url":
                        self.ANS_SEARCH_ID_BASE
                        + identifier,
                    "provenance_sections":
                        sections,
                    "has_provenance_data":
                        bool(
                            sections
                        ),
                    "status":
                        "completed",
                })

            except Exception as exc:
                rows.append({
                    "identifier":
                        identifier,
                    "object_uri":
                        specimen.get(
                            "object_uri",
                            "",
                        ),
                    "record_url":
                        self.ANS_SEARCH_ID_BASE
                        + identifier,
                    "provenance_sections":
                        [],
                    "has_provenance_data":
                        False,
                    "status":
                        "error",
                    "error": (
                        f"{type(exc).__name__}: "
                        f"{str(exc)[:220]}"
                    ),
                })

        return rows

    @classmethod
    def auction_mentions(
        cls,
        provenance_rows: list[dict],
    ) -> list[dict]:
        terms = [
            "auction",
            "sale",
            "sotheby",
            "christie",
            "leu",
            "künker",
            "kunker",
            "classical numismatic group",
            "cng",
            "naville",
            "numismatica ars classica",
        ]

        rows = []

        for row in (
            provenance_rows
            or []
        ):
            for section in (
                row.get(
                    "provenance_sections",
                    []
                )
                or []
            ):
                text = cls.clean_text(
                    section.get(
                        "text",
                        ""
                    )
                )

                ascii_text = (
                    cls._ascii(
                        text
                    )
                )

                matches = [
                    term
                    for term in terms
                    if cls._ascii(
                        term
                    ) in ascii_text
                ]

                if matches:
                    rows.append({
                        "identifier":
                            row.get(
                                "identifier"
                            ),
                        "record_url":
                            row.get(
                                "record_url"
                            ),
                        "section":
                            section.get(
                                "section"
                            ),
                        "text":
                            text,
                        "matched_terms":
                            matches,
                    })

        return rows
