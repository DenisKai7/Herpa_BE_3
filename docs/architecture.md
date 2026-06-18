# Arsitektur HERPA

```mermaid
flowchart LR
  FE[Next.js Herpa_FE] -->|JWT + REST/SSE| API[FastAPI]
  API --> AUTH[Supabase Auth/Profile]
  API --> ORCH[Agentic Orchestrator]
  ORCH --> KG[Neo4j Knowledge Graph]
  ORCH --> TXT[llama.cpp Text]
  ORCH --> VLM[llama.cpp Vision]
  ORCH --> PM[PubMed]
  ORCH --> PC[PubChem]
  API --> DB[(Supabase PostgreSQL)]
  API --> OBJ[(MinIO)]
```

`app/api` hanya menangani HTTP. `app/logic` mengoordinasikan use case. `app/agents` menangani state machine. `app/graph` membatasi akses GraphRAG ke query template terparameter. `app/services` membungkus sistem eksternal. Model Pydantic menjadi kontrak lintas lapisan.
