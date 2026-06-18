from app.agents.state import AgentState
from app.graph.retriever import GraphRetriever


class GraphRetrieverAgent:
    def __init__(self, retriever: GraphRetriever):
        self.retriever = retriever

    async def run(self, state: AgentState) -> AgentState:
        limit = state.get("retrieval_limit")
        retrieval = await self.retriever.retrieve(
            state.get("user_query", ""),
            limit=limit if isinstance(limit, int) else None,
            persona=state.get("persona", ""),
        )
        state["retrieval"] = retrieval
        state["entities"] = retrieval.get("entities", state.get("entities", []))
        state["graph_facts"] = retrieval.get("facts", [])
        return state
