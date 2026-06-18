# Agent Flow

1. Resolve JWT, role, persona.
2. Klasifikasi intent dan ekstraksi entitas.
3. Safety pre-check dan red-flag detection.
4. Ambil context attachment bila ada.
5. Bangun retrieval plan yang terbatas.
6. Query Neo4j dengan template terparameter.
7. Panggil PubMed/PubChem jika persona dan intent mengizinkan.
8. Susun context dengan provenance.
9. Generate jawaban menggunakan model teks.
10. Validasi grounding dan safety.
11. Format sesuai persona.
12. Simpan message, source, metric, dan event.

Raw chain-of-thought tidak dikirim atau disimpan.
