# 컨테이너의 PID 1 - 데몬으로 띄우면 왜 즉시 죽고, docker stop은 왜 10초가 걸리는가

## 출처

- **아티클**: Docker demons: PID-1, orphans, zombies, and signals
- **저자/출처**: Michael Snoyman, FP Complete 블로그 (현재 FP Block Academy로 이전)
- **링크**: https://academy.fpblock.com/blog/2016/10/docker-demons-pid1-orphans-zombies-signals/

> 원문은 2016년 글이고, 예제는 저자가 만든 `fpco/pid1` 이미지를 쓴다. 이 문서는 **주장만 원문에서 가져오고**, 확인은 Docker 27.4.0 / `nginx:1.27-alpine` / `alpine:3.20` / `python:3.12-alpine`에서 다시 했다. 원문의 `pid1` 자리는 Docker에 내장된 `--init`(tini)로 대체했다.
>
> 원문에 없는 **nginx 데몬화 사례**와 **쉘 래퍼의 시그널 차단**은 원문 주장을 실무 상황에 적용해 본 것이라, PoC 절에 표시해 두었다.
>
> 범위는 PID 1의 커널 예외 처리 하나다.

---

## AI 요약

### 0. 컨테이너는 프로세스 집합이 아니라 PID 1 하나다

컨테이너를 "격리된 작은 VM"으로 생각하면 사고가 난다. VM에서는 부팅 스크립트가 데몬을 띄우고 끝나는 게 정상이다. 컨테이너에서는 **그 스크립트가 컨테이너 자체**다.

```text
VM         : init(systemd) ─┬─ nginx          스크립트가 끝나도 시스템은 산다
                            └─ sshd

컨테이너   : PID 1 = 내가 띄운 그 명령어       PID 1이 끝나면 전부 끝난다
```

여기서 한 걸음 더 들어간다. 컨테이너의 PID 1은 "그냥 첫 번째 프로세스"가 아니라 **커널이 특별 취급하는 자리**다. 일반 앱을 그 자리에 앉히면 제목의 두 증상이 나온다.

**데몬으로 띄우면 왜 즉시 죽는가.** 데몬화란 fork해서 자식을 백그라운드에 남기고 부모는 끝나는 동작이다. 컨테이너에서는 그 부모가 PID 1이다.

```text
PID 1 = nginx          ← 내가 띄운 명령
  ↓ fork
PID 8 = nginx master   ← 진짜 서버는 여기로 넘어간다
  ↓
PID 1 이 "데몬화 성공"하고 exit(0)
  ↓
커널: PID 1이 없으니 이 네임스페이스를 정리한다 → PID 8도 같이 사라진다
```

죽은 게 아니라 **할 일을 마치고 정상 종료한 것**이고, 커널이 그 뒤를 따라 나머지를 쓸어버린 것이다. 그래서 종료 코드가 0이다.

**`docker stop`은 왜 10초가 걸리는가.** 이번엔 반대로 PID 1이 안 죽는다. 보통 프로세스는 SIGTERM 핸들러가 없어도 커널이 대신 죽여 주지만, PID 1은 **핸들러를 명시적으로 달지 않은 신호를 커널이 그냥 버린다.**

```text
docker stop
  → STOPSIGNAL → PID 1 (핸들러 없음) → 커널이 버린다
  → 아무 일도 일어나지 않는다
  → 기본 유예 10초 경과
  → SIGKILL (막을 수 없다) → exit 137
```

10초는 앱이 느려서가 아니라 **Docker의 기본 유예 시간을 끝까지 기다린 값**이다.

둘은 증상이 반대지만 원인이 같다. PID 1이라는 자리에 그 역할을 모르는 프로세스를 앉혔다는 것.

| 제목의 질문 | 한 줄 답 | 원리 | 실측 |
| --- | --- | --- | --- |
| 데몬으로 띄우면 왜 즉시 죽는가 | 부모가 fork 후 종료하는데, 그 부모가 PID 1이라 네임스페이스 전체가 정리된다 | 4절 | PoC A |
| `docker stop`은 왜 10초가 걸리는가 | PID 1은 핸들러 없는 신호를 커널이 버린다. 10초는 Docker의 기본 유예 시간 | 1~2절 | PoC B·C |
| (덤) 좀비는 왜 쌓이는가 | PID 1이 입양한 고아를 수확하지 않는다 | 3절 | PoC D |

