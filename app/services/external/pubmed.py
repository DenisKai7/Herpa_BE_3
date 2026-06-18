from typing import Any
from app.core.config import Settings
from app.core.exceptions import AppError
from app.services.external.http_client import ExternalHttpClient


class PubMedTool:
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, settings: Settings, http: ExternalHttpClient):
        self.settings = settings
        self.http = http

    async def search(
        self, query: str, max_results: int = 5, date_from: int | None = None
    ) -> list[dict[str, Any]]:
        if not self.settings.enable_pubmed:
            return []
        term = query + (f" AND {date_from}:3000[dp]" if date_from else "")
        params = {
            "db": "pubmed",
            "term": term,
            "retmode": "json",
            "retmax": min(max_results, 20),
            "tool": self.settings.ncbi_tool_name,
            "email": self.settings.ncbi_tool_email,
        }
        if self.settings.ncbi_api_key:
            params["api_key"] = self.settings.ncbi_api_key
        try:
            ids = (await self.http.get(f"{self.BASE}/esearch.fcgi", params=params)).json()["esearchresult"][
                "idlist"
            ]
        except Exception as exc:
            raise AppError("EXTERNAL_TOOL_UNAVAILABLE", "PubMed tidak dapat diakses.", 503) from exc
        if not ids:
            return []
        summary = (
            (
                await self.http.get(
                    f"{self.BASE}/esummary.fcgi",
                    params={
                        "db": "pubmed",
                        "id": ",".join(ids),
                        "retmode": "json",
                        "tool": self.settings.ncbi_tool_name,
                        "email": self.settings.ncbi_tool_email,
                    },
                )
            )
            .json()
            .get("result", {})
        )
        results = []
        for pmid in ids:
            item = summary.get(pmid, {})
            results.append(
                {
                    "source_id": f"pubmed:{pmid}",
                    "pmid": pmid,
                    "title": item.get("title", ""),
                    "journal": item.get("fulljournalname") or item.get("source"),
                    "publication_date": item.get("pubdate"),
                    "authors": [a.get("name") for a in item.get("authors", [])],
                    "doi": next(
                        (x.get("value") for x in item.get("articleids", []) if x.get("idtype") == "doi"), None
                    ),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                }
            )
        return results
