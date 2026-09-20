#!/usr/bin/env python3
"""컨테이너 PID 1 의 네 가지 성질을 실제 컨테이너로 확인한다.

A. PID 1 이 끝나면 컨테이너가 끝난다        (nginx 데몬화)
B. PID 1 에는 기본 시그널 동작이 없다        (SIGTERM 무시 -> docker stop 10초)
C. 쉘 래퍼는 시그널을 자식에게 넘기지 않는다 (exec 유무)
D. 고아 프로세스는 PID 1 이 수확해야 한다    (좀비)

Docker 외에 필요한 것은 없다. 표준 라이브러리만 쓴다.
"""

import subprocess
import sys
import time

NGINX = "nginx:1.27-alpine"
ALPINE = "alpine:3.20"
PYTHON = "python:3.12-alpine"

PREFIX = "pid1poc-"
PASSED = 0
FAILED = 0


# --- docker 헬퍼 ---------------------------------------------------------

def sh(args, check=False):
    return subprocess.run(args, capture_output=True, text=True, check=check)


def run_bg(name, image, cmd, init=False):
    """백그라운드 컨테이너를 띄우고 이름을 돌려준다."""
    full = PREFIX + name
    sh(["docker", "rm", "-f", full])
    args = ["docker", "run", "-d", "--name", full]
    if init:
        args.append("--init")
    args += [image] + cmd
    r = sh(args, check=True)
    return full


def inspect(name, fmt):
    return sh(["docker", "inspect", "-f", fmt, name]).stdout.strip()


def status(name):
    return inspect(name, "{{.State.Status}}")


def exit_code(name):
    return int(inspect(name, "{{.State.ExitCode}}") or -1)


def ps_table(name):
    return sh(["docker", "exec", name, "ps", "-eo", "pid,ppid,stat,args"]).stdout


def logs(name):
    r = sh(["docker", "logs", name])
    return r.stdout + r.stderr


