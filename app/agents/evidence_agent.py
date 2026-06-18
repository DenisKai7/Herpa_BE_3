from app.agents.state import AgentState
from app.services.external.pubmed import PubMedTool
from app.services.external.pubchem import PubChemTool


class EvidenceAgent:
    def __init__(self, pubmed: PubMedTool, pubchem: PubChemTool):
        self.pubmed = pubmed
        self.pubchem = pubchem

    async def run(self, state: AgentState) -> AgentState:
        evidence = []
        persona = state.get("persona", "umum")
        query = state.get("user_query", "")
        if persona in {"peneliti", "tenaga_medis"} and state.get("intent") in {
            "research",
            "medical_information",
        }:
            evidence.extend(await self.pubmed.search(query, max_results=5))
        if persona in {"peneliti", "pelajar"}:
            for entity in state.get("entities", []):
                if entity.get("entity_type") == "compound":
                    item = await self.pubchem.compound(entity.get("canonical_name", ""))
                    if item:
                        evidence.append(item)
        state["external_evidence"] = evidence
        return state
