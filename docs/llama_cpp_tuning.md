# Llama.cpp Tuning Guide for HERPA

Optimasi llama-server untuk RAM terbatas dan CPU Ryzen 5 5600H.

## Command Startup yang Direkomendasikan

### Windows (cmd.exe)
```cmd
llama-server.exe ^
  --model app\models\Qwen_Qwen3-4B-Instruct-2507-Q6_K.gguf ^
  --alias Qwen3-4B-Instruct-2507 ^
  --host 127.0.0.1 ^
  --port 8080 ^
  --ctx-size 4096 ^
  --threads 6 ^
  --threads-batch 12 ^
  --parallel 1 ^
  --batch-size 512 ^
  --ubatch-size 128 ^
  --cache-type-k q8_0 ^
  --cache-type-v q8_0 ^
  --cache-prompt ^
  --cache-reuse 256 ^
  --cont-batching ^
  --prio 1 ^
  --prio-batch 1 ^
  --metrics ^
  --slots ^
  --gpu-layers 0 ^
  -fit off
```

### Windows (PowerShell)
```powershell
.\llama-server.exe `
  --model app\models\Qwen_Qwen3-4B-Instruct-2507-Q6_K.gguf `
  --alias Qwen3-4B-Instruct-2507 `
  --host 127.0.0.1 `
  --port 8080 `
  --ctx-size 4096 `
  --threads 6 `
  --threads-batch 12 `
  --parallel 1 `
  --batch-size 512 `
  --ubatch-size 128 `
  --cache-type-k q8_0 `
  --cache-type-v q8_0 `
  --cache-prompt `
  --cache-reuse 256 `
  --cont-batching `
  --prio 1 `
  --prio-batch 1 `
  --metrics `
  --slots `
  --gpu-layers 0 `
  -fit off
```

## Parameter Kunci
- `--cache-prompt`: Mengaktifkan cache system prompt / common prefix caching di server.
- `--ctx-size 4096`: Ukuran context window diselaraskan dengan budget context backend.
- `--threads 6`: Disesuaikan dengan jumlah core CPU fisik.
- `-fit off`: Mencegah alokasi memori berlebih untuk slot tidak terpakai.
- `--cache-type-k q8_0` dan `--cache-type-v q8_0`: Mengompres memori KV-cache ke 8-bit untuk mengurangi jejak RAM tanpa penurunan kualitas.
