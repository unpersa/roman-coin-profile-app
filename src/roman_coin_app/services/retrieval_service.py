from __future__ import annotations
import re, unicodedata
from roman_coin_app.config import Settings
from roman_coin_app.schemas import Candidate, IdentificationResult

def normalize_query_text(value) -> str:
    value=unicodedata.normalize("NFKD",str(value or "").strip())
    value="".join(x for x in value if not unicodedata.combining(x))
    return re.sub(r"\s+"," ",value).strip()

def latin_legend_variants(value) -> list[str]:
    original=normalize_query_text(value)
    if not original: return []
    clean=re.sub(r"[-·•.,;:/\\|]+"," ",original)
    clean=re.sub(r"\s+"," ",clean).strip()
    classical=re.sub(r"[uU]",lambda m:"V" if m.group(0).isupper() else "v",clean)
    values=[original,clean,classical,clean.replace(" ",""),classical.replace(" ","")]
    out=[]
    for x in values:
        if x and x not in out: out.append(x)
    return out

def lucene_quote(value) -> str:
    value=str(value or "").strip().replace("\\","\\\\").replace('"','\\"')
    return f'"{value}"' if value else ""

class NullLocalRetriever:
    def retrieve(self, identification: IdentificationResult, depth: int=250) -> list[str]:
        return []

class RetrievalService:
    def __init__(self, ocre_provider, local_retriever=None, settings: Settings|None=None):
        self.ocre=ocre_provider
        self.local=local_retriever or NullLocalRetriever()
        self.settings=settings or Settings.from_environment()

    def build_api_queries(self, identification: IdentificationResult) -> list[tuple[str,float]]:
        e,h=identification.evidence,identification.hypothesis
        q=[]
        def add(text,weight):
            text=str(text or "").strip()
            if len(text)>=3 and text not in [x[0] for x in q]:
                q.append((text,float(weight)))
        for f in e.visible_reverse_fragments:
            for v in latin_legend_variants(f)[:3]: add(v,1.50)
        for f in e.visible_obverse_fragments:
            for v in latin_legend_variants(f)[:3]: add(v,1.25)
        if e.exergue_or_mintmark: add(e.exergue_or_mintmark,1.45)
        if h.authority and h.mint:
            add("authority_facet:"+lucene_quote(h.authority)+" AND mint_facet:"+lucene_quote(h.mint),1.45)
        if h.authority and h.denomination:
            add("authority_facet:"+lucene_quote(h.authority)+" AND denomination_facet:"+lucene_quote(h.denomination),1.20)
        if h.authority: add(h.authority,0.65)
        if h.mint: add(h.mint,0.55)
        return q[:18]

    def _api_ranking(self, identification: IdentificationResult) -> list[str]:
        fused={}
        for query,weight in self.build_api_queries(identification):
            ranking=self.ocre.search_feed(query,max_results=100,page_size=20)
            for rank,tid in enumerate(ranking,1):
                fused[tid]=fused.get(tid,0.0)+weight/(self.settings.rrf_k+rank)
        return [x[0] for x in sorted(fused.items(),key=lambda z:(-z[1],z[0]))]

    def retrieve(self, identification: IdentificationResult) -> list[Candidate]:
        local=self.local.retrieve(identification,depth=250)
        api=self._api_ranking(identification)
        fused={}
        for branch,ranking,weight in [
            ("local",local,self.settings.hybrid_local_weight),
            ("api",api,self.settings.hybrid_api_weight),
        ]:
            for rank,tid in enumerate(ranking,1):
                row=fused.setdefault(tid,{"score":0.0,"local_rank":None,"api_rank":None})
                row["score"] += weight/(self.settings.rrf_k+rank)
                row[branch+"_rank"]=rank
        rows=sorted(fused.items(),key=lambda z:(-z[1]["score"],z[0]))
        out=[]
        for hybrid_rank,(tid,info) in enumerate(rows[:self.settings.top_k_candidates],1):
            try:
                metadata=self.ocre.fetch_candidate_metadata(tid)
            except Exception as exc:
                metadata={"metadata_status":"not_evaluated","error":f"{type(exc).__name__}: {str(exc)[:180]}"}
            out.append(Candidate(
                type_id=tid,source="hybrid_local_api_rrf",
                local_rank=info["local_rank"],api_rank=info["api_rank"],
                hybrid_rank=hybrid_rank,hybrid_score=info["score"],metadata=metadata
            ))
        return out
