#!/usr/bin/env python3
"""
§7 실증: "블로킹은 느린 게 아니다" — CPU 시간으로 증명.

같은 1.5초를 두 가지 방식으로 기다린다:
  1) busy-wait  : while True 로 계속 확인 (폴링과 같음)
  2) blocking   : select() 로 커널이 재워줌 (read()가 잠드는 것과 같은 원리)

기다린 '벽시계 시간'은 둘 다 1.5초로 같지만,
'소비한 CPU 시간'은 하늘과 땅 차이여야 한다.
select()는 read()가 데이터를 기다릴 때 커널이 쓰는 바로 그 잠드는 메커니즘이다.
"""
import resource, select, time

WAIT = 1.5  # 초


def cpu_time():
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime  # user + system CPU 시간


def busy_wait():
    start_cpu = cpu_time()
    end = time.monotonic() + WAIT
    while time.monotonic() < end:  # 계속 확인 = CPU 태움
        pass
    return cpu_time() - start_cpu


def blocking_wait():
    start_cpu = cpu_time()
    # 절대 안 열리는 것을 WAIT초 기다림 → 커널이 프로세스를 재움
    select.select([], [], [], WAIT)
    return cpu_time() - start_cpu


print(f"각각 벽시계로 {WAIT}초씩 기다립니다...\n")

busy = busy_wait()
print(f"  busy-wait (while True) : CPU {busy:6.3f}s 소비  🔥")

blk = blocking_wait()
print(f"  blocking  (select)     : CPU {blk:6.3f}s 소비  😴")

print()
if blk < 0.05 < busy:
    ratio = busy / max(blk, 1e-6)
    print(f"→ 같은 1.5초를 기다렸는데 busy-wait가 CPU를 약 {ratio:,.0f}배 더 태웠습니다.")
    print("  '블로킹 read()가 느리다'는 착각인 이유가 이거예요:")
    print("  잠든 프로세스는 CPU를 안 쓰고, 커널이 데이터 올 때 정확히 깨워줍니다.")
else:
    print("→ 환경에 따라 수치가 다를 수 있어요. 그래도 busy 쪽이 훨씬 큽니다.")
