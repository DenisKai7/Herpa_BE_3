# Audit Kontrak Frontend Herpa_FE

Frontend target menggunakan endpoint legacy di bawah `/api`. Backend ini mempertahankan endpoint tersebut dan menambahkan endpoint kanonik `/api/v1`.

| Area | Endpoint frontend yang dipertahankan | Endpoint kanonik |
|---|---|---|
| Auth | `/api/auth/login`, `/register`, `/me` | `/api/v1/auth/*`, `/api/v1/profiles/me` |
| Chat | `/api/chat/list`, `/message`, `/message/stream`, rename, pin, share | `/api/v1/chats/*` |
| File | `/api/files/upload`, status, retry | `/api/v1/attachments/*` |
| Rekomendasi | `/api/herbal-recommendations/analyze` | `/api/v1/recommendations` |
| Admin | `/api/admin/analytics`, `/users`, `/users/role` | `/api/v1/admin/*` |
| Shared chat | `/api/chat/public/{share_id}` | `/api/v1/shared/{share_id}` |
| Quiz | disediakan melalui `/api/v1/quiz/*` | sama |

Respons chat mempertahankan `chat_id`, `response`, `quiz_data`, dan metadata tambahan. Kuis mempertahankan objek `analisis_performa` dengan `sorotan` dan `area_fokus`.
