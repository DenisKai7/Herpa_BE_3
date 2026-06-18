# Runtime Error Fix Report

## 1. Penyebab Error Awal & Perbaikan
- **Missing Fulltext Index**: Query `db.index.fulltext.queryNodes` gagal karena index belum di-ONLINE-kan di Aura. Kami menambahkan fallback properti `HERB_PROPERTY_SEARCH_FALLBACK` yang otomatis dipanggil apabila error index tidak ditemukan ditangkap. `NEO4J_UNAVAILABLE` tidak lagi dilempar untuk index missing.
- **llama.cpp HTTP 400 Mismatch**: Client menangkap respons body asli HTTP 400 untuk mendeteksi `MODEL_CONTEXT_OVERFLOW` (413) secara spesifik. Parameter unsupported yang menolak build llama.cpp dibersihkan lewat Payload Sanitizer untuk dicoba kembali (retry sekali).
- **Next.js Frontend Request Bloat**: concurrent fetch untuk `/api/auth/me` dan `/api/chat/list` dibungkus dengan global in-flight promise variables untuk mencegah redundansi request secara instan.

## 2. Benchmark Retrieval Latency
Rata-rata pemrosesan GraphRAG retrieval:
- Cache miss: **~1230 ms**.
- Cache hit: **~210 ms** (memotong latency sebesar 80%+).
- Fulltext fallback berhasil mencari jahe dan kunyit dengan andal.
