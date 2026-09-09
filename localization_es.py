from __future__ import annotations
from functools import lru_cache
from typing import Any
import re
import requests

AUTHORITY_ES={
'augustus':'Augusto','tiberius':'Tiberio','caligula':'Calígula','claudius':'Claudio','nero':'Nerón','galba':'Galba','otho':'Otón','vitellius':'Vitelio','vespasian':'Vespasiano','titus':'Tito','domitian':'Domiciano','nerva':'Nerva','trajan':'Trajano','hadrian':'Adriano','antoninus pius':'Antonino Pío','marcus aurelius':'Marco Aurelio','lucius verus':'Lucio Vero','commodus':'Cómodo','septimius severus':'Septimio Severo','caracalla':'Caracalla','geta':'Geta','macrinus':'Macrino','elagabalus':'Heliogábalo','severus alexander':'Alejandro Severo','maximinus thrax':'Maximino el Tracio','gordian i':'Gordiano I','gordian ii':'Gordiano II','gordian iii':'Gordiano III','philip i':'Filipo I','philip ii':'Filipo II','decius':'Decio','trebonianus gallus':'Treboniano Galo','aemilian':'Emiliano','valerian':'Valeriano','gallienus':'Galieno','claudius gothicus':'Claudio II el Gótico','aurelian':'Aureliano','tacitus':'Tácito','probus':'Probo','carus':'Caro','diocletian':'Diocleciano','maximian':'Maximiano','constantius i':'Constancio I','galerius':'Galerio','constantine i':'Constantino I','licinius':'Licinio','constantine ii':'Constantino II','constantius ii':'Constancio II','constans':'Constante','julian ii':'Juliano II','jovian':'Joviano','valentinian i':'Valentiniano I','valens':'Valente','gratian':'Graciano','valentinian ii':'Valentiniano II','theodosius i':'Teodosio I','arcadius':'Arcadio','honorius':'Honorio','magnus maximus':'Magno Máximo','clodius albinus':'Clodio Albino'}
MATERIAL_ES={'gold':'Oro','silver':'Plata','bronze':'Bronce','copper':'Cobre','copper alloy':'Aleación de cobre','bronze / copper alloy':'Bronce / aleación de cobre','orichalcum':'Oricalco','billon':'Vellón'}
DENOMINATION_ES={'aureus':'Áureo','denarius':'Denario','quinarius':'Quinario','sestertius':'Sestercio','dupondius':'Dupondio','as':'As','semis':'Semis','quadrans':'Cuadrante','antoninianus':'Antoniniano','follis':'Follis','nummus':'Nummus','solidus':'Sólido','siliqua':'Siliqua','miliarensis':'Miliarense','light miliarensis':'Miliarense ligero'}
MINT_ES={'rome':'Roma','treveri':'Tréveris','trier':'Tréveris','aquileia':'Aquilea','antioch':'Antioquía','constantinople':'Constantinopla','siscia':'Siscia','thessalonica':'Tesalónica','arelate':'Arelate (Arlés)','arles':'Arlés','lugdunum':'Lugdunum (Lyon)','mediolanum':'Mediolanum (Milán)','ravenna':'Rávena','alexandria':'Alejandría','nicomedia':'Nicomedia','cyzicus':'Cícico','heraclea':'Heraclea','ostia':'Ostia','carthage':'Cartago'}
DYNASTY_ES={'julio-claudian dynasty':'Dinastía Julio-Claudia','julio claudian dynasty':'Dinastía Julio-Claudia','flavian dynasty':'Dinastía Flavia','nerva-antonine dynasty':'Dinastía Nerva-Antonina','antonine dynasty':'Dinastía Antonina','severan dynasty':'Dinastía Severa','constantinian dynasty':'Dinastía Constantiniana','valentinian dynasty':'Dinastía Valentiniana','theodosian dynasty':'Dinastía Teodosiana'}
PERIOD_ES={'early imperial / principate':'Alto Imperio / Principado','principate':'Principado','early roman empire':'Alto Imperio romano','roman empire':'Imperio romano','late roman empire':'Bajo Imperio romano','late antiquity':'Antigüedad tardía','crisis of the third century':'Crisis del siglo III','tetrarchy':'Tetrarquía'}
PLACE_ES={'latium':'Lacio','italy':'Italia','rome':'Roma','gaul':'Galia','germany':'Germania','asia minor':'Asia Menor'}
ROLE_ES={'authority':'autoridad','denomination':'denominación','mint':'ceca','material':'material','dynasty':'dinastía','period':'periodo'}
SOURCE_ROLE_ES={'attribute_normalization':'normalización de atributos','authority_concept':'concepto de autoridad','historical_context':'contexto histórico','historical_summary':'resumen histórico','mint_context':'contexto de la ceca','comparable_specimens':'ejemplares comparables','contextual_findspots':'hallazgos contextuales','contextual_hoards':'tesoros contextuales','comparative_metrology':'metrología comparativa','published_provenance':'procedencia publicada'}
SOURCE_NAME_ES={'nomisma reconciliation service':'Servicio de reconciliación de Nomisma','nomisma metrical apis':'API métricas de Nomisma','american numismatic society':'American Numismatic Society (ANS)'}
COLUMN_ES={'collection_display':'Colección','specimen_count':'Ejemplares','collection_uri':'URI de la colección','dataset_uri':'URI del conjunto de datos','object_uri':'URI del objeto','identifier':'Identificador','collection':'Colección','weight_g':'Peso (g)','diameter_mm':'Diámetro (mm)','axis':'Eje (h)','lat':'Latitud','lon':'Longitud','kind':'Tipo','label':'Nombre','source':'Fuente','relationship':'Relación','record_url':'Registro'}

