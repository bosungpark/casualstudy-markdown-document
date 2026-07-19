#!/usr/bin/env python3
"""
§7 실증: read() 시스템 콜이 '블록되었다가 깨어나는' 순간을 dtruss로 관찰.

문제: sudo dtruss -t read_nocancel cat  → SIP가 /bin/cat 추적을 막음
      (dtrace: failed to execute cat: Operation not permitted)

해결: 시스템 보호 바이너리(cat) 대신, 내가 만든 이 스크립트를 추적한다.
      homebrew python은 SIP 보호 대상이 아니라서 dtrace가 붙을 수 있다.

실행:
      sudo dtruss -t read_nocancel python3 read_syscall_demo.py
      (실행되면 아무 키나 치고 Enter)

보이는 것:
      키 치기 전 → read 가 멈춰(블록) 있음
      키 친 순간 → read(0x0, ..., 0x400) = <바이트수> 0   가 찍힘
      = 커널이 잠든 프로세스를 깨워 데이터를 복사해준 증거.
"""
import os

print(f"PID={os.getpid()}  —  이제 stdin을 read()로 기다립니다. 아무거나 치고 Enter:")
data = os.read(0, 1024)          # 진짜 read() 시스템 콜. 데이터 없으면 여기서 블록.
print(f"\nread() 반환: {len(data)} 바이트 수신 → {data!r}")
print("dtruss 출력에서 read_nocancel(...) = 값 이 찍힌 줄을 확인하세요.")
