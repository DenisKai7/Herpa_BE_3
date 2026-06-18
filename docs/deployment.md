# Deployment

Gunakan reverse proxy TLS, CORS allowlist eksplisit, secret manager, backup Supabase/Neo4j/MinIO, dan resource limits. Jalankan migration secara eksplisit sebelum rollout. Jangan menjalankan destructive migration otomatis saat container restart. Pisahkan model server pada host GPU bila diperlukan.
