# Chat Performance & Telemetry HERPA

## Mode Karakteristik

### 1. Fast Medium
- **Model Calls**: Selalu 1.
- **Refinement**: Dinonaktifkan (`allow_refinement=False`).
- **Context Budget**: Maksimal 1800 token.
- **Retrieval Limit**: Minimal (`retrieval_limit=1`, `compound_limit=10`).
- **Target Latency**: ~1.2 - 2.5 detik.

### 2. Thinking High (Adaptive)
- **Model Calls**: 1 atau 2 (refinement dilakukan hanya jika query kompleks atau terdeteksi unsupported claims).
- **Refinement**: Aktif jika dibutuhkan (`refinement_max_tokens=320`).
- **Context Budget**: Maksimal 2800 token.
- **Retrieval Limit**: Rich (`retrieval_limit=2`, `compound_limit=20`, `target_limit=8`).
- **Target Latency**: ~3.2 - 6.5 detik.

## Telemetry
Metadata response menyertakan timing pemrosesan berikut:
- `auth_ms`: Durasi otentikasi.
- `profile_ms`: Durasi resolusi profil.
- `retrieval_ms`: Durasi query database Neo4j.
- `ttft_ms`: Time-To-First-Token untuk generator streaming.
- `generation_ms`: Durasi generasi LLM.
- `persistence_ms`: Durasi penyimpanan riwayat ke database Supabase.
- `total_ms`: Latency total request.
