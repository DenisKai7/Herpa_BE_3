# Audit perbaikan model mode HERPA

## Endpoint ditemukan
- `POST /api/chat/message` -> `app/api/v1/chats.py::send_message`
- `POST /api/chat/message/stream` -> `app/api/v1/chats.py::stream_message`
- `GET /api/v1/chats`
- `GET /api/v1/chats/{chat_id}/messages`
- `POST /api/v1/chats/messages`
- `POST /api/v1/chats/messages/stream`
- `POST /api/v1/chats/{chat_id}/messages/stream`

## Komponen utama
- Compatibility route: `app/api/v1/chats.py`
- Chat orchestrator: `app/logic/chat_orchestrator.py`
- Agent graph: `app/agents/graph.py`
- Model gateway: `app/services/ai/model_gateway.py`
- Text client: `app/services/ai/text_client.py`
- Neo4j retriever: `app/graph/retriever.py`, `app/agents/graph_retriever_agent.py`
- Grounding validator: `app/graph/grounding_validator.py`, `app/agents/grounding_validator_agent.py`
- Error handler: `app/core/exceptions.py`
- Health endpoint: `app/api/v1/health.py`
- Pydantic chat schema: `app/models/chat.py`
- Persona prompt: `app/prompts/personas.py`
- Model mode prompt: `app/prompts/model_modes.py`
- Settings: `app/core/config.py`
- SSE response: `app/logic/chat_orchestrator.py::stream`

## Titik 503 sebelum perbaikan
- `app/services/ai/text_client.py`: semua HTTP/model error dinormalisasi menjadi `TEXT_MODEL_UNAVAILABLE` generic.
- `app/services/ai/model_gateway.py`: circuit breaker hanya `_failures >= 3`, tanpa half-open recovery.
- `app/graph/neo4j_client.py`: koneksi Neo4j gagal.
- `app/services/storage/minio_client.py`: MinIO gagal.
- `app/services/supabase/client.py`: Supabase gagal.
- `app/services/external/pubmed.py`, `app/services/external/pubchem.py`: tool eksternal gagal.

## Penyebab paling mungkin untuk log kasus ini
Auth, profile, chat, dan pesan user sudah berhasil. Error terjadi setelah user message tersimpan, yaitu saat `AgenticGraph` memanggil retrieval/model. Kandidat paling kuat: llama.cpp server di `127.0.0.1:8080` tidak reachable, model id mismatch, timeout, atau circuit breaker sudah open.