def wait_exit(name, timeout):
    """컨테이너가 멈출 때까지 기다리고 걸린 시간을 돌려준다. 안 멈추면 None."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if status(name) == "exited":
            return time.time() - t0
        time.sleep(0.2)
    return None


def timed_stop(name):
    """docker stop 에 걸린 시간을 잰다 (기본 타임아웃 10초)."""
    t0 = time.time()
    sh(["docker", "stop", name])
    return time.time() - t0


def cleanup():
    r = sh(["docker", "ps", "-aq", "--filter", f"name=^{PREFIX}"])
    ids = r.stdout.split()
    if ids:
        sh(["docker", "rm", "-f"] + ids)


# --- 검증 출력 -----------------------------------------------------------

def scenario(title):
    print(f"\n[{time.strftime('%H:%M:%S')}] {title}")


def check(label, actual, expected, ok):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  [PASS] {label}: {actual} (기대: {expected})")
    else:
        FAILED += 1
        print(f"  [FAIL] {label}: {actual} (기대: {expected})")


# --- A. PID 1 이 끝나면 컨테이너가 끝난다 --------------------------------

def scenario_a():
    scenario("시나리오 A. 데몬으로 띄우면 왜 즉시 죽는가")

    # A-1. 기본 nginx.conf 에는 daemon off 가 없다 -> nginx 가 데몬화한다.
    c = run_bg("a-daemon-on", NGINX, ["nginx"])
    elapsed = wait_exit(c, 10)
    check("nginx (데몬 모드) 컨테이너",
          f"{elapsed:.1f}초 만에 exited, exit={exit_code(c)}" if elapsed else "10초 넘게 running",
          "3초 안에 exited, exit=0",
          elapsed is not None and elapsed < 3 and exit_code(c) == 0)

    # A-2. PID 1 이 살아 있는 동안 nginx 는 실제로 떠 있었다.
    #      PID 1(sleep)이 끝나는 순간 nginx 도 같이 사라진다.
    c = run_bg("a-orphan", NGINX, ["sh", "-c", "nginx; sleep 3"])
    time.sleep(1.5)
    table = ps_table(c)
    master = [l for l in table.splitlines() if "master process" in l]
    reparented = bool(master) and master[0].split()[1] == "1"
    check("데몬화된 nginx master 의 부모",
          f"PPID={master[0].split()[1]}" if master else "master 프로세스 없음",
          "PPID=1 (PID 1 에게 재부모화)",
          reparented)

    elapsed = wait_exit(c, 10)
    check("PID 1(sleep) 종료 후 컨테이너",
          f"{elapsed:.1f}초 만에 exited, exit={exit_code(c)}" if elapsed else "10초 넘게 running",
          "5초 안에 exited, exit=0 (nginx 가 살아 있어도 끝난다)",
          elapsed is not None and elapsed < 5 and exit_code(c) == 0)

    graceful = sum(1 for l in logs(c).splitlines()
                   if "gracefully" in l or "exiting" in l)
    check("nginx 의 graceful shutdown 로그",
          f"{graceful}건",
          "0건 (정리할 틈 없이 네임스페이스째 정리된다)",
          graceful == 0)

    # A-3. daemon off 면 nginx 자신이 PID 1 이 되어 계속 산다.
    c = run_bg("a-daemon-off", NGINX, [])  # 이미지 기본 CMD = nginx -g "daemon off;"
    time.sleep(2)
    check("nginx -g 'daemon off;' 컨테이너",
          status(c),
          "running",
          status(c) == "running")


# --- B. PID 1 에는 기본 시그널 동작이 없다 -------------------------------

def scenario_b():
    scenario("시나리오 B. PID 1 은 SIGTERM 을 기본값으로 무시한다")

    # B-1. sleep 은 SIGTERM 핸들러를 달지 않는다. PID 1 이면 커널이 신호를 버린다.
    c = run_bg("b-bare", ALPINE, ["sleep", "1000"])
    time.sleep(1)
    sh(["docker", "kill", "-s", "TERM", c])
    time.sleep(2)
    check("PID 1 = sleep 에 SIGTERM 을 보낸 뒤",
          status(c),
          "running (신호가 버려진다)",
          status(c) == "running")

    took = timed_stop(c)
    check("docker stop 소요 시간 / 종료 코드",
          f"{took:.1f}초, exit={exit_code(c)}",
          "약 10초, exit=137 (SIGKILL)",
          took >= 9 and exit_code(c) == 137)

    # B-2. 같은 sleep 을 PID 1 이 아닌 자리로 내리면 신호가 정상 동작한다.
    c = run_bg("b-init", ALPINE, ["sleep", "1000"], init=True)
    time.sleep(1)
    table = ps_table(c)
    is_init = "docker-init" in table
    check("--init 을 붙였을 때의 PID 1",
          "/sbin/docker-init" if is_init else "docker-init 아님",
          "/sbin/docker-init (tini)",
          is_init)

    sh(["docker", "kill", "-s", "TERM", c])
    elapsed = wait_exit(c, 5)
    check("같은 sleep 에 SIGTERM 을 보낸 뒤",
          f"{elapsed:.1f}초 만에 exited, exit={exit_code(c)}" if elapsed else "5초 넘게 running",
          "즉시 exited, exit=143 (128+15)",
          elapsed is not None and elapsed < 3 and exit_code(c) == 143)


# --- C. 쉘 래퍼는 시그널을 넘기지 않는다 ---------------------------------

WRAPPER_NO_EXEC = 'echo "[wrapper] start"; nginx -g "daemon off;"; echo "[wrapper] done"'
WRAPPER_EXEC = 'echo "[wrapper] start"; exec nginx -g "daemon off;"'


def scenario_c():
    scenario("시나리오 C. 쉘 래퍼 한 겹이 graceful shutdown 을 먹는다")

    # C-1. PID 1 이 sh 다. sh 는 STOPSIGNAL 을 받아도 자식에게 넘기지 않는다.
    c = run_bg("c-noexec", NGINX, ["sh", "-c", WRAPPER_NO_EXEC])
    time.sleep(2)
    first = ps_table(c).splitlines()[1] if len(ps_table(c).splitlines()) > 1 else ""
    check("exec 없는 래퍼의 PID 1",
          first.split(maxsplit=3)[-1][:40] if first else "확인 실패",
          "sh -c ... (nginx 는 자식)",
          first.strip().startswith("1 ") and "sh -c" in first)

    took = timed_stop(c)
    check("docker stop 소요 시간 / 종료 코드",
          f"{took:.1f}초, exit={exit_code(c)}",
          "약 10초, exit=137 (신호가 nginx 까지 못 간다)",
          took >= 9 and exit_code(c) == 137)

    # C-2. exec 를 붙이면 쉘이 nginx 로 교체되어 nginx 가 직접 PID 1 이 된다.
    c = run_bg("c-exec", NGINX, ["sh", "-c", WRAPPER_EXEC])
    time.sleep(2)
    first = ps_table(c).splitlines()[1] if len(ps_table(c).splitlines()) > 1 else ""
    check("exec 를 붙인 래퍼의 PID 1",
          first.split(maxsplit=3)[-1][:40] if first else "확인 실패",
          "nginx: master process",
          "master process" in first)

    took = timed_stop(c)
    check("docker stop 소요 시간 / 종료 코드",
          f"{took:.1f}초, exit={exit_code(c)}",
          "1초 이내, exit=0 (nginx 가 직접 받아 정상 종료)",
          took < 3 and exit_code(c) == 0)


# --- D. 고아는 PID 1 이 수확해야 한다 ------------------------------------

ZOMBIE_CODE = """import os, time
for _ in range(3):
    pid = os.fork()
    if pid == 0:
        if os.fork() == 0:
            os._exit(0)     # 손자: 즉시 종료 -> 좀비
        time.sleep(0.3)
        os._exit(0)         # 자식: 수확하지 않고 종료 -> 손자는 고아가 된다
    os.waitpid(pid, 0)      # PID 1 은 자기 직계 자식만 수확한다
time.sleep(600)
"""


def count_zombies(name):
    return sum(1 for line in ps_table(name).splitlines()[1:]
               if len(line.split()) > 2 and line.split()[2].startswith("Z"))


def scenario_d():
    scenario("시나리오 D. 고아 프로세스를 수확하지 않으면 좀비가 쌓인다")

    c = run_bg("d-bare", PYTHON, ["python", "-c", ZOMBIE_CODE])
    time.sleep(3)
    n = count_zombies(c)
    check("앱이 직접 PID 1 인 컨테이너의 좀비",
          f"{n}개",
          "3개 (아무도 wait 하지 않는다)",
          n == 3)

    c = run_bg("d-init", PYTHON, ["python", "-c", ZOMBIE_CODE], init=True)
    time.sleep(3)
    n = count_zombies(c)
    check("--init (tini) 을 붙인 컨테이너의 좀비",
          f"{n}개",
          "0개 (tini 가 고아를 수확한다)",
          n == 0)


# --- main ----------------------------------------------------------------

def main():
    if sh(["docker", "version", "--format", "{{.Server.Version}}"]).returncode != 0:
        print("Docker 데몬에 접속할 수 없다.")
        return 2

    cleanup()
    try:
        scenario_a()
        scenario_b()
        scenario_c()
        scenario_d()
    finally:
        cleanup()

    total = PASSED + FAILED
    print(f"\n===== {PASSED}/{total} 검증 통과 =====")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
