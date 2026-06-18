# Asumsi

- Supabase dan Neo4j Aura dikelola sebagai layanan cloud, sehingga tidak dijalankan sebagai container lokal.
- Model GGUF tersedia di folder `models/` dan kompatibel dengan build llama.cpp yang dipakai.
- Data seed herbal hanya untuk smoke test, bukan basis bukti medis lengkap.
- Browser melakukan autentikasi melalui Supabase; backend tetap memvalidasi bearer token dan mengambil role/persona dari tabel `profiles`.
- Endpoint legacy dipertahankan untuk mengurangi perubahan frontend.
- Async worker dapat dipisahkan kemudian; versi awal memproses attachment secara sinkron dengan batas ukuran/halaman.
