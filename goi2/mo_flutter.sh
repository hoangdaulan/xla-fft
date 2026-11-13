#!/usr/bin/env bash
set -e
xla_flutter_root="$(cd -- "$(dirname -- "$0")" && pwd)"
export XLA_ROOT="$xla_flutter_root"
export XLA_PYTHON="${XLA_PYTHON:-$xla_flutter_root/.venv/bin/python}"
xla_flutter_binary="$xla_flutter_root/flutter_app/build/linux/x64/release/bundle/fourier_studio"
if [ ! -x "$XLA_PYTHON" ]; then
    printf '%s\n' 'Chưa có Python môi trường riêng. Tạo .venv và cài requirements.txt trong goi2 trước.' >&2
    exit 1
fi
if [ ! -x "$xla_flutter_binary" ]; then
    cd "$xla_flutter_root/flutter_app"
    flutter pub get
    flutter build linux --release
fi
cd "$xla_flutter_root"
exec "$xla_flutter_binary"
