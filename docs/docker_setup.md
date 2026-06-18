# Docker Setup

```bash
cp .env.example .env
docker compose up -d minio minio-init
docker compose --profile text up -d llama-text backend
docker compose --profile vision up -d llama-vlm
```

GPU:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile ai up -d
```

Backend dan model server dipisahkan agar perubahan kode tidak membangun ulang model runtime.
