#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

case "${1:-}" in
  down)
    ids=$(docker ps -aq --filter 'name=^pid1poc-')
    [ -n "$ids" ] && docker rm -f $ids
    exit 0
    ;;
esac

echo "==> 이미지 준비 (nginx:1.27-alpine, alpine:3.20, python:3.12-alpine)"
for img in nginx:1.27-alpine alpine:3.20 python:3.12-alpine; do
  docker image inspect "$img" >/dev/null 2>&1 || docker pull -q "$img"
done

echo "==> 검증 시작 (약 1분 소요: docker stop 10초 타임아웃을 두 번 기다린다)"
python3 verify.py
