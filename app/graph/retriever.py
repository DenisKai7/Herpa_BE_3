from typing import Any

from app.graph.compound_normalizer import CompoundNormalizer
from app.graph.entity_resolver import resolve_entities
from app.graph.repositories import KnowledgeGraphRepository


class GraphRetriever:
    def __init__(self, repository: KnowledgeGraphRepository):
        self.repository = repository

    async def retrieve(
        self, query: str, limit: int | None = 10, cache_ttl: int = 0, persona: str = ""
    ) -> dict[str, Any]:
        limit = limit or 10
        entities = resolve_entities(query)
        raw_facts: list[dict[str, Any]] = []
        for entity in entities[:limit]:
            if entity.entity_type == "plant":
                raw_facts.extend(
                    await self.repository.herb_by_name(entity.original_text, limit=limit, cache_ttl=cache_ttl)
                )
            elif entity.entity_type == "compound":
                raw_facts.extend(
                    await self.repository.herbs_by_compound(
                        entity.original_text, limit=limit, cache_ttl=cache_ttl
                    )
                )
                raw_facts.extend(
                    await self.repository.compound_by_name(
                        entity.original_text, limit=limit, cache_ttl=cache_ttl
                    )
                )

        facts = self._deduplicate_facts(raw_facts, persona=persona)
        return {
            "entities": [e.model_dump() for e in entities],
            "facts": facts,
            "grounding_status": "grounded" if facts else "insufficient",
        }

    async def direct_herb_context(
        self,
        query: str,
        compound_limit: int = 10,
        source_limit: int = 3,
        cache_ttl: int = 0,
    ) -> dict[str, Any]:
        entities = resolve_entities(query)
        herb_id = None
        herb_row: dict[str, Any] | None = None
        for entity in entities:
            if entity.entity_type != "plant":
                continue
            rows = await self.repository.find_herbs(entity.original_text, limit=1, cache_ttl=cache_ttl)
            if rows:
                herb_row = rows[0].get("plant", rows[0])
                herb_id = herb_row.get("plant_id") or herb_row.get("id")
                break
        if not herb_id:
            return {"entities": [e.model_dump() for e in entities], "herb": {}, "compounds": [], "sources": []}
        context = await self.repository.get_direct_compound_context(
            herb_id,
            compound_limit=compound_limit,
            source_limit=source_limit,
            cache_ttl=cache_ttl,
        )
        if not context.get("herb") and herb_row:
            context["herb"] = herb_row
        context["entities"] = [e.model_dump() for e in entities]
        return context

    def _deduplicate_facts(self, raw_facts: list[dict[str, Any]], persona: str = "") -> list[dict[str, Any]]:
        seen_plant_ids: set[str] = set()
        seen_compounds: set[str] = set()
        deduped: list[dict[str, Any]] = []

        for row in raw_facts:
            row = self._canonicalize_fact(row)
            plant = row.get("plant") or {}
            plant_id = plant.get("plant_id")
            if plant_id:
                if plant_id in seen_plant_ids:
                    continue
                seen_plant_ids.add(plant_id)

            # Deduplicate the inner compounds using CompoundNormalizer
            if row.get("compounds"):
                row["compounds"] = CompoundNormalizer.deduplicate(row["compounds"], persona=persona)

            # If it's a raw compound query result (no plant, just compound dict)
            compound = row.get("compound")
            if compound and isinstance(compound, dict) and compound.get("name"):
                c_name = CompoundNormalizer.normalize_name(compound["name"])
                if c_name in seen_compounds:
                    continue
                seen_compounds.add(c_name)

            deduped.append(row)
        return deduped

    @staticmethod
    def _canonicalize_fact(row: dict[str, Any]) -> dict[str, Any]:
        row.setdefault("families", [])
        row.setdefault("compounds", [])
        row.setdefault("therapeutic_uses", [])
        row.setdefault("protein_targets", [])
        row.setdefault("toxicity", [])
        row.setdefault("sources", [])
        row["traditional_uses"] = row.get("therapeutic_uses", [])
        row.setdefault("contraindications", [])
        row.setdefault("side_effects", [])
        row.setdefault("parts", [])
        return row