> 원문 소제목과의 대응: 1~2절 = Sending TERM signal, 3절 = Reaping orphans, 4절 = Surviving children.

### 1. 커널이 PID 1에 거는 두 가지 예외

**예외 1 - 기본 동작(default disposition)이 없다.**

보통 프로세스는 SIGTERM을 받으면 핸들러가 없어도 커널이 죽여 준다. PID 1은 다르다. 원문 표현대로, 커널은 PID 1에 대해 "핸들러를 명시적으로 설치하지 않은 신호는 **그냥 버린다**". 원래 이 예외는 호스트의 진짜 init(systemd)이 실수로 죽어 커널 패닉이 나는 걸 막으려는 보호 장치인데, PID 네임스페이스마다 적용되므로 컨테이너의 PID 1도 똑같이 보호받는다.

**예외 2 - 고아를 입양한다.**

부모가 먼저 죽은 프로세스는 PID 1의 자식으로 재부모화(reparenting)된다. 커널은 PID 1이 이 입양아들의 종료 상태를 `waitpid()`로 거둬 줄 거라고 기대한다. 이렇게 거둬 가는 일을 **수확(reaping)**이라고 부른다. 거두지 않으면 좀비가 남는데, 그건 3절에서 다시 본다.

```text
             보통 프로세스        PID 1
SIGTERM  →   커널이 죽여 준다      핸들러 없으면 무시된다
고아      →   받을 일이 없다        전부 나에게 온다 (수확 책임)
```

일반 애플리케이션은 이 두 가지 중 어느 것도 하도록 만들어지지 않았다. 그래서 문제가 생긴다.

### 2. SIGTERM을 무시하는 게 정상 동작이다

원문의 가장 단순한 재현이다.

```bash
docker run --rm --name sleeper ubuntu:16.04 sleep 100
docker kill -s TERM sleeper      # 다른 터미널에서
```

`sleep`은 죽지 않는다. `sleep`은 SIGTERM 핸들러를 달지 않고, PID 1이므로 커널이 신호를 버리기 때문이다.

해결책은 앱을 PID 1 자리에서 **내리는** 것이다. 작은 init 프로세스를 PID 1에 앉히고, 앱은 그 자식으로 실행한다. 원문은 저자가 만든 `pid1`을 쓰지만, 지금은 Docker에 `--init` 플래그로 tini가 내장돼 있다. 아래부터는 전부 `--init` 기준이다.

```text
docker run alpine sleep 1000
  PID 1  sleep 1000                 ← 커널 보호 대상. TERM 무시

docker run --init alpine sleep 1000
  PID 1  /sbin/docker-init          ← init이 보호 대상
  PID 7    └─ sleep 1000            ← 평범한 PID. TERM 받으면 죽는다
```

동작 순서는 이렇다.

1. 컨테이너가 `docker-init <명령어>`로 뜬다
2. init이 PID 1이 되고, fork/exec로 실제 명령어를 자식으로 띄운다
3. init이 받은 시그널을 자식에게 그대로 전달한다
4. 자식이 시그널 15로 죽으면 init은 **143(128+15)**으로 종료한다
5. 컨테이너가 끝난다

`128 + 시그널 번호`라는 관례 덕분에, 종료 코드만 봐도 "무엇에 죽었는지"를 읽을 수 있다. 143이면 SIGTERM으로 정상 종료, **137이면 SIGKILL로 강제 종료**다.

### 3. 고아와 좀비

용어를 먼저 구분한다.

- **좀비(zombie)**: 종료했지만 부모가 `waitpid()`로 수확하지 않아 프로세스 테이블에 남은 항목. `ps`에 `<defunct>` / STAT `Z`로 보인다. 메모리는 해제됐지만 **PID 슬롯을 계속 점유**한다.
- **고아(orphan)**: 부모보다 오래 산 자식. 커널이 PID 1에게 재부모화한다.

둘이 만나면 문제가 된다. 앱이 자식을 띄우고 그 자식이 손자를 남긴 채 죽으면, 손자의 종료 상태를 수거할 책임이 PID 1에게 넘어온다. PID 1이 평범한 앱이면 그런 루프가 없으므로 좀비가 그대로 쌓인다. 원문의 `orphans` 예제가 보여 주는 게 정확히 이것이다.

```text
13 ?  00:00:00 echo <defunct>
14 ?  00:00:00 echo <defunct>
```

