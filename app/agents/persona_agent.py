from app.agents.state import AgentState
from app.core.constants import Persona


class PersonaAgent:
    async def run(self, state: AgentState) -> AgentState:
        requested = state.get("persona", "umum")
        state["persona"] = requested if requested in {p.value for p in Persona} else Persona.UMUM.value
        return state
