# Endpoint Inventory

Generated from the FastAPI OpenAPI schema.

| Method | Path | Tags | Summary |
|---|---|---|---|
| `GET` | `/` |  | Root |
| `GET` | `/api/admin/analytics` | Admin | Analytics |
| `GET` | `/api/admin/users` | Admin | Users |
| `POST` | `/api/admin/users/role` | Admin | Role |
| `POST` | `/api/auth/login` | Authentication | Login |
| `GET` | `/api/auth/me` | Authentication | Me |
| `PUT` | `/api/auth/me` | Authentication | Update Me |
| `PUT` | `/api/auth/me/avatar` | Authentication | Upload Avatar |
| `PUT` | `/api/auth/me/password` | Authentication | Change Password |
| `POST` | `/api/auth/register` | Authentication | Register |
| `GET` | `/api/chat/list` | Chats | List Chats |
| `POST` | `/api/chat/message` | Chats | Send Message |
| `POST` | `/api/chat/message/stream` | Chats | Stream Message |
| `GET` | `/api/chat/public/{share_id}` | Shared Chats | Public Chat |
| `DELETE` | `/api/chat/{chat_id}` | Chats | Delete Chat |
| `GET` | `/api/chat/{chat_id}/messages` | Chats | Messages |
| `PATCH` | `/api/chat/{chat_id}/pin` | Chats | Pin Legacy |
| `PATCH` | `/api/chat/{chat_id}/rename` | Chats | Rename |
| `PATCH` | `/api/chat/{chat_id}/share` | Chats | Share |
| `POST` | `/api/files/upload` | Attachments | Upload |
| `POST` | `/api/files/{attachment_id}/retry` | Attachments | Retry |
| `GET` | `/api/files/{attachment_id}/status` | Attachments | Attachment Status |
| `POST` | `/api/herbal-recommendations/analyze` | Herbal Recommendations | Analyze |
| `GET` | `/api/v1/admin/audit-logs` | Admin | Audit Logs |
| `POST` | `/api/v1/admin/storage/cleanup-orphans` | Admin Storage | Cleanup Orphans |
| `GET` | `/api/v1/admin/storage/objects` | Admin Storage | Objects |
| `DELETE` | `/api/v1/admin/storage/objects/{object_id}` | Admin Storage | Delete Object |
| `GET` | `/api/v1/admin/storage/summary` | Admin Storage | Summary |
| `GET` | `/api/v1/admin/system-health` | Admin | Health |
| `GET` | `/api/v1/admin/usage/features` | Admin | Feature Usage |
| `GET` | `/api/v1/admin/usage/models` | Admin | Model Usage |
| `GET` | `/api/v1/admin/usage/storage` | Admin | Storage Usage |
| `GET` | `/api/v1/admin/users/{user_id}` | Admin | User Detail |
| `PATCH` | `/api/v1/admin/users/{user_id}/status` | Admin | Update Status |
| `POST` | `/api/v1/attachments/complete` | Attachments | Complete |
| `POST` | `/api/v1/attachments/presign-upload` | Attachments | Presign |
| `DELETE` | `/api/v1/attachments/{attachment_id}` | Attachments | Delete |
| `POST` | `/api/v1/chats` | Chats | Create Chat |
| `GET` | `/api/v1/chats/{chat_id}` | Chats | Get Chat |
| `PATCH` | `/api/v1/chats/{chat_id}` | Chats | Update Chat |
| `DELETE` | `/api/v1/chats/{chat_id}/pin` | Chats | Unpin |
| `POST` | `/api/v1/chats/{chat_id}/pin` | Chats | Pin |
| `DELETE` | `/api/v1/chats/{chat_id}/share` | Chats | Revoke Share |
| `GET` | `/api/v1/graph/search` | Knowledge Graph | Search |
| `GET` | `/api/v1/health/dependencies` | Health | Dependencies |
| `GET` | `/api/v1/health/live` | Health | Live |
| `GET` | `/api/v1/health/ready` | Health | Ready |
| `GET` | `/api/v1/profiles/me` | Profiles | Profile |
| `POST` | `/api/v1/profiles/me/avatar/complete` | Profiles | Complete Avatar |
| `POST` | `/api/v1/profiles/me/avatar/presign-upload` | Profiles | Presign Avatar |
| `PATCH` | `/api/v1/profiles/me/persona` | Profiles | Change Persona |
| `POST` | `/api/v1/quiz/attempts` | Quiz | Start |
| `GET` | `/api/v1/quiz/attempts/{attempt_id}` | Quiz | Get Attempt |
| `POST` | `/api/v1/quiz/attempts/{attempt_id}/answers` | Quiz | Answer |
| `POST` | `/api/v1/quiz/attempts/{attempt_id}/complete` | Quiz | Complete |
| `GET` | `/api/v1/quiz/history` | Quiz | History |
| `DELETE` | `/api/v1/quiz/history/{attempt_id}` | Quiz | Delete History |
| `GET` | `/api/v1/quiz/levels/{level_id}` | Quiz | Level |
| `GET` | `/api/v1/quiz/modules` | Quiz | Modules |
| `GET` | `/api/v1/quiz/modules/{module_id}` | Quiz | Module |
| `GET` | `/api/v1/quiz/progress` | Quiz | Progress |
| `GET` | `/api/v1/quiz/subjects` | Quiz | Subjects |
| `GET` | `/api/v1/recommendations` | Herbal Recommendations | History |
| `DELETE` | `/api/v1/recommendations/{session_id}` | Herbal Recommendations | Delete Recommendation |
| `GET` | `/api/v1/recommendations/{session_id}` | Herbal Recommendations | Get Recommendation |
