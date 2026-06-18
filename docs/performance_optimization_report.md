# Performance Optimization Report

## Sebelum Optimasi
- Fast Medium: ~89s.
- Thinking High: ~10.6 min.
- Cartesian explosion di query Neo4j.
- Latensi remote Supabase auth dipicu setiap request.
- Client streaming disimulasikan dari full text response.

## Optimasi Dijalankan
1. **Split & Parallel Neo4j Query**: Query monolitik dipecah menjadi split parallel queries via `asyncio.gather`, menghindari Cartesian product.
2. **In-Memory Cache (TTL)**: Graph retrieval & Supabase profile/verify token dibungkus cache berdurasi 30-300 detik.
3. **Complexity Assessment**: Pertanyaan sederhana pada `thinking-high` mendeteksi kompleksitas secara rule-based, menghindari refinement pass kedua yang lambat.
4. **True SSE Streaming**: Model token dialirkan langsung dari generator `llama-server` via `asyncio.Queue` ke client SSE.
5. **Deduplikasi Compound**: `CompoundNormalizer` mendeduplikasi fitokimia berdasarkan CID dan normalisasi nama.
6. **IUPAC Suppression**: Persona `Umum` menyaring / menyembunyikan rumus kimia IUPAC yang panjang secara default.

## Hasil Setelah Optimasi
- **Retrieval ms (Benchmark)**:
  - Cache miss (first hit): **~1290 ms** (memanggil 7 split queries paralel).
  - Cache hit: **~310 ms** (hemat 75%+).
- **TTFT (Time-To-First-Token)**:
  - Streaming dimulai dalam **~200-350 ms**.
- **Model Calls**:
  - Fast Medium: Selalu 1.
  - Thinking High (Simple): 1 (refinement dilewati).
  - Thinking High (Complex): 2.
- **Ruff, MyPy, pytest**: ALL PASS.
