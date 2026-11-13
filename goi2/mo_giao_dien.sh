#!/usr/bin/env bash
set -e
xla_app_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
exec bash "$xla_app_dir/mo_flutter.sh"
