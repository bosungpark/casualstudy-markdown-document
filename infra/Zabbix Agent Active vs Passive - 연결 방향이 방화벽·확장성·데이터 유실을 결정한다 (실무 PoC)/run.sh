#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

case "${1:-}" in
  down)
    docker compose down -v
    exit 0
    ;;
esac

echo "==> 스택 기동 (postgres + zabbix server + frontend + agent 4대)"
docker compose up -d

echo "==> 검증 시작 (약 6분 소요: 기준 수집 45초 + 단절 시나리오 2회)"
python3 verify.py
status=$?

echo
echo "프론트엔드: http://localhost:8080  (Admin / zabbix)"
echo "정리하려면: ./run.sh down"
exit $status
