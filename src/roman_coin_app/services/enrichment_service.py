from __future__ import annotations
from datetime import datetime, timezone
from roman_coin_app.schemas import EnrichmentResult

class EnrichmentService:
    def __init__(self, ocre_provider, nomisma_provider):
        self.ocre=ocre_provider
        self.nomisma=nomisma_provider

    @staticmethod
    def _binding(b,key):
        return str(b.get(key,{}).get("value","") or "").strip()

    def _specimens(self,type_id: str,limit: int=150) -> list[dict]:
        canonical=self.ocre.canonical_uri(type_id)
        https=self.ocre.web_url(type_id)
        query=f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX nmo: <http://nomisma.org/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX void: <http://rdfs.org/ns/void#>
SELECT DISTINCT ?object ?identifier ?collection ?collectionUri ?dataset
                ?weight ?diameter ?axis ?obvThumb ?revThumb ?obvRef ?revRef
WHERE {{
  VALUES ?typeSeriesItem {{ <{canonical}> <{https}> }}
  ?object nmo:hasTypeSeriesItem ?typeSeriesItem ; rdf:type nmo:NumismaticObject .
  OPTIONAL {{ ?object dcterms:identifier ?identifier }}
  OPTIONAL {{
    ?object nmo:hasCollection ?collectionUri .
    OPTIONAL {{
      ?collectionUri skos:prefLabel ?collection .
      FILTER(lang(?collection) = "" || langMatches(lang(?collection), "EN"))
    }}
  }}
  OPTIONAL {{ ?object void:inDataset ?dataset }}
  OPTIONAL {{ ?object nmo:hasWeight ?weight }}
  OPTIONAL {{ ?object nmo:hasDiameter ?diameter }}
  OPTIONAL {{ ?object nmo:hasAxis ?axis }}
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
LIMIT {limit}
"""
        payload=self.nomisma.sparql(query)
        rows=[]; seen=set()
        for b in payload.get("results",{}).get("bindings",[]):
            uri=self._binding(b,"object")
            if not uri or uri in seen: continue
            seen.add(uri)
            rows.append({
                "object_uri":uri,
                "identifier":self._binding(b,"identifier"),
                "collection":self._binding(b,"collection"),
                "collection_uri":self._binding(b,"collectionUri"),
                "dataset_uri":self._binding(b,"dataset"),
                "weight_g":self._binding(b,"weight"),
                "diameter_mm":self._binding(b,"diameter"),
                "axis":self._binding(b,"axis"),
                "obverse_thumbnail":self._binding(b,"obvThumb"),
                "reverse_thumbnail":self._binding(b,"revThumb"),
                "obverse_image":self._binding(b,"obvRef"),
                "reverse_image":self._binding(b,"revRef"),
            })
        return rows

    @staticmethod
    def _features(payload):
        rows=[]
        for feature in payload.get("features",[]) or []:
            p=feature.get("properties",{}) or {}
            g=feature.get("geometry",{}) or {}
            rows.append({
                "name":p.get("toponym") or p.get("gazetteer_label") or p.get("name") or "",
                "coordinates":g.get("coordinates"),
                "properties":p,
            })
        return rows

    @staticmethod
    def _collection_summary(specimens):
        counts={}
        for s in specimens:
            name=s.get("collection") or s.get("collection_uri") or s.get("dataset_uri") or "Unknown collection"
            counts[name]=counts.get(name,0)+1
        return [{"collection":k,"specimen_count":v}
                for k,v in sorted(counts.items(),key=lambda x:(-x[1],x[0]))]

    def enrich(self,type_id: str) -> EnrichmentResult:
        canonical=self.ocre.canonical_uri(type_id)
        web=self.ocre.web_url(type_id)
        jsonld=self.ocre.fetch_jsonld(type_id)
        specimens=self._specimens(type_id)
        try: findspots=self._features(self.nomisma.findspots(canonical))
        except Exception: findspots=[]
        try: hoards=self._features(self.nomisma.hoards(canonical))
        except Exception: hoards=[]
        collections=self._collection_summary(specimens)
        payload={
            "schema_version":"roman_coin_application_v1",
            "generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "identification":{"type_id":type_id,"ocre_uri":canonical,"ocre_web_url":web,"status":"verified_input"},
            "ocre_jsonld":jsonld,
            "museum_presence":{
                "specimen_count_retrieved":len(specimens),
                "collection_count":len(collections),
                "collections":collections,
                "specimens":specimens[:30],
                "is_exhaustive":False,
            },
            "archaeological_context":{
                "findspot_count_retrieved":len(findspots),
                "findspots":findspots[:50],
                "hoard_count_retrieved":len(hoards),
                "hoards":hoards[:50],
                "is_exhaustive":False,
            },
            "ownership_provenance":{"status":"adapter_extension_point","records":[]},
            "market_and_auctions":{"status":"open_data_only_extension_point","records":[]},
            "sources":[{"name":"OCRE","url":web},{"name":"Nomisma SPARQL","url":self.nomisma.QUERY_URL}],
        }
        return EnrichmentResult(type_id=type_id,payload=payload)