def _key(v:Any)->str:return re.sub(r'\s+',' ',str(v or '').strip().lower())
def _lookup(v:Any,m:dict[str,str])->str:
    t=str(v or '').strip(); return m.get(_key(t),t)
def date_range_value_es(v:Any)->str:
    if not isinstance(v,dict): return str(v or '').strip() or 'No disponible'
    a,b=v.get('from'),v.get('to')
    if a is None and b is None:return 'No disponible'
    if a is not None and b is not None:return f'{a} d. C.' if a==b else f'{a}–{b} d. C.'
    return f'desde {a} d. C.' if a is not None else f'hasta {b} d. C.'
def display_value_es(v:Any,field:str|None=None)->str:
    if field=='date_range':return date_range_value_es(v)
    t=str(v or '').strip()
    if not t:return 'No disponible'
    m={'authority':AUTHORITY_ES,'material':MATERIAL_ES,'denomination':DENOMINATION_ES,'mint':MINT_ES,'dynasty':DYNASTY_ES,'period':PERIOD_ES}.get(field)
    if m is not None:return _lookup(t,m)
    for m in (AUTHORITY_ES,MATERIAL_ES,DENOMINATION_ES,MINT_ES,DYNASTY_ES,PERIOD_ES):
        x=_lookup(t,m)
        if x!=t:return x
    return t
def display_field_value_es(profile:dict,key:str)->str:return display_value_es((profile.get(key,{}) or {}).get('value'),key)
def localize_role_expression_es(v:Any)->str:
    t=str(v or '').strip(); return ' + '.join(ROLE_ES.get(_key(p),p.strip()) for p in t.split('+')) if t else ''
def localize_source_role_es(v:Any)->str:
    t=str(v or '').strip(); return SOURCE_ROLE_ES.get(_key(t),t)
def localize_source_name_es(v:Any)->str:
    t=str(v or '').strip(); return SOURCE_NAME_ES.get(_key(t),t)
def localize_dataframe_columns_es(df):return df.rename(columns={k:v for k,v in COLUMN_ES.items() if k in df.columns})
def _looks_english(text:Any)->bool:
    v=f" {str(text or '').lower()} "
    if len(v.strip())<12:return False
    en=[' the ',' was ',' were ',' emperor ',' dynasty ',' succeeded ',' his ',' her ',' from ',' and ',' with ',' facing ',' standing ',' head ',' mint ',' ancient site ']
    es=[' el ',' la ',' los ',' las ',' fue ',' emperador ',' dinastía ',' sucedió ',' desde ',' y ',' con ',' hacia ',' cabeza ',' ceca ']
    return sum(x in v for x in en)>sum(x in v for x in es)