좀비 하나는 무해하다. 문제는 **장수 컨테이너**다. 원문 표현대로 "쌓이면 새 프로세스를 못 만드는" 상태가 되고, 그게 배포 며칠 뒤에 터진다.

`--init`을 붙이면 tini가 PID 1이 되어 재부모화된 고아를 계속 수확하므로 좀비가 남지 않는다.

### 4. PID 1이 먼저 끝나면 남은 자식은 정리할 틈이 없다

원문 "Surviving children" 절이다. PID 1이 종료되면 커널은 그 PID 네임스페이스에 남은 프로세스를 **강제로 정리**한다. 정리 기회를 주지 않는다.

```text
PID 1 종료
   ↓
커널: 네임스페이스 내 잔여 프로세스 강제 종료
   ↓
남은 프로세스: 종료 훅/플러시/graceful shutdown 없음
```

init 프로세스는 자기가 끝나기 전에 남은 자식에게 먼저 SIGTERM을 보내고, 유예 시간을 준 뒤 SIGKILL 한다. 그래서 같은 상황에서도 자식들이 "Got a TERM"을 찍고 정리할 수 있다.

**이 절이 실무에서 가장 자주 부딪히는 지점이다.** 데몬화하는 프로세스를 CMD로 쓰면 정확히 이 경로를 탄다(→ PoC 시나리오 A).

### 5. `docker run`에 보낸 시그널 ≠ 컨테이너에 보낸 시그널

`docker run`은 컨테이너가 아니다. 터미널 → `docker run` 프로세스 → Docker 데몬 → 컨테이너 PID 1로 이어지는 **프록시**다.

- SIGINT/SIGTERM: `docker run`이 잡아서 데몬을 통해 컨테이너로 전달한다
- **SIGKILL: 잡을 수 없다.** `docker run`만 죽고 **컨테이너는 계속 산다**

```bash
docker run --rm alpine:3.20 sleep 60 &
kill -KILL $!        # docker run 프로세스만 죽는다
docker ps            # 컨테이너는 여전히 떠 있다
```

결론은 단순하다. 컨테이너를 죽이려면 `docker kill`을 쓴다.

### 6. Dockerfile의 shell form vs exec form

같은 명령을 어떻게 쓰느냐에 따라 **PID 1 자리에 앉는 프로세스가 달라진다.**

```dockerfile
ENTRYPOINT /sbin/pid1          # shell form → 도커가 /bin/sh -c "/sbin/pid1" 로 감싼다
ENTRYPOINT ["/sbin/pid1"]      # exec form  → 쓴 그대로 실행한다
```

**문제 1 - 인자가 사라진다.**

shell form은 명령 전체를 문자열 하나로 박아 넣기 때문에, `docker run` 뒤에 붙인 인자를 이어 붙일 자리가 없다.

```bash
docker run --rm test ps
# shell form : pid1: No arguments provided    ← ps가 전달되지 않는다
# exec form  : PID  TTY  TIME  CMD ...        ← ps가 인자로 넘어간다
```

**문제 2 - PID 1이 내 앱이 아니라 쉘이 된다.** 이쪽이 더 아프다.

```text
shell form                          exec form
PID 1  /bin/sh -c "node app.js"     PID 1  node app.js
PID 7    └─ node app.js
```

쉘은 자식을 띄워 놓고 끝나기를 기다릴 뿐, 자기가 받은 신호를 자식에게 넘겨주지 않는다. 게다가 그 쉘은 PID 1이라 2절의 규칙을 그대로 적용받는다 - 핸들러가 없는 신호는 커널이 버린다. 결국 앱은 종료 신호를 구경도 못 하고 10초 뒤 SIGKILL로 잘린다. 실제 측정값은 PoC 시나리오 C에 있다.

다만 쉘이 항상 남아 있는 건 아니다. `sh -c "node app.js"`처럼 단순한 명령 하나뿐이면 쉘이 `exec`로 자기 자신을 그 명령으로 바꿔치기하고 사라지기도 한다. 하지만 `&&`, 파이프, 리다이렉션, 변수 확장이 하나라도 끼면 쉘은 PID 1에 그대로 남는다. **될 때도 있고 안 될 때도 있다는 게 제일 나쁘다.** exec form(JSON 배열)으로 쓰면 이 변수 자체가 없어진다.

