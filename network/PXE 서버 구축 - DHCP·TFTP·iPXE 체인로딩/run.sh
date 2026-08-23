#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$script_dir"

BUILDX_NO_DEFAULT_ATTESTATIONS=1 docker compose build pxe-server pxe-client
docker compose up -d --wait pxe-server
docker compose run --rm pxe-client

echo
echo "PXE 서버는 Docker 격리 네트워크 안에서 실행 중입니다."
echo "로그: docker compose logs -f pxe-server"
echo "종료: cd '$script_dir' && docker compose down"
