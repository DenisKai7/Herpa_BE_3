from typing import Protocol

from app.agents.attachment_agent import AttachmentAgent
from app.agents.botanical_agent import BotanicalAgent
from app.agents.entity_extraction_agent import EntityExtractionAgent
from app.agents.evidence_agent import EvidenceAgent
from app.agents.intent_agent import IntentAgent
from app.agents.medical_agent import MedicalAgent
from app.agents.persona_agent import PersonaAgent
from app.agents.pharmacology_agent import PharmacologyAgent
from app.agents.phytochemical_agent import PhytochemicalAgent
from app.agents.quiz_agent import QuizAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.research_agent import ResearchAgent
from app.agents.retrieval_planner_agent import RetrievalPlannerAgent
from app.agents.safety_agent import SafetyAgent
from app.agents.state import AgentState


class StateAgent(Protocol):
    async def run(self, state: AgentState) -> AgentState: ...


class SupervisorAgent:
    def __init__(self, evidence: EvidenceAgent):
        self.prepare_steps: list[StateAgent] = [
            PersonaAgent(),
            IntentAgent(),
            SafetyAgent(),
            AttachmentAgent(),
            EntityExtractionAgent(),
            RetrievalPlannerAgent(),
        ]
        self.specialist_steps: list[StateAgent] = [
            BotanicalAgent(),
            PhytochemicalAgent(),
            PharmacologyAgent(),
            ResearchAgent(),
            MedicalAgent(),
            RecommendationAgent(),
            QuizAgent(),
        ]
        self.evidence = evidence

    async def prepare(self, state: AgentState) -> AgentState:
        for step in self.prepare_steps:
            state = await step.run(state)
        return state

    async def specialize(self, state: AgentState) -> AgentState:
        for step in self.specialist_steps:
            state = await step.run(state)
        return state
