from app.agents.evidence_agent import EvidenceAgent
from app.agents.state import AgentState


class ExternalToolAgent:
    def __init__(self, evidence_agent: EvidenceAgent):
        self.evidence_agent = evidence_agent

    async def run(self, state: AgentState) -> AgentState:
        return await self.evidence_agent.run(state)
