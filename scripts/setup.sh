#!/usr/bin/env sh
set -eu
[ -f .env ] || cp .env.example .env
python -m pip install -e '.[dev]'
printf '\nSetup selesai. Isi .env, letakkan GGUF di models/, lalu jalankan docker compose.\n'
