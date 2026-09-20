# 컨테이너 PID 1 PoC

`docker run` 한 줄짜리 컨테이너 여러 대로, **PID 1이라는 자리 하나가 무엇을 바꾸는지**를 종료 코드와 소요 시간으로 확인한다.

```text
A. nginx 를 데몬으로 기동   →  0.2초 만에 exit 0      (nginx 는 멀쩡히 떠 있었다)
B. PID 1 = sleep 에 TERM    →  무시 / stop 10.2초 137  vs  --init 시 0.1초 143
C. exec 없는 쉘 래퍼        →  stop 10.2초 137         vs  exec 붙이면 0.1초 0
D. 고아 프로세스 3개        →  좀비 3개 잔류           vs  --init 시 0개
```

## 실행

필요한 것은 Docker와 Python 3뿐이다(추가 패키지 없음).

```bash
cd "infra/컨테이너의 PID 1 - 데몬으로 띄우면 왜 즉시 죽고 docker stop은 왜 10초가 걸리는가 (실무 PoC)"
./run.sh
```

약 1분 걸린다. `docker stop`의 기본 타임아웃 10초를 두 번 기다리는 게 대부분이다.

성공하면 이렇게 끝난다.

```text
[17:22:02] 시나리오 A. 데몬으로 띄우면 왜 즉시 죽는가
  [PASS] nginx (데몬 모드) 컨테이너: 0.2초 만에 exited, exit=0 (기대: 3초 안에 exited, exit=0)
  [PASS] 데몬화된 nginx master 의 부모: PPID=1 (기대: PPID=1 (PID 1 에게 재부모화))
  [PASS] PID 1(sleep) 종료 후 컨테이너: 1.7초 만에 exited, exit=0 (기대: 5초 안에 exited, exit=0 ...)
  [PASS] nginx 의 graceful shutdown 로그: 0건 (기대: 0건 (정리할 틈 없이 네임스페이스째 정리된다))
  [PASS] nginx -g 'daemon off;' 컨테이너: running (기대: running)

[17:22:08] 시나리오 B. PID 1 은 SIGTERM 을 기본값으로 무시한다
  [PASS] PID 1 = sleep 에 SIGTERM 을 보낸 뒤: running (기대: running (신호가 버려진다))
  [PASS] docker stop 소요 시간 / 종료 코드: 10.2초, exit=137 (기대: 약 10초, exit=137 (SIGKILL))
  [PASS] --init 을 붙였을 때의 PID 1: /sbin/docker-init (기대: /sbin/docker-init (tini))
  [PASS] 같은 sleep 에 SIGTERM 을 보낸 뒤: 0.1초 만에 exited, exit=143 (기대: 즉시 exited, exit=143 (128+15))

[17:22:23] 시나리오 C. 쉘 래퍼 한 겹이 graceful shutdown 을 먹는다
  [PASS] exec 없는 래퍼의 PID 1: sh -c echo "[wrapper] start"; nginx -g " (기대: sh -c ... (nginx 는 자식))
  [PASS] docker stop 소요 시간 / 종료 코드: 10.2초, exit=137 (기대: 약 10초, exit=137 ...)
  [PASS] exec 를 붙인 래퍼의 PID 1: nginx: master process nginx -g daemon of (기대: nginx: master process)
  [PASS] docker stop 소요 시간 / 종료 코드: 0.1초, exit=0 (기대: 1초 이내, exit=0 ...)

[17:22:39] 시나리오 D. 고아 프로세스를 수확하지 않으면 좀비가 쌓인다
  [PASS] 앱이 직접 PID 1 인 컨테이너의 좀비: 3개 (기대: 3개 (아무도 wait 하지 않는다))
  [PASS] --init (tini) 을 붙인 컨테이너의 좀비: 0개 (기대: 0개 (tini 가 고아를 수확한다))

===== 15/15 검증 통과 =====
```

## 구성

컨테이너는 검증 중에만 뜨고 바로 지워진다. 이름은 전부 `pid1poc-` 접두사를 쓴다.

| 이미지 | 쓰는 곳 | 이유 |
| --- | --- | --- |
| `nginx:1.27-alpine` | 시나리오 A, C | 기본 conf에 `daemon` 지시어가 없어 데몬화한다. `STOPSIGNAL`이 `SIGQUIT`이다 |
| `alpine:3.20` | 시나리오 B | `sleep`은 시그널 핸들러를 달지 않는 가장 단순한 표본이다 |
| `python:3.12-alpine` | 시나리오 D | `os.fork()`로 고아를 결정적으로 만들 수 있다 |

측정값은 두 개뿐이다. **`docker stop`에 걸린 시간**과 **종료 코드**다.

```text
exit 0    정상 종료
exit 143  128 + 15(SIGTERM) → 시그널이 닿았고 앱이 스스로 끝냈다
exit 137  128 + 9(SIGKILL)  → 시그널이 안 닿아 타임아웃 후 강제 종료됐다
```

## 직접 확인해 보기

```bash
# A. 데몬화하면 exit 0 으로 끝난다
docker run --rm nginx:1.27-alpine nginx; echo "exit=$?"

# A. PID 1 이 살아 있는 동안 nginx 가 PID 1 에게 입양돼 있는 모습
docker run --rm nginx:1.27-alpine sh -c 'nginx; sleep 1; ps -eo pid,ppid,stat,args; true'

# B. PID 1 은 TERM 을 무시한다
docker run -d --name t1 alpine:3.20 sleep 1000
docker kill -s TERM t1 && sleep 2 && docker ps --filter name=t1   # 아직 살아 있다
time docker stop t1                                               # 10초 + exit 137
docker rm -f t1

# C. exec 한 단어의 차이
docker run -d --name t2 nginx:1.27-alpine sh -c 'echo hi; nginx -g "daemon off;"; true'
docker run -d --name t3 nginx:1.27-alpine sh -c 'echo hi; exec nginx -g "daemon off;"'
docker exec t2 ps -eo pid,args | head -3     # PID 1 = sh
docker exec t3 ps -eo pid,args | head -3     # PID 1 = nginx master
time docker stop t2                          # 10초
time docker stop t3                          # 즉시
docker rm -f t2 t3

# D. 좀비 세기
docker exec <컨테이너> ps -eo stat | grep -c Z
```

## 정리

```bash
./run.sh down
```
