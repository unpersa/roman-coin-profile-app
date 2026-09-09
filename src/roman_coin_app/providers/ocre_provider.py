from __future__ import annotations
import re, xml.etree.ElementTree as ET
import requests
from roman_coin_app.config import Settings
from roman_coin_app.utils import clean_type_id

class OCREProvider:
    CANONICAL_BASE = "http://numismatics.org/ocre/id/"
    WEB_BASE = "https://numismatics.org/ocre/id/"
    FEED_URL = "https://numismatics.org/ocre/feed/"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_environment()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "RomanCoinTFM/1.0 application"})

    def canonical_uri(self, type_id: str) -> str:
        return self.CANONICAL_BASE + clean_type_id(type_id)

    def web_url(self, type_id: str) -> str:
        return self.WEB_BASE + clean_type_id(type_id)

    def fetch_jsonld(self, type_id: str) -> dict:
        r = self.session.get(
            self.web_url(type_id)+".jsonld",
            timeout=self.settings.request_timeout,
            headers={"Accept":"application/ld+json"},
        )
        r.raise_for_status()
        return r.json()

    def fetch_candidate_metadata(self, type_id: str) -> dict:
        return {
            "type_id": clean_type_id(type_id),
            "canonical_uri": self.canonical_uri(type_id),
            "web_url": self.web_url(type_id),
            "jsonld": self.fetch_jsonld(type_id),
        }

    def search_feed(self, query: str, max_results=100, page_size=20) -> list[str]:
        ns={"atom":"http://www.w3.org/2005/Atom"}
        results, seen = [], set()
        for start in range(0,max_results,page_size):
            r=self.session.get(
                self.FEED_URL,
                params={"q":query,"start":start},
                timeout=self.settings.request_timeout,
                headers={"Accept":"application/atom+xml"},
            )
            r.raise_for_status()
            root=ET.fromstring(r.text)
            entries=root.findall("atom:entry",ns)
            if not entries:
                break
            for entry in entries:
                values=[entry.findtext("atom:id",default="",namespaces=ns)]
                values += [x.attrib.get("href","") for x in entry.findall("atom:link",ns)]
                for value in values:
                    m=re.search(r"/ocre/id/([^/?#]+)",value or "")
                    if not m: continue
                    tid=clean_type_id(m.group(1))
                    if tid and tid not in seen:
                        seen.add(tid); results.append(tid)
            if len(entries)<page_size:
                break
        return results[:max_results]