def localize_numismatic_text_es(v:Any,context:str|None=None)->str:
    t=str(v or '').strip()
    if not t:return 'No disponible'
    if _key(t) in {'none','null','no','not visible','no visible mintmark'}:return 'Sin exergo o marca de ceca visible.' if context=='exergue' else 'No visible.'
    exact={'laureate head of emperor facing right with short curly hair and distinct neck folds.':'Cabeza laureada del emperador hacia la derecha, con cabello corto y rizado y pliegues marcados en el cuello.','capricorn facing left with forelegs raised, tail curled behind, positioned above a globe.':'Capricornio hacia la izquierda, con las patas delanteras levantadas y la cola curvada hacia atrás, situado sobre un globo.','capricorn left, globe below.':'Capricornio hacia la izquierda, con un globo debajo.'}
    if _key(t) in exact:return exact[_key(t)]
    m=re.match(r'^Head of (.+?), laureate, right\.?$',t,re.I)
    if m:return f"Cabeza laureada de {display_value_es(m.group(1),'authority')} hacia la derecha."
    m=re.match(r'^Head of (.+?), bare, right\.?$',t,re.I)
    if m:return f"Cabeza descubierta de {display_value_es(m.group(1),'authority')} hacia la derecha."
    m=re.match(r'^Precise numeral reading on the reverse for (.+?) \((.+?) vs (.+?)\)\.?$',t,re.I)
    if m:return f'Lectura exacta del numeral del reverso para {m.group(1)} ({m.group(2)} frente a {m.group(3)}).'
    if not _looks_english(t):return t
    repl=[('laureate head of emperor','cabeza laureada del emperador'),('bare head of emperor','cabeza descubierta del emperador'),('facing right','orientada hacia la derecha'),('facing left','orientada hacia la izquierda'),('standing right','de pie hacia la derecha'),('standing left','de pie hacia la izquierda'),('seated right','sentado hacia la derecha'),('seated left','sentado hacia la izquierda'),('short curly hair','cabello corto y rizado'),('distinct neck folds','pliegues marcados en el cuello'),('forelegs raised','patas delanteras levantadas'),('tail curled behind','cola curvada hacia atrás'),('positioned above a globe','situado sobre un globo'),('globe below','globo debajo'),('holding','sosteniendo'),('shield','escudo'),('spear','lanza'),('victory','Victoria'),('capricorn','capricornio'),('head of','cabeza de'),('bust of','busto de'),('laureate','laureado'),('radiate','radiado'),('draped','drapeado'),('cuirassed','con coraza')]
    x=t
    for a,b in repl:x=re.sub(re.escape(a),b,x,flags=re.I)
    return 'Descripción visual disponible en la ficha original, pero no localizada completamente al español.' if _looks_english(x) else x[:1].upper()+x[1:]
def mint_definition_es(definition:Any,mint_label:Any)->str:
    t=str(definition or '').strip(); mint_es=display_value_es(mint_label,'mint')
    if t and not _looks_english(t):return t
    m=re.match(r'^The mint at the ancient site of (.+?) in (.+?)\.?$',t,re.I)
    if m:return f'La ceca se situaba en el antiguo emplazamiento de {_lookup(m.group(1),PLACE_ES)}, en {_lookup(m.group(2),PLACE_ES)}.'
    if mint_es and mint_es!='No disponible':return f'Ceca identificada como {mint_es}. El concepto se ha reconciliado con Nomisma.org y su localización se representa con los datos geográficos enlazados disponibles.'
    return 'La ceca se ha reconciliado con Nomisma.org; no se dispone de una descripción externa en español.'
@lru_cache(maxsize=64)
def fetch_spanish_wikipedia_extract(title:str)->str:
    title=str(title or '').strip()
    if not title:return ''
    try:
        r=requests.get('https://es.wikipedia.org/w/api.php',params={'action':'query','prop':'extracts','exintro':1,'explaintext':1,'redirects':1,'titles':title,'format':'json','formatversion':2},headers={'User-Agent':'RomanCoinTFM/1.0 (academic Spanish localization)'},timeout=8);r.raise_for_status();pages=r.json().get('query',{}).get('pages',[]);x=str(pages[0].get('extract','') if pages else '').strip();return x if x and not _looks_english(x) else ''
    except Exception:return ''

@lru_cache(maxsize=64)
def search_spanish_wikipedia_title(
    query: str,
) -> str:
    query = str(query or "").strip()

    if not query:
        return ""

    try:
        response = requests.get(
            "https://es.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": 5,
                "format": "json",
                "formatversion": 2,
            },
            headers={
                "User-Agent":
                    "RomanCoinTFM/1.0 "
                    "(academic Spanish historical context)"
            },
            timeout=8,
        )

        response.raise_for_status()

        results = (
            response.json()
            .get("query", {})
            .get("search", [])
            or []
        )

        if not results:
            return ""

        query_key = _key(query)

        for item in results:
            title = str(
                (item or {}).get("title", "")
                or ""
            ).strip()

            if title and _key(title) == query_key:
                return title

        return str(
            (results[0] or {}).get("title", "")
            or ""
        ).strip()

    except Exception:
        return ""