---

## PoC - 직접 띄워서 확인한 것

Docker와 Python 3만 있으면 된다. 추가 패키지도, compose도 없다.

```bash
cd "infra/컨테이너의 PID 1 - 데몬으로 띄우면 왜 즉시 죽고 docker stop은 왜 10초가 걸리는가 (실무 PoC)"
./run.sh
```

약 1분 걸린다(`docker stop`의 10초 타임아웃을 두 번 기다린다). 전부 `docker run` 한 줄짜리 시나리오다.

| 시나리오 | 확인하는 것 | 요약 절 |
| --- | --- | --- |
| A | 데몬화하면 컨테이너가 즉시 끝난다 | 4절 |
| B | PID 1은 SIGTERM을 무시한다 | 2절 |
| C | 쉘 래퍼 한 겹이 종료 신호를 먹는다 | 2절 + 6절 (내 조합) |
| D | 고아를 수확하지 않으면 좀비가 쌓인다 | 3절 |

### A. nginx를 데몬으로 띄우면 왜 즉시 죽는가

`nginx:1.27-alpine`의 기본 CMD는 `nginx -g "daemon off;"`다. 여기서 `-g` 옵션을 떼고 그냥 `nginx`로 실행하면, `/etc/nginx/nginx.conf`에 `daemon` 지시어가 없으므로 기본값(`daemon on`)으로 데몬화한다.

```bash
docker run -d nginx:1.27-alpine nginx
```

```text
[PASS] nginx (데몬 모드) 컨테이너: 0.2초 만에 exited, exit=0
```

**0.2초 만에, 그것도 종료 코드 0으로 끝난다.** 순서를 풀면 이렇다.

```text
t=0     PID 1 = nginx (foreground)
          ↓ fork
        PID 8 = nginx master (데몬)  ← 진짜 서버는 여기
          ↓
        PID 1 은 할 일을 마치고 exit(0)      ← "데몬화 성공"
t=0.2   PID 1 부재 → 커널이 네임스페이스 정리 → PID 8도 같이 사라진다
        Docker: 컨테이너 exited (0)
```

PID 1이 죽는 그 순간 nginx가 **정상 동작 중이었다**는 걸 따로 확인했다. PID 1을 `sleep 3`으로 잡아 두고 그 사이를 들여다본다.

```bash
docker run -d nginx:1.27-alpine sh -c 'nginx; sleep 3'
docker exec <cid> ps -eo pid,ppid,stat,args
```

```text
PID   PPID  STAT COMMAND
    1     0 S    sleep 3
    8     1 S    nginx: master process nginx     ← 부모가 죽어 PID 1에게 입양됐다
    9     8 S    nginx: worker process
```

```text
[PASS] 데몬화된 nginx master 의 부모: PPID=1
[PASS] PID 1(sleep) 종료 후 컨테이너: 1.7초 만에 exited, exit=0
[PASS] nginx 의 graceful shutdown 로그: 0건
```

nginx master는 워커까지 띄우고 멀쩡히 돌고 있었는데, PID 1(`sleep`)이 끝나자 같이 사라졌다. 로그에 graceful shutdown 흔적이 **0건**이라는 게 원문 4절 그대로다. **정리할 틈을 주지 않는다.**

반대로 기본 CMD(`daemon off`)면 nginx master 자신이 PID 1이 되어 계속 산다.

```text
[PASS] nginx -g 'daemon off;' 컨테이너: running
```

> 여기서 제일 고약한 건 컨테이너가 죽는 것 자체가 아니라 **exit 0**이다. 실패로 안 보인다.

### B. PID 1은 SIGTERM을 기본값으로 무시한다

```bash
docker run -d alpine:3.20 sleep 1000
docker kill -s TERM <cid>
```

```text
[PASS] PID 1 = sleep 에 SIGTERM 을 보낸 뒤: running
[PASS] docker stop 소요 시간 / 종료 코드: 10.2초, exit=137
```

SIGTERM은 버려진다. `docker stop`은 기본 10초를 기다렸다가 SIGKILL을 보내고, 컨테이너는 137(128+9)로 끝난다.

`--init` 하나를 붙이면 똑같은 `sleep`이 즉시 죽는다.

```text
[PASS] --init 을 붙였을 때의 PID 1: /sbin/docker-init
[PASS] 같은 sleep 에 SIGTERM 을 보낸 뒤: 0.1초 만에 exited, exit=143
```

