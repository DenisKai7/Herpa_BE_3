# Audit Arsitektur A.L.I.S.A.

A.L.I.S.A. digunakan sebagai referensi pola, bukan disalin domainnya. Pola yang dipertahankan adalah FastAPI sebagai lapisan API, pemisahan `api`, `core`, `logic`, `models`, `services`, `data_pipeline`, `tests`, dan `utils`, serta orkestrasi data antara Neo4j, Supabase, dan local LLM. Domain pembelajaran bahasa Jepang diganti menjadi tanaman herbal, farmasi, fitokimia, layanan informasi medis, dan pembelajaran kimia.

## Adaptasi utama

- **Neo4j**: sumber fakta domain dan traversal relasi; model tidak diberi akses Cypher arbitrer.
- **Supabase**: autentikasi, profil, chat, kuis, rekomendasi, analytics, dan audit.
- **llama.cpp**: dua server independen untuk model teks dan vision-language.
- **MinIO**: attachment, avatar, export, dan file sementara.
- **Agent graph**: state machine eksplisit agar alur dapat diuji, dibatasi, dan diobservasi.
- **Grounding**: jawaban akhir menyertakan sumber dan status grounding.

## Perbedaan yang disengaja

Backend HERPA menambahkan keamanan medis, red-flag screening, PubMed/PubChem tools, multimodal document pipeline, RLS Supabase, storage quota, serta compatibility layer untuk kontrak frontend yang telah ada.
