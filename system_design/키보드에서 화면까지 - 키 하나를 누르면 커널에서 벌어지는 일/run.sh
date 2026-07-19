#!/usr/bin/env bash
# 키보드에서 화면까지 — PoC 실행 메뉴
# 사용법:  bash run.sh
set -euo pipefail
cd "$(dirname "$0")"

PY="$(command -v python3 || true)"
[ -z "$PY" ] && { echo "python3가 필요해요."; exit 1; }

echo "============================================"
echo " 키보드에서 화면까지 — PoC (macOS)"
echo "============================================"
echo " 1) CPU: 블로킹 vs busy-wait   (§7, 바로 실행)"
echo " 2) make/break 키 이벤트        (§3, pynput·권한 필요)"
echo " 3) read() 시스템 콜 추적        (§7, sudo dtruss)"
echo " q) 종료"
echo "--------------------------------------------"
read -r -p "선택> " choice

case "$choice" in
  1)
    "$PY" cpu_blocking_vs_busywait.py
    ;;
  2)
    if ! "$PY" -c "import pynput" 2>/dev/null; then
      echo "pynput 설치 중..."
      "$PY" -m pip install --quiet pynput
    fi
    echo "→ 첫 실행 시 macOS '입력 모니터링' 권한을 물어봐요. 터미널을 허용하고 다시 실행하세요."
    "$PY" makebreak.py
    ;;
  3)
    echo "→ SIP 때문에 /bin/cat 은 추적 못 해요. 대신 내 스크립트를 추적합니다:"
    echo "   sudo dtruss -t read_nocancel python3 read_syscall_demo.py"
    echo "   (실행되면 아무 키나 치고 Enter)"
    sudo dtruss -t read_nocancel "$PY" read_syscall_demo.py
    ;;
  q|Q)
    echo "bye"
    ;;
  *)
    echo "1, 2, 3, q 중에서 골라주세요."
    ;;
esac