**바뀐 건 코드가 아니라 `sleep`이 앉은 자리뿐이다.** 10.2초 / 137 → 0.1초 / 143.

### C. 쉘 래퍼 한 겹이 graceful shutdown을 먹는다

원문 2절과 6절을 겹쳐서 만든 내 실험이다. 흔한 "시작 스크립트" 패턴을 재현한다.

```bash
# exec 없음 → PID 1은 sh, nginx는 그 자식
docker run -d nginx:1.27-alpine sh -c 'echo "[wrapper] start"; nginx -g "daemon off;"; echo done'
```

```text
$ docker exec <cid> ps -eo pid,args
PID   COMMAND
    1 sh -c echo "[wrapper] start"; nginx -g "daemon off;"; echo done
    7 nginx: master process nginx -g daemon off;
```

```text
[PASS] exec 없는 래퍼의 PID 1: sh -c echo "[wrapper] start"; nginx -g "
[PASS] docker stop 소요 시간 / 종료 코드: 10.2초, exit=137
```

nginx는 SIGQUIT(이 이미지의 `STOPSIGNAL`) 핸들러를 제대로 갖고 있다. 그런데도 10초가 걸린다. 신호가 **nginx까지 도달하지 못하기** 때문이다.

```text
docker stop
   → SIGQUIT → PID 1 = sh        sh에는 SIGQUIT 핸들러가 없다
                                 PID 1이므로 커널이 신호를 버린다
   → nginx는 아무것도 듣지 못한다
   → 10초 뒤 SIGKILL → 137
```

`exec` 한 단어를 붙이면 쉘이 자기 자신을 nginx로 **교체**하므로 nginx가 직접 PID 1이 된다.

```bash
docker run -d nginx:1.27-alpine sh -c 'echo "[wrapper] start"; exec nginx -g "daemon off;"'
```

```text
[PASS] exec 를 붙인 래퍼의 PID 1: nginx: master process nginx -g daemon of
[PASS] docker stop 소요 시간 / 종료 코드: 0.1초, exit=0
```

10.2초 / 137 → **0.1초 / 0**. 공식 nginx 이미지의 `/docker-entrypoint.sh`가 마지막 줄을 `exec "$@"`로 끝내는 이유가 이것이다.

### D. 고아를 수확하지 않으면 좀비가 쌓인다

손자를 남기고 죽는 자식을 세 번 만든다. PID 1(파이썬)은 자기 직계 자식만 수확한다.

```python
for _ in range(3):
    pid = os.fork()
    if pid == 0:
        if os.fork() == 0:
            os._exit(0)     # 손자: 즉시 종료 → 좀비
        time.sleep(0.3)
        os._exit(0)         # 자식: 수확하지 않고 종료 → 손자는 고아
    os.waitpid(pid, 0)      # PID 1은 직계 자식만 수확한다
time.sleep(600)
```

```text
PID   PPID  STAT COMMAND
    1     0 S    python -c ...
    8     1 Z    [python]        ← 재부모화된 뒤 아무도 wait 하지 않는다
   10     1 Z    [python]
   12     1 Z    [python]
```

```text
[PASS] 앱이 직접 PID 1 인 컨테이너의 좀비: 3개
[PASS] --init (tini) 을 붙인 컨테이너의 좀비: 0개
```

### 전체 결과

```text
===== 15/15 검증 통과 =====
```

---

## 내가 얻은 인사이트

### 운영 - 증상에서 원인으로 역추적하기

1. **exit 0인데 컨테이너가 죽었다면 데몬화를 의심한다**
   - A 시나리오가 보여 주듯 데몬화 실패는 exit 0으로 나온다. "성공적으로 백그라운드로 갔다"가 PID 1의 정상 종료이기 때문이다.
   - 오케스트레이터 입장에서는 성공한 종료라 `restartPolicy: Always`면 조용히 재시작을 반복한다. 로그에 에러가 없는 CrashLoopBackOff가 이 모양이다.
   - 점검은 `docker inspect -f '{{.Config.Cmd}}'` 한 줄이면 된다. 데몬화 옵션이 붙어 있는지, 포그라운드 플래그(`daemon off`, `-F`, `--foreground`, `-DFOREGROUND`)가 빠졌는지 본다.

