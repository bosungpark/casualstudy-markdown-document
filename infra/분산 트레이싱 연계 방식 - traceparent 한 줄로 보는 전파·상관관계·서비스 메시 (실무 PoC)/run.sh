#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

# Stable image metadata prevents needless container recreation on repeat runs.
BUILDX_NO_DEFAULT_ATTESTATIONS=1 docker compose --profile build build app-image
docker compose up -d
python3 verify.py "$@"

echo
echo "Jaeger UI는 http://localhost:16686 에 남겨두었습니다."
echo "종료: cd $SCRIPT_DIR && docker compose down"
