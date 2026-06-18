from dataclasses import dataclass
from fastapi import Request
from app.agents.evidence_agent import EvidenceAgent
from app.agents.graph import AgenticGraph
from app.agents.supervisor import SupervisorAgent
from app.core.config import Settings
from app.graph.neo4j_client import Neo4jClient
from app.graph.repositories import KnowledgeGraphRepository
from app.graph.retriever import GraphRetriever
from app.logic.attachment_orchestrator import AttachmentOrchestrator
from app.logic.chat_orchestrator import ChatOrchestrator
from app.logic.quiz_orchestrator import QuizOrchestrator
from app.logic.recommendation_orchestrator import RecommendationOrchestrator
from app.services.ai.model_gateway import ModelGateway
from app.services.documents.extractor import DocumentExtractor
from app.services.documents.image_processor import ImageProcessor
from app.services.external.http_client import ExternalHttpClient
from app.services.external.pubchem import PubChemTool
from app.services.external.pubmed import PubMedTool
from app.services.storage.minio_client import MinioStorage
from app.services.supabase.admin_service import AdminService
from app.services.supabase.auth_service import AuthService
from app.services.supabase.chat_service import ChatService
from app.services.supabase.client import SupabaseClient
from app.services.supabase.profile_service import ProfileService
from app.services.supabase.quiz_service import QuizService


@dataclass
class Services:
    settings: Settings
    supabase: SupabaseClient
    auth: AuthService
    profiles: ProfileService
    chats: ChatService
    quiz_service: QuizService
    admin: AdminService
    neo4j: Neo4jClient
    graph_repository: KnowledgeGraphRepository
    storage: MinioStorage
    model_gateway: ModelGateway
    external_http: ExternalHttpClient
    pubmed: PubMedTool
    pubchem: PubChemTool
    attachments: AttachmentOrchestrator
    chat_orchestrator: ChatOrchestrator
    recommendation_orchestrator: RecommendationOrchestrator
    quiz_orchestrator: QuizOrchestrator


async def create_services(settings: Settings) -> Services:
    supabase = SupabaseClient(settings)
    auth = AuthService(supabase)
    profiles = ProfileService(supabase)
    chats = ChatService(supabase)
    quiz = QuizService(supabase)
    admin = AdminService(supabase)
    neo4j = Neo4jClient(settings)
    repo = KnowledgeGraphRepository(neo4j)
    retriever = GraphRetriever(repo)
    storage = MinioStorage(settings)
    gateway = ModelGateway(settings)
    external = ExternalHttpClient()
    pubmed = PubMedTool(settings, external)
    pubchem = PubChemTool(settings, external)
    image = ImageProcessor(gateway)
    attachments = AttachmentOrchestrator(settings, storage, supabase, DocumentExtractor(settings), image)
    evidence = EvidenceAgent(pubmed, pubchem)
    agent_graph = AgenticGraph(SupervisorAgent(evidence), retriever, gateway)
    chat_orchestrator = ChatOrchestrator(chats, agent_graph)
    recommendation = RecommendationOrchestrator(repo, supabase, settings.allow_mock_services)
    quiz_orch = QuizOrchestrator(quiz)
    return Services(
        settings,
        supabase,
        auth,
        profiles,
        chats,
        quiz,
        admin,
        neo4j,
        repo,
        storage,
        gateway,
        external,
        pubmed,
        pubchem,
        attachments,
        chat_orchestrator,
        recommendation,
        quiz_orch,
    )


async def close_services(services: Services) -> None:
    await services.model_gateway.close()
    await services.external_http.close()
    await services.neo4j.close()
    await services.supabase.close()


def get_services(request: Request) -> Services:
    return request.app.state.services
