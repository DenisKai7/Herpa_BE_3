$ErrorActionPreference = "Stop"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m pip install -e ".[dev]"
Write-Host "Setup selesai. Isi .env, letakkan GGUF di models/, lalu jalankan docker compose."
