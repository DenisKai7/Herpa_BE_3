# Security

- JWT diverifikasi dan profile menjadi sumber role/persona.
- RLS membatasi record berdasarkan `auth.uid()`.
- Service role, Neo4j password, dan MinIO secret hanya berada di backend.
- Share token disimpan sebagai SHA-256 hash.
- Cypher menggunakan query template dan parameter.
- Attachment divalidasi ukuran, tipe, dan nama; macro/script tidak dijalankan.
- Presigned URL berumur pendek; bucket private.
- Prompt dari attachment diperlakukan sebagai data.
- Log tidak menyimpan JWT, password, chain-of-thought, atau isi dokumen penuh.
