import asyncio
import logging
from typing import Any

from app.core.exceptions import AppError
from app.graph.neo4j_client import Neo4jClient
from app.graph.query_templates import (
    COMPOUND_BY_NAME,
    HERB_BASIC_BY_ID,
    HERB_COMPOUNDS,
    HERB_FAMILY,
    HERB_PROTEIN_TARGETS,
    HERB_SOURCES,
    HERB_THERAPEUTIC_USES,
    HERB_TOXICITY,
    HERBS_BY_COMPOUND,
    HERBS_BY_THERAPEUTIC_USE,
    HERB_FULLTEXT_SEARCH,
    HERB_PROPERTY_SEARCH_FALLBACK,
)
from app.utils.cache import AsyncMemoryTTLCache

logger = logging.getLogger(__name__)


class KnowledgeGraphRepository:
    def __init__(self, client: Neo4jClient):
        self.client = client
        self._cache = AsyncMemoryTTLCache(max_size=512)

    async def find_herbs(self, name: str, limit: int = 5, cache_ttl: int = 0) -> list[dict[str, Any]]:
        normalized = name.strip()
        if not normalized:
            return []
        cache_key = f"find_herbs:{normalized}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        parameters = {
            "search_term": normalized,
            "name": normalized,
            "limit": max(1, min(limit, 10)),
        }

        try:
            rows = await self.client.read(HERB_FULLTEXT_SEARCH, parameters)
        except AppError as exc:
            details = exc.details or {}
            reason = str(details.get("reason", "")).lower()

            missing_index_markers = (
                "there is no such fulltext schema index",
                "no such fulltext schema index",
                "herb_fulltext_idx",
            )

            missing_index = any(marker in reason for marker in missing_index_markers)

            if not missing_index:
                raise

            logger.warning(
                "herb_fulltext_index_unavailable_using_fallback",
                extra={
                    "index_name": "herb_fulltext_idx",
                    "search_term": normalized,
                },
            )

            rows = await self.client.read(HERB_PROPERTY_SEARCH_FALLBACK, parameters)

        if cache_ttl > 0:
            self._cache.set(cache_key, rows, cache_ttl)
        return rows

    async def get_herb_basic(self, herb_id: str, cache_ttl: int = 0) -> dict[str, Any] | None:
        cache_key = f"herb:v3:{herb_id}:identity"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        rows = await self.client.read(HERB_BASIC_BY_ID, {"herb_id": herb_id})
        res = rows[0].get("herb", rows[0]) if rows else None
        if cache_ttl > 0 and res is not None:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def get_herb_compounds(
        self, herb_id: str, limit: int = 20, cache_ttl: int = 0
    ) -> list[dict[str, Any]]:
        cache_key = f"herb:v3:{herb_id}:compounds:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        rows = await self.client.read(HERB_COMPOUNDS, {"herb_id": herb_id, "limit": limit})
        res = [row.get("compound", row) for row in rows]
        if cache_ttl > 0:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def get_direct_compound_context(
        self,
        herb_id: str,
        compound_limit: int = 10,
        source_limit: int = 3,
        cache_ttl: int = 0,
    ) -> dict[str, Any]:
        cache_key = f"herb:v3:{herb_id}:thinking-high:{compound_limit}:{source_limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        herb, compounds, sources = await asyncio.gather(
            self.get_herb_basic(herb_id, cache_ttl=cache_ttl),
            self.get_herb_compounds(herb_id, limit=compound_limit, cache_ttl=cache_ttl),
            self.get_herb_sources(herb_id, limit=source_limit, cache_ttl=cache_ttl),
        )
        res = {"herb": herb or {}, "compounds": compounds, "sources": sources, "retrieval_source": "neo4j"}
        if cache_ttl > 0:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def get_herb_therapeutic_uses(
        self, herb_id: str, limit: int = 20, cache_ttl: int = 0
    ) -> list[dict[str, Any]]:
        cache_key = f"uses:{herb_id}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        rows = await self.client.read(HERB_THERAPEUTIC_USES, {"herb_id": herb_id, "limit": limit})
        res = [row.get("therapeutic_use", row) for row in rows]
        if cache_ttl > 0:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def get_herb_family(self, herb_id: str, limit: int = 5, cache_ttl: int = 0) -> list[dict[str, Any]]:
        cache_key = f"family:{herb_id}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        rows = await self.client.read(HERB_FAMILY, {"herb_id": herb_id, "limit": limit})
        res = [row.get("family", row) for row in rows]
        if cache_ttl > 0:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def get_herb_protein_targets(
        self, herb_id: str, limit: int = 20, cache_ttl: int = 0
    ) -> list[dict[str, Any]]:
        cache_key = f"targets:{herb_id}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        rows = await self.client.read(HERB_PROTEIN_TARGETS, {"herb_id": herb_id, "limit": limit})
        res = [row.get("protein_target", row) for row in rows]
        if cache_ttl > 0:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def get_herb_toxicity(
        self, herb_id: str, limit: int = 10, cache_ttl: int = 0
    ) -> list[dict[str, Any]]:
        cache_key = f"toxicity:{herb_id}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        rows = await self.client.read(HERB_TOXICITY, {"herb_id": herb_id, "limit": limit})
        res = [row.get("toxicity", row) for row in rows]
        if cache_ttl > 0:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def get_herb_sources(
        self, herb_id: str, limit: int = 10, cache_ttl: int = 0
    ) -> list[dict[str, Any]]:
        cache_key = f"herb:v3:{herb_id}:sources:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        rows = await self.client.read(HERB_SOURCES, {"herb_id": herb_id, "limit": limit})
        res = [row.get("source", row) for row in rows]
        if cache_ttl > 0:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def plant_by_name(self, name: str, limit: int = 5, cache_ttl: int = 0) -> list[dict[str, Any]]:
        # Resolve the core herb list first
        herbs = await self.find_herbs(name, limit=limit, cache_ttl=cache_ttl)
        if not herbs:
            return []

        # Resolve properties for all matching herbs in parallel
        tasks = [self._hydrate_herb(row["plant"], cache_ttl) for row in herbs]
        return await asyncio.gather(*tasks)

    async def herb_by_name(self, name: str, limit: int = 5, cache_ttl: int = 0) -> list[dict[str, Any]]:
        return await self.plant_by_name(name, limit, cache_ttl)

    async def compound_by_name(self, name: str, limit: int = 5, cache_ttl: int = 0) -> list[dict[str, Any]]:
        normalized = name.strip()
        if not normalized:
            return []
        cache_key = f"compound_by_name:{normalized}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        rows = await self.client.read(COMPOUND_BY_NAME, {"name": normalized, "limit": limit})
        res = [row.get("compound", row) for row in rows]
        if cache_ttl > 0:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def herbs_by_therapeutic_use(
        self, term: str, limit: int = 10, cache_ttl: int = 0
    ) -> list[dict[str, Any]]:
        normalized = term.strip()
        if not normalized:
            return []
        cache_key = f"herbs_by_use:{normalized}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        herbs = await self.client.read(HERBS_BY_THERAPEUTIC_USE, {"term": normalized, "limit": limit})
        tasks = [self._hydrate_herb(row["plant"], cache_ttl) for row in herbs]
        res = await asyncio.gather(*tasks)
        if cache_ttl > 0:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def herbs_by_compound(
        self, compound_name: str, limit: int = 10, cache_ttl: int = 0
    ) -> list[dict[str, Any]]:
        normalized = compound_name.strip()
        if not normalized:
            return []
        cache_key = f"herbs_by_compound:{normalized}:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        herbs = await self.client.read(HERBS_BY_COMPOUND, {"compound_name": normalized, "limit": limit})
        tasks = [self._hydrate_herb(row["plant"], cache_ttl) for row in herbs]
        res = await asyncio.gather(*tasks)
        if cache_ttl > 0:
            self._cache.set(cache_key, res, cache_ttl)
        return res

    async def _hydrate_herb(self, plant: dict[str, Any], cache_ttl: int) -> dict[str, Any]:
        herb_id = plant["plant_id"]
        # Fetch relationships in parallel to avoid cartesian query cost
        families, compounds, therapeutic_uses, targets, toxicity, sources = await asyncio.gather(
            self.get_herb_family(herb_id, limit=5, cache_ttl=cache_ttl),
            self.get_herb_compounds(herb_id, limit=30, cache_ttl=cache_ttl),
            self.get_herb_therapeutic_uses(herb_id, limit=30, cache_ttl=cache_ttl),
            self.get_herb_protein_targets(herb_id, limit=20, cache_ttl=cache_ttl),
            self.get_herb_toxicity(herb_id, limit=10, cache_ttl=cache_ttl),
            self.get_herb_sources(herb_id, limit=10, cache_ttl=cache_ttl),
        )
        return {
            "plant": plant,
            "families": families,
            "compounds": compounds,
            "therapeutic_uses": therapeutic_uses,
            "protein_targets": targets,
            "toxicity": toxicity,
            "sources": sources,
        }

    @property
    def query_handlers(self):
        return {
            "herb_by_name": self.herb_by_name,
            "plant_by_name": self.plant_by_name,
            "therapeutic_use": self.herbs_by_therapeutic_use,
            "compound": self.herbs_by_compound,
            "herbs_by_therapeutic_use": self.herbs_by_therapeutic_use,
            "herbs_by_compound": self.herbs_by_compound,
        }

    async def plants_for_symptoms(
        self, symptoms: list[str], limit: int = 8, cache_ttl: int = 0
    ) -> list[dict[str, Any]]:
        by_plant: dict[str, dict[str, Any]] = {}
        for symptom in symptoms:
            for row in await self.herbs_by_therapeutic_use(symptom, limit=limit, cache_ttl=cache_ttl):
                plant = row.get("plant") or {}
                plant_id = plant.get("plant_id") or plant.get("herb_id") or plant.get("id")
                if not plant_id:
                    continue
                if plant_id not in by_plant:
                    row["matched_symptoms"] = []
                    by_plant[plant_id] = row
                matched = by_plant[plant_id].setdefault("matched_symptoms", [])
                if symptom not in matched:
                    matched.append(symptom)
        rows = list(by_plant.values())
        rows.sort(key=lambda row: len(row.get("matched_symptoms", [])), reverse=True)
        return rows[:limit]

    async def fulltext_index_status(self, index_name: str) -> dict[str, Any]:
        query = """
        SHOW FULLTEXT INDEXES
        YIELD name, state, populationPercent
        WHERE name = $index_name
        RETURN name, state, populationPercent
        """
        try:
            rows = await self.client.read(query, {"index_name": index_name})
            if not rows:
                return {"exists": False, "state": "MISSING"}
            row = rows[0]
            return {
                "exists": True,
                "state": row.get("state", "UNKNOWN"),
                "population_percent": row.get("populationPercent", 0.0),
            }
        except Exception as exc:
            logger.warning(
                "failed_to_check_fulltext_index_status",
                extra={"index_name": index_name, "error": str(exc)},
            )
            return {"exists": False, "state": "ERROR", "error": str(exc)}