2. **`docker stop`이 매번 정확히 10초라면 그건 타임아웃이지 종료 시간이 아니다**
   - 10초는 우연이 아니라 Docker의 기본 grace period다. "10초 + exit 137" 조합은 **신호가 앱에 닿지 않았다**는 신호로 읽는다.
   - 앱이 느린 게 아니므로 `docker stop -t 60`이나 쿠버네티스 `terminationGracePeriodSeconds`를 늘려도 60초로 늘어날 뿐 해결되지 않는다. 고쳐야 할 건 PID 1의 정체다.
   - 반대로 137이 아니라 143으로 끝나면 시그널 경로는 정상이라는 뜻이다. 종료 코드가 진단의 1차 지표다.

3. **배포 며칠 뒤에 터지는 장애는 3절을 의심한다**
   - 좀비는 메모리를 안 먹어서 모니터링에 잘 안 잡히는데 PID 슬롯을 점유한다. 짧게 도는 배치 컨테이너에서는 평생 안 보이다가, 장수 컨테이너에서 어느 날 fork 실패로 나타난다.
   - 앱이 셸 아웃(subprocess, 사이드카 헬퍼, `git`/`ffmpeg` 호출)을 자주 하면 확인해 볼 값이 있다. `docker exec <c> ps -eo stat | grep -c Z` 한 줄이면 끝난다.

### 설계 - 이미지를 만들 때

4. **선택지는 세 개뿐이고, 답은 상황에 따라 다르다**

   | 선택 | 조건 | 비용 |
   | --- | --- | --- |
   | 앱이 직접 PID 1 | 앱이 SIGTERM 핸들러를 갖고, 자식을 안 만든다 | 0 (가장 깔끔) |
   | `exec`로 교체 | 래퍼 스크립트가 꼭 필요할 때 | 단어 하나 |
   | init 프로세스 | 소스를 못 고치거나 자식을 만들 때 | 바이너리 하나 (Docker 번들 tini 0.19.0 = 601KB) |

   - 원문은 "특별한 이유가 없으면 최소 init을 써라"는 쪽이다. 나는 순서를 반대로 둔다. **앱이 스스로 할 수 있으면 자리를 그대로 주고, 못 할 때만 init을 넣는다.** 레이어가 하나 줄면 디버깅할 것도 하나 준다.
   - 단, `--init`은 `docker run` 플래그라 쿠버네티스에서는 쓸 수 없다. 쿠버네티스까지 갈 이미지면 **`ENTRYPOINT ["/sbin/tini", "--"]`로 이미지 안에 박아 두는 쪽**이 이식성이 좋다.

5. **`exec`는 스타일이 아니라 기능이다**
   - 래퍼 스크립트에서 `exec`를 빠뜨리면 프로세스가 하나 더 생기는 게 아니라 **종료 경로가 끊어진다.** C 시나리오의 10.2초/137이 그 값이다.
   - 반대 함정도 있다. 쉘(ash/dash)은 `sh -c '단일 명령'`을 자동으로 exec 최적화하기 때문에, 래퍼가 한 줄일 때는 `exec` 없이도 우연히 잘 돈다. 로그 한 줄이 앞에 붙는 순간 깨진다. **우연히 도는 상태에 의존하지 않으려면 명시적으로 `exec`를 쓴다.**
   - Dockerfile에서는 shell form(`CMD nginx ...`)이 같은 문제를 만든다. exec form(`CMD ["nginx", "-g", "daemon off;"]`)을 기본으로 둔다.

6. **PID 1의 진짜 계약은 "graceful shutdown을 누가 책임지는가"다**
   - 지금까지의 증상들은 표면이고, 공통 원인은 하나다. **PID 1은 컨테이너의 종료 담당자다.** 그 자리에 종료를 모르는 프로세스를 앉히면, 연결 드레이닝도 버퍼 플러시도 트랜잭션 롤백도 전부 SIGKILL에 잘린다.
   - A 시나리오의 "graceful shutdown 로그 0건"이 그 대가를 직접 보여 준다. 무상태 웹 서버면 재시도로 덮이지만, 쓰기 중인 큐 컨슈머나 배치 잡이면 데이터가 남는다.
   - 그래서 새 이미지를 만들 때 확인할 건 한 줄이다. **`docker stop`이 1초 안에 끝나고 종료 코드가 0 또는 143인가.** 10초와 137이 나오면 아직 안 끝난 것이다.
