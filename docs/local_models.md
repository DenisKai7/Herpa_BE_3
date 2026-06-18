# Model Lokal

Letakkan tanpa mengubah nama:

- `models/Qwen_Qwen3-4B-Instruct-2507-Q6_K.gguf`
- `models/Qwen3-VL-4B-Instruct-Q4_K_M.gguf`
- `models/mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf`

Model tidak dimasukkan ke image. Gunakan `TEXT_MODEL_GPU_LAYERS=0` dan `VISION_MODEL_GPU_LAYERS=0` untuk CPU. Gunakan override `docker-compose.gpu.yml` dan nilai GPU layer yang sesuai untuk CUDA. Verifikasi health endpoint llama.cpp sebelum mengaktifkan backend produksi.
