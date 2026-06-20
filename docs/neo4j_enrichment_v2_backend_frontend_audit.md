# Neo4j Enrichment v2 Backend/Frontend Audit

## Backend ditemukan
- `app/api/v1/recommendations.py`: endpoint rekomendasi herbal.
- `app/logic/recommendation_orchestrator.py`: ekstraksi gejala, red-flag, ranking kandidat, response.
- `app/models/recommendation.py`: kontrak Pydantic request/response.
- `app/graph/repositories.py`: repository Neo4j, fallback `USED_FOR` lama.
- `app/graph/query_templates.py`: query schema dasar + query enrichment v2 baru.
- `app/graph/neo4j_client.py`: client read/write Neo4j.
- `app/core/json_safety.py`: sanitasi JSON untuk NaN/datetime/object.
- `app/core/exceptions.py`: error typed app.
- `app/services/recommendation/symptom_aliases.py`: alias gejala lokal.

## Frontend ditemukan
- Tidak ada `frontend/`, `frontend/src/`, `frontend/app/`, `frontend/components/`, atau `package.json` di repo ini.
- Ada `frontend_patch/src/types/backend.ts` dan `frontend_patch/src/lib/backendApi.ts` sebagai patch integrasi minimal Herpa_FE.
- Implementasi UI tab aktual perlu diterapkan di repo frontend utama Herpa_FE. Repo backend ini menyediakan type/helper + dokumen kontrak tab.

## String audit
- `recommendations`, `options`: ada di model/route/tests.
- `traditional_uses`, `preparation_methods`, `usage_guidelines`, dst: ditambahkan ke model, query, mapper, frontend_patch types.
- `Cara Pengolahan`, `Aturan Pakai`, `Peringatan`, `Sumber`: didokumentasikan di kontrak frontend tabs.
- `GraphRAG`: ada di README/docs/prompts.
- `HerbalRecommendationItem`: ditambahkan di `frontend_patch/src/types/backend.ts`.
- `HERB_USAGE_GUIDE`: tidak ditemukan.

## Kesimpulan
Backend siap diintegrasikan penuh dengan Neo4j enrichment v2. Frontend full tidak ada di workspace, sehingga perubahan frontend berupa patch kontrak TypeScript/helper + dokumentasi tab.
