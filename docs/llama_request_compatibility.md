# Llama.cpp Request Compatibility & Payload Sanitizer

## Penanganan Error HTTP 400
Backend tidak lagi mengasumsikan semua error HTTP 400 dari `llama-server` sebagai context overflow. Response body dibaca dan dicatat secara rinci.

### Klasifikasi Error
1. **MODEL_CONTEXT_OVERFLOW (HTTP 413)**: Dipicu jika response body mengandung kata kunci seperti `context window`, `context size`, `n_ctx`, atau `too many tokens`.
2. **MODEL_REQUEST_INVALID (HTTP 502)**: Dipicu untuk error format, invalid parameters, atau sampling issues lainnya.

## Payload Sanitizer & Single Retry
Jika llama.cpp menolak parameter tertentu (misalnya `cache_prompt`, `top_k`, `min_p`, atau `repeat_penalty` karena perbedaan build):
1. Parser membaca nama parameter yang bermasalah dari pesan error.
2. Parameter tersebut dihapus dari payload dictionary.
3. Melakukan retry request **maksimal satu kali** secara otomatis.
4. Kejadian ini dicatat melalui log `llama_payload_field_removed`.
