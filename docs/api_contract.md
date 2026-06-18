# API Contract

OpenAPI tersedia di `/docs`. Endpoint utama:

- `POST /api/v1/chats`
- `GET /api/v1/chats`
- `POST /api/v1/chats/messages`
- `POST /api/v1/chats/messages/stream`
- `POST /api/v1/recommendations`
- `POST /api/v1/attachments/upload`
- `GET /api/v1/quiz/subjects`
- `POST /api/v1/quiz/attempts`
- `GET /api/v1/admin/overview`
- `GET /api/v1/health/dependencies`

Error memakai `{success:false,error:{code,message,details},meta:{request_id}}`. SSE mengirim event `message.started`, `retrieval.started`, `token`, `message.completed`, atau `message.failed`.