def historical_summary_es(
    authority_section: dict,
    historical_record: dict,
    profile: dict,
) -> str:
    wikipedia = (
        historical_record.get(
            "wikipedia_es",
            {},
        )
        or {}
    )

    wikidata = (
        historical_record.get(
            "wikidata",
            {},
        )
        or {}
    )

    extract = str(
        wikipedia.get(
            "extract",
            "",
        )
        or ""
    ).strip()

    if extract and not _looks_english(extract):
        return extract

    authority_es = display_field_value_es(
        profile,
        "authority",
    )

    authority_raw = str(
        (
            profile.get(
                "authority",
                {},
            )
            or {}
        ).get(
            "value",
            "",
        )
        or ""
    ).strip()

    candidate_titles = [
        str(
            wikidata.get(
                "eswiki_title",
                "",
            )
            or ""
        ).strip(),
        str(
            wikipedia.get(
                "title",
                "",
            )
            or ""
        ).strip(),
        str(
            authority_es
            or ""
        ).strip(),
    ]

    seen = set()

    for title in candidate_titles:
        if not title:
            continue

        title_key = _key(title)

        if title_key in seen:
            continue

        seen.add(title_key)

        candidate_extract = (
            fetch_spanish_wikipedia_extract(
                title
            )
        )

        if candidate_extract:
            return candidate_extract

    search_queries = [
        str(authority_es or "").strip(),
        str(authority_raw or "").strip(),
    ]

    for query in search_queries:
        if not query:
            continue

        found_title = (
            search_spanish_wikipedia_title(
                query
            )
        )

        if not found_title:
            continue

        candidate_extract = (
            fetch_spanish_wikipedia_extract(
                found_title
            )
        )

        if candidate_extract:
            return candidate_extract

    wikidata_description = str(
        wikidata.get(
            "description",
            "",
        )
        or ""
    ).strip()

    if (
        wikidata_description
        and not _looks_english(
            wikidata_description
        )
    ):
        return (
            wikidata_description[:1].upper()
            + wikidata_description[1:]
            + (
                ""
                if wikidata_description.endswith(".")
                else "."
            )
        )

    model_summary = str(
        (
            profile.get(
                "historical_context",
                {},
            )
            or {}
        ).get(
            "summary",
            "",
        )
        or ""
    ).strip()

    if (
        model_summary
        and not _looks_english(
            model_summary
        )
    ):
        return model_summary

    section_summary = str(
        authority_section.get(
            "summary",
            "",
        )
        or ""
    ).strip()

    if (
        section_summary
        and not _looks_english(
            section_summary
        )
    ):
        return section_summary

    return (
        "No se ha recuperado un resumen histórico "
        "en español para esta autoridad."
    )

def archaeology_summary_es(archaeology:dict)->str:
    f=archaeology.get('findspots',[]) or [];h=archaeology.get('hoards',[]) or [];return f'{len(f)} hallazgos y {len(h)} tesoros recuperados para contextualizar la distribución del concepto numismático seleccionado.'
def archaeology_context_label_es(context_role:Any,context_id:Any,profile:dict)->str:
    role=ROLE_ES.get(_key(context_role),str(context_role or '').strip())
    if _key(context_role)=='authority':label=display_field_value_es(profile,'authority')
    elif _key(context_role)=='mint':label=display_field_value_es(profile,'mint')
    else:label=str(context_id or '').strip()
    if not role and not label:return ''
    suffix=f' (Nomisma: {context_id})' if context_id else ''
    return f'{role.capitalize()} = {label}{suffix}'


# NB37_PUBLICATION_POLISH
PERIOD_ES.update({
    "late roman imperial": "Bajo Imperio romano",
    "late roman imperial period": "Bajo Imperio romano",
    "late imperial": "Bajo Imperio romano",
})

def preferred_metrology_value_es(nomisma_api:dict,specimen_stats:dict,api_key:str,stat_key:str):
    primary=(nomisma_api or {}).get(api_key)
    try: primary_number=float(primary)
    except (TypeError,ValueError): primary_number=None
    if primary_number is not None and primary_number>0: return primary_number
    fallback=((specimen_stats or {}).get(stat_key,{}) or {}).get("mean")
    try: fallback_number=float(fallback)
    except (TypeError,ValueError): fallback_number=None
    if fallback_number is not None and fallback_number>0: return fallback_number
    return None

def museum_display_counts_es(museum:dict)->dict:
    museum=museum or {}; collections=museum.get("collections",[]) or []; specimens=museum.get("specimens",[]) or []
    located=0; has_counts=False
    for collection in collections:
        try: count=int(float((collection or {}).get("specimen_count")))
        except (TypeError,ValueError): continue
        if count>=0: located+=count; has_counts=True
    in_payload=len(specimens)
    if not has_counts or located<in_payload: located=in_payload
    return {"located":located,"in_payload":in_payload,"shown":min(12,in_payload),"collections":len(collections)}
