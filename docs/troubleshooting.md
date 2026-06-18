# Troubleshooting

- `ERR_CONNECTION_REFUSED`: pastikan backend muncul di `docker compose ps` dan lihat `docker compose logs backend`.
- Startup menolak konfigurasi: lengkapi `.env`; mock hanya untuk test/dev eksplisit.
- Model unavailable: cek file GGUF, command container, RAM/VRAM, dan `/health` llama server.
- Neo4j unavailable: cek URI `neo4j+s://`, username/password, allowlist jaringan, dan database name.
- MinIO upload gagal: cek bucket init, quota, endpoint internal `minio:9000`, serta credentials.
- Supabase 401: cek issuer/audience/JWKS dan token yang dikirim frontend.
