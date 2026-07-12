# 리눅스 inode - 파일의 정체와 inode에 저장되지 않는 것들

## 출처
- **아티클/논문**: Linux File System Architecture: A Deep Dive into VFS, Inodes, and Storage
- **저자/출처**: kanywst (DEV Community)
- **링크**: https://dev.to/kanywst/linux-file-system-architecture-a-deep-dive-into-vfs-inodes-and-storage-1n9

---

## AI 요약

### 1. inode란?

리눅스는 파일을 **파일명이 아니라 inode 번호로 식별한다.** 파일명은 인간의 편의를 위한 라벨일 뿐이고, 커널 입장에서 파일의 실체는 inode다.

```bash
echo "dummy" > example.txt
stat example.txt
```

```
File: example.txt
Size: 6           Blocks: 8          IO Block: 4096   regular file
Device: f5h/245d  Inode: 1714604     Links: 1
```

| inode에 저장되는 것 | 설명 |
|---|---|
| 파일 타입 | 일반 파일, 디렉토리, 심볼릭 링크, 디바이스 등 |
| 크기 / 블록 수 | 파일 크기(바이트), 할당된 디스크 블록 |
| 소유자 / 권한 | UID, GID, rwx 퍼미션 |
| 타임스탬프 | atime(접근), mtime(수정), ctime(메타데이터 변경) |
| 링크 카운트 | 이 inode를 가리키는 디렉토리 엔트리(하드링크) 수 |
| 데이터 블록 포인터 | 실제 데이터가 저장된 디스크 블록의 위치 |

### 2. inode에 저장되지 **않는** 것 — 파일명

이 아티클의 핵심 통찰이자 질문의 답:

> **파일명은 inode에 없다.** 파일명은 "디렉토리"라는 특수 파일의 데이터 안에, `파일명 → inode 번호` 매핑으로 저장된다.

```
┌─────────────────────────┐        ┌──────────────────────┐
│  디렉토리 (자체도 파일)      │        │  inode #1714604       │
│  ─────────────────────  │        │  ─────────────────    │
│  "example.txt" → 1714604 │──────▶│  크기, 권한, 소유자,     │
│  "hard.txt"    → 1714604 │──────▶│  타임스탬프, 링크수=2,   │
│  "other.log"   → 1714888 │        │  데이터 블록 포인터      │
└─────────────────────────┘        └──────────┬───────────┘
                                              ▼
                                   ┌──────────────────────┐
                                   │  데이터 블록 (실제 내용)  │
                                   └──────────────────────┘
```

이 구조에서 따라 나오는 사실들:

- **하나의 inode를 여러 이름이 가리킬 수 있다** → 하드링크. 어느 쪽이 "원본"이라는 개념 자체가 없다.
- **파일 삭제(`rm`)는 사실 unlink다** → 디렉토리 엔트리를 지우고 링크 카운트를 줄이는 것. 카운트가 0이 되고 열어둔 프로세스도 없어야 inode와 데이터 블록이 회수된다.
- 파일명 바꾸기/이동은 디렉토리 엔트리 조작일 뿐, 데이터는 이동하지 않는다.

### 3. cp vs mv — inode 번호로 확인하기

```bash
ls -i example.txt      # 1714604
cp example.txt copy.txt
ls -i copy.txt         # 1714664 ← 새 inode (새 파일 생성)

mv copy.txt moved.txt
ls -i moved.txt        # 1714664 ← 같은 inode (이름만 변경)
```

| 연산 | inode | 의미 |
|---|---|---|
| `cp` | 새로 생성 | 데이터 블록도 새로 복사된 별개의 파일 |
| `mv` (같은 파일시스템) | 유지 | 디렉토리 엔트리만 변경, 대용량 파일도 즉시 완료 |

### 4. sed -i / Vim의 함정 — "제자리 수정"은 제자리가 아니다

`sed -i`, Vim 등은 안전한 저장(safe-write) 전략을 쓴다:

1. 임시 파일 생성 (**새 inode**)
2. 변경 내용을 임시 파일에 기록
3. 임시 파일을 원래 이름으로 rename → 기존 inode는 unlink

```bash
echo "hello" > config.txt
ls -i config.txt       # 1714736
sed -i 's/hello/world/' config.txt
ls -i config.txt       # 1714737 ← inode가 바뀌었다!
```

반면 **append(`>>`)는 inode를 유지**한다:

```bash
touch target.txt
ls -i target.txt          # 1714736
echo "append" >> target.txt
ls -i target.txt          # 1714736 ← 그대로
vi target.txt             # 편집 후 :wq
ls -i target.txt          # 1714739 ← 바뀜
```

**프로덕션 임팩트**: `inotify`나 inode 기반으로 파일을 추적하는 로그 수집기는 로그 로테이션이나 `sed -i` 편집 순간 **삭제된 옛 inode를 계속 바라보게 된다.** `tail -f`(fd 고정)가 아니라 `tail -F`(이름 기준 재추적)를 써야 하는 이유가 정확히 이것이다.

### 5. 하드링크 vs 심볼릭 링크

```bash
echo "Hello" > original.txt
ln original.txt hard.txt      # 하드링크
ln -s original.txt sym.txt    # 심볼릭 링크

ls -li
# 1714669 ... hard.txt                    ← original과 같은 inode
# 1714669 ... original.txt
# 1714670 ... sym.txt -> original.txt     ← 별도 inode, 내용은 "경로 문자열"
```

`ls -li`의 맨 앞이 inode 번호, 세 번째 컬럼이 링크 카운트다. hard.txt와 original.txt가 **같은 inode + 카운트 2**로 뜨는 게 핵심 — 둘은 동등한 이름이며 "원본/링크" 구분 자체가 없다.

| | 하드링크 | 심볼릭 링크 |
|---|---|---|
| 실체 | 같은 inode를 가리키는 또 하나의 디렉토리 엔트리 | 경로 문자열을 담은 별도 파일(별도 inode) |
| 링크 카운트 | inode 카운트 **+1** (직접 참조) | inode 카운트와 **무관** (경로 문자열만 저장) |
| 원본 삭제 시 | 데이터 유지 (카운트만 감소, 0이 될 때만 회수) | 깨진 링크(dangling) — 화살표만 남고 대상이 없음 |
| 파일시스템 경계 | 불가 (inode 번호는 파티션 내에서만 유일) | 가능 (경로 문자열이라 어디든 가리킴) |
| 디렉토리 대상 | 불가 (트리에 순환 발생 → 커널이 금지) | 가능 (순환 시 ELOOP로 안전하게 중단) |

> **삭제 = unlink**: `rm`은 데이터가 아니라 `이름 → inode` 매핑 하나를 떼는 것. 하드링크는 카운트만 2→1로 줄어 데이터가 살아있고, 심볼릭 링크는 대상 inode의 카운트를 애초에 건드리지 않았으므로 원본이 지워지면 가리킬 곳이 사라져 깨진다.

> **macOS(BSD)에서 링크 카운트/inode 확인** — 이 노트의 다른 PoC는 GNU 도구(`stat -c`)를 쓰지만, macOS는 BSD `stat`이라 포맷 문자가 다르다.
> ```bash
> # Linux(GNU):  stat -c 'links=%h inode=%i' hard.txt
> stat -f 'links=%l inode=%i' hard.txt   # macOS(BSD): %l=링크수, %i=inode, %N=파일명
> ```
> GNU 문법 그대로 쓰려면 `brew install coreutils` 후 `gstat -c '...'`. inode 개념 자체는 APFS에도 있으나 번호·포맷은 ext4와 다를 수 있다.

### 6. 큰 그림 — VFS와 파일시스템의 종류

inode는 VFS(Virtual File System) 추상화의 일부다. VFS 덕분에 애플리케이션은 아래가 무엇이든 동일한 `open/read/write/close`를 쓴다.

| 유형 | 예시 | 특징 |
|---|---|---|
| 디스크 기반 | ext4, xfs, btrfs | 영속 저장 (`/home`, `/var`) |
| 메모리 기반 | tmpfs, ramfs | 재부팅 시 소멸, 매우 빠름 (`/tmp`, `/run`) |
| 의사(Pseudo) | /proc, /sys, cgroup | 접근 시 커널이 즉석 생성 — 커널 상태를 보는 창 |
| 레이어드 | overlay, aufs | 읽기 전용 하층 + 쓰기 가능 상층 병합 — Docker의 기반 |

Docker의 OverlayFS는 읽기 전용 이미지 레이어(Lower) 위에 컨테이너별 쓰기 레이어(Upper)를 겹치고, 수정 시 Copy-on-Write로 상층에 복사한다. `/proc/cpuinfo` 같은 파일은 디스크 어디에도 없고 읽는 순간 커널이 만들어낸다 — "모든 것이 파일"이라는 추상화의 결과다.

### 7. 프로세스의 시각 — 파일 디스크립터

프로세스가 파일을 열면 커널은 프로세스별 open file table의 인덱스인 **파일 디스크립터(FD)** 를 돌려준다. 0(stdin), 1(stdout), 2(stderr)이 선점되어 있어 첫 파일은 보통 3번을 받는다.

"모든 것이 파일"이므로 **DB 커넥션, TCP 소켓, 로그 파일이 전부 FD를 소비한다.** 기본 한도(보통 1024)는 서버에 너무 낮아서, CPU/RAM이 남아돌아도 `too many open files`로 커넥션을 못 받는 장애가 난다. 대응은 두 가지: 누수 수정(`defer file.Close()` 등)과 `/etc/security/limits.conf`에서 한도 상향.

---

## 실무 PoC — 리눅스에서 직접 재현하기

> 아래 PoC는 전부 **Debian(ext4) 컨테이너에서 직접 실행해 검증**했다(`docker run debian:stable-slim`). 각 PoC 아래에 **🍎 macOS 실행 노트**를 붙여 맥(APFS/BSD 도구)에서의 차이와 실제 출력도 함께 검증해 정리했다. 요약하면 ①⑤는 명령 몇 개만 바꾸면 그대로 재현되고, ②는 `/proc`·`lsof` 차이로 관찰법이 달라지며, **③(inode 고갈)·④(tail -f/-F)는 APFS와 BSD `tail`의 동작 특성상 맥에서 원리적으로 재현되지 않는다** — 이 경우 리눅스 컨테이너(`docker run debian:stable-slim`)에서 확인해야 한다.

### PoC ①: "파일명은 inode에 없다"를 하드링크로 증명

파일명이 inode가 아니라 디렉토리 엔트리(`이름 → inode번호` 매핑)에 산다면, **하나의 inode에 여러 이름**을 붙일 수 있어야 하고, **이름 하나를 지워도 실체는 남아야** 한다. 정확히 그렇게 동작한다.

```bash
echo "dummy" > example.txt
ls -i example.txt
# 2883849 example.txt        ← 이름과 inode번호의 매핑

ln example.txt hard.txt      # 하드링크: 같은 inode에 이름 하나 더
ls -li example.txt hard.txt
# 2883849 -rw-r--r-- 2 root root 6 ... example.txt   ← 같은 inode, Links=2
# 2883849 -rw-r--r-- 2 root root 6 ... hard.txt      ← 같은 inode, Links=2

rm example.txt               # rm = unlink(2): 디렉토리 엔트리 삭제 + 링크카운트 -1
cat hard.txt                 # dummy   ← 데이터는 멀쩡히 살아있다
stat -c 'links=%h inode=%i' hard.txt
# links=1 inode=2883849       ← 실체(inode)는 그대로, 카운트만 2→1
```

**포인트**: `rm`은 "파일을 지우는" 명령이 아니라 "이름과 실체의 연결을 끊는" 명령이다. 링크카운트가 0이 되고 아무도 안 열고 있어야 비로소 inode와 데이터 블록이 회수된다 — 다음 PoC의 전제.

> **🍎 macOS 실행** — 그대로 재현된다. 링크 카운트 출력만 GNU(`stat -c`)가 아니라 BSD(`stat -f`) 문법을 쓴다.
> ```bash
> echo "dummy" > example.txt
> ln example.txt hard.txt
> ls -li example.txt hard.txt   # 맨 앞=inode, 세 번째 컬럼=링크수(2)로 동일
> rm example.txt
> cat hard.txt                  # dummy — 데이터 생존
> stat -f 'links=%l inode=%i' hard.txt
> # links=1 inode=105491852     ← 카운트만 2→1, inode는 그대로 (맥에서 직접 확인)
> ```

### PoC ②: "삭제했는데 `df`가 안 줄어든다" — deleted-but-open

운영에서 가장 자주 만나는 유령. 로그 파일을 `rm` 했는데 디스크가 안 비워진다. 프로세스가 fd로 inode를 쥐고 있으면 unlink돼도 inode는 살아있기 때문이다.

```bash
dd if=/dev/zero of=big.log bs=1M count=100 status=none   # 100MB
tail -f big.log >/dev/null &                              # 어떤 프로세스가 열어둠
TPID=$!
rm big.log                                                # unlink — ls엔 안 보인다
ls big.log        # ls: cannot access 'big.log': No such file or directory

# 그런데 공간은 회수되지 않았다. lsof가 '(deleted)'로 잡아준다:
lsof -p $TPID | grep -i deleted
# tail  256 root  3r  REG  0,142  104857600  2883910  /root/big.log (deleted)
ls -l /proc/$TPID/fd/ | grep -i deleted
# lr-x------ 1 root root 64 ... 3 -> /root/big.log (deleted)

kill $TPID        # fd를 닫는 순간(=프로세스 종료) 비로소 100MB 회수
```

**실무 처방**: `df`는 여유가 없는데 `du`로 합산하면 설명이 안 될 때, 범인은 십중팔구 이것이다. `lsof +L1`(링크카운트 0인 열린 파일)로 찾고, 해당 프로세스를 재시작하거나 `: > /proc/PID/fd/N`으로 truncate하면 공간이 즉시 돌아온다. 서비스 무중단으로 회수해야 할 때 후자가 유용하다.

> **🍎 macOS 실행** — "unlink된 파일을 열어둔 프로세스가 공간을 쥔다"는 원리는 동일하나, **관찰·회수 도구가 다르다.**
> ```bash
> mkfile 100m big.log            # 또는: dd if=/dev/zero of=big.log bs=1m count=100
> tail -f big.log >/dev/null & TPID=$!
> rm big.log                     # ls엔 사라짐
> lsof -p $TPID | grep big.log   # 여전히 열려 있음 (경로+크기 표시)
> kill $TPID                     # 닫는 순간 공간 회수
> ```
> **차이 두 가지**: (1) 맥 `lsof`는 리눅스처럼 `(deleted)` 꼬리표를 **붙이지 않는다** — `grep deleted`가 안 먹으니 파일명으로 찾아야 한다. (2) 맥엔 `/proc`이 없어 `: > /proc/PID/fd/N` 무중단 truncate 트릭을 쓸 수 없다. 회수하려면 프로세스를 재시작/종료해야 한다.

### PoC ③: "디스크는 남는데 파일을 못 만든다" — inode 고갈

inode 개수는 파일시스템 생성 시 고정되는 유한 자원이다. 작은 파일이 수백만 개 쌓이면 용량이 남아도 파일 생성이 막힌다. inode 128개짜리 초소형 ext4를 만들어 재현한다.

```bash
dd if=/dev/zero of=fs.img bs=1M count=8 status=none
mkfs.ext4 -q -N 128 fs.img          # inode를 일부러 128개만
mkdir -p /mnt/tiny && mount -o loop fs.img /mnt/tiny
cd /mnt/tiny

i=0; while echo x > f$i 2>/dev/null; do i=$((i+1)); done   # 작은 파일 폭탄
echo "만들어진 파일: $i"            # 116개에서 멈춤 (나머지는 예약/오버헤드)

df -h .    # /dev/loop0  7.0M  164K  6.2M   3%  /mnt/tiny   ← 용량은 3%만 씀
df -i .    # /dev/loop0   128   128     0  100% /mnt/tiny   ← inode는 100%!
touch overflow
# touch: cannot touch 'overflow': No space left on device   ← 메시지는 똑같다
```

**함정**: 에러 메시지가 용량 부족과 **완전히 동일한** `No space left on device`다. `df -h`만 보면 원인을 놓친다. 반드시 **`df -i`를 함께** 봐야 한다. 메일 큐(`/var/spool`), 세션 파일, npm `node_modules`, 컨테이너 레이어가 흔한 범인이다.

> **🍎 macOS 재현 불가** — 맥의 기본 파일시스템 **APFS는 inode를 미리 고정 할당하지 않고 필요할 때 동적으로 만든다.** 그래서 `mkfs.ext4 -N 128` 같은 "inode 개수 고정"이 없고, `df -i`를 찍어도 `ifree`가 수억 개로 나온다.
> ```bash
> df -i /System/Volumes/Data
> # ... iused 6292694  ifree 199161880  %iused 3%   ← 남는 inode가 사실상 무제한
> ```
> 이 PoC는 inode 개수가 고정된 ext4/xfs에서만 성립한다. 맥에서 보려면 리눅스 컨테이너로:
> ```bash
> docker run --rm --privileged debian:stable-slim bash -c '
>   apt-get -qq update && apt-get -qq install -y e2fsprogs
>   dd if=/dev/zero of=fs.img bs=1M count=8 status=none
>   mkfs.ext4 -q -N 128 fs.img && mkdir -p /mnt/tiny && mount -o loop fs.img /mnt/tiny
>   cd /mnt/tiny; i=0; while echo x > f$i 2>/dev/null; do i=$((i+1)); done
>   echo "files=$i"; df -i . | tail -1'
> # files=116,  ifree 0 / %iused 100%  (컨테이너에서 직접 확인)
> ```

### PoC ④: "`sed -i` 한 번에 로그 수집기가 눈이 먼다" — `tail -f` vs `tail -F`

`sed -i`·Vim의 "제자리 수정"은 사실 **임시파일 생성 → rename → 옛 inode unlink**다. inode가 통째로 바뀐다. fd를 고정하는 `tail -f`는 삭제된 옛 inode를 계속 바라보고, 이름으로 재추적하는 `tail -F`는 새 inode를 따라간다. 두 추적기를 동시에 띄워 차이를 관찰한다.

```bash
printf 'line1\n' > app.log
ls -i app.log                     # 2883862 app.log

tail -f app.log > f_out.txt &     # fd 고정 방식
tail -F app.log > F_out.txt &     # 이름 재추적 방식
sleep 2

sed -i 's/line1/LINE1/' app.log   # '제자리 수정' → inode 교체
ls -i app.log                     # 2883879 app.log   ← inode가 바뀌었다
echo 'line2-after-rotate' >> app.log
sleep 3

cat f_out.txt        # line1                       ← 옛 inode에 갇혀 이후를 통째로 놓침
cat F_out.txt        # line1 / LINE1 / line2-after-rotate  ← 새 inode 재추적 성공
```

**포인트**: 로그 로테이션도 `sed -i`도 에디터 저장도 전부 inode를 회전시킨다. Fluent Bit·Filebeat 같은 수집기가 "파일명 기준 재발견/`rotate_wait`" 옵션을 두는 이유가 정확히 이것이고, 셸에서는 `tail -f`가 아니라 `tail -F`를 써야 하는 이유다.

> **🍎 macOS 재현 불안정** — 이 대비는 **GNU coreutils의 `tail`에서만 선명하다.** 맥 기본 `tail`은 BSD 판본이라 `-f`가 이미 이름 기반 재오픈을 부분적으로 수행해서, 로테이션 후 `-f`와 `-F`가 **둘 다 새 inode를 따라가거나** 실행마다 결과가 달라진다(관찰 완료). 즉 "-f는 놓치고 -F만 따라간다"는 교과서적 차이가 맥에선 깨진다.
> - `sed -i`도 문법이 다르다: 맥은 백업 접미사 인자가 필수라 `sed -i '' 's/.../.../' app.log`.
> - 차이를 제대로 보려면 GNU tail(`brew install coreutils` → `gtail -f` / `gtail -F`)을 쓰거나, 애초에 inotify 기반인 리눅스 컨테이너에서 확인하는 편이 확실하다.

### PoC ⑤: "too many open files" — FD도 유한 자원

"모든 것이 파일"이라 소켓·DB 커넥션·로그가 전부 fd를 먹는다. 한도를 16으로 낮춰 EMFILE을 재현하면 예약된 fd(0/1/2)까지 셈이 맞는 걸 볼 수 있다.

```bash
ulimit -Sn 16          # soft 한도를 16으로
python3 - <<'PY'
import errno
opened=[]
try:
    while True: opened.append(open("/etc/hostname"))
except OSError as e:
    print(f"errno={e.errno}({errno.errorcode[e.errno]}) {e.strerror}")
    print(f"연 개수={len(opened)}, 마지막 fd={opened[-1].fileno()}")
PY
# errno=24(EMFILE) Too many open files
# 연 개수=13, 마지막 fd=15      ← 16 - (stdin/out/err 3개) = 13, fd는 3~15
```

**실무 처방**: CPU·메모리 그래프가 멀쩡한데 커넥션을 못 받는 장애의 전형이다. `cat /proc/PID/limits`로 실제 한도를, `ls /proc/PID/fd | wc -l`로 현재 소비량을 확인한다. 대응은 두 갈래 — fd 누수 수정(`defer f.Close()`, 커넥션 풀 반환)과 한도 상향(`LimitNOFILE=` in systemd unit, `/etc/security/limits.conf`). 컨테이너에선 호스트/런타임 한도까지 함께 봐야 한다.

> **🍎 macOS 실행** — 그대로 재현된다. 단, 파이썬이 여는 대상 파일을 맥에 존재하는 것으로 바꿔야 한다(`/etc/hostname`은 맥에 없음 → `/etc/hosts`).
> ```bash
> ( ulimit -Sn 16
>   python3 - <<'PY'
> import errno
> opened=[]
> try:
>     while True: opened.append(open("/etc/hosts"))
> except OSError as e:
>     print(f"errno={e.errno}({errno.errorcode[e.errno]}) {e.strerror}")
>     print(f"opened={len(opened)}, last_fd={opened[-1].fileno()}")
> PY
> )
> # errno=24(EMFILE) Too many open files
> # opened=13, last_fd=15   ← 16 - (0/1/2 예약 3개) = 13, fd 3~15 (맥에서 동일하게 확인)
> ```
> 소비량 확인도 `/proc`이 없으니 `lsof -p PID | wc -l`로, 한도는 `launchctl limit maxfiles` / `ulimit -n`으로 본다.

---

## 내가 얻은 인사이트

### 설계 관점

1. **"이름"과 "실체"의 분리가 유닉스 파일시스템 설계의 핵심**
   - 파일명(디렉토리 엔트리)과 파일 실체(inode)를 분리한 덕분에 하드링크, 원자적 rename, "열려 있는 파일 삭제" 같은 유닉스 특유의 동작이 모두 자연스럽게 성립한다. 저장되지 "않는" 정보가 무엇인지가 오히려 설계 의도를 가장 잘 드러낸다.
   - `rm`이 `unlink(2)` 시스템 콜인 것도 같은 맥락 — 파일을 지우는 게 아니라 이름과 실체 사이의 연결을 끊는 것이다.

2. **rename의 원자성이 안전한 쓰기 패턴의 토대**
   - Vim, sed -i의 "임시 파일 + rename" 패턴은 크래시가 나도 파일이 반쯤 쓰인 상태로 남지 않게 하는 표준 기법이다. 같은 저장소의 [Files are hard](Files%20are%20hard%20-%20파일에%20안전하게%20쓰는%20것은%20왜%20어려운가.md)에서 다룬 crash-safe 쓰기와 정확히 연결된다.
   - 대신 대가가 있다: inode가 바뀐다. 안전성(새 inode)과 추적 연속성(같은 inode)은 트레이드오프다.

### 운영/트러블슈팅 관점

1. **"디스크는 남는데 파일을 못 만든다"면 inode 고갈을 의심하라**
   - inode는 파일시스템 생성 시 개수가 정해지는 유한 자원이다. 수백만 개의 작은 파일(세션 파일, 캐시, 메일 큐)이 쌓이면 `df -h`는 여유가 있어도 `df -i`가 100%일 수 있다.

2. **로그 파이프라인 장애의 단골 원인은 inode 회전**
   - 로그 로테이션, `sed -i`, 에디터 저장 — 전부 inode를 바꾼다. inode/fd 기반 추적기(inotify, tail -f)는 이 순간 유령 파일을 감시하게 된다. 로그 수집기 설정에서 "파일명 기준 재발견" 옵션이 존재하는 이유다.
   - 반대로 "삭제했는데 디스크가 안 비워진다"는 것도 같은 원리다. 프로세스가 fd를 쥐고 있으면 unlink되어도 inode는 살아 있다. `lsof +L1`로 deleted-but-open 파일을 찾는다.

3. **FD 한도는 용량 계획의 일부다**
   - "모든 것이 파일"은 철학이 아니라 청구서다. 커넥션 폭증 장애에서 CPU/메모리 그래프만 보면 원인을 놓친다. `ulimit -n`과 커넥션 풀 크기, keep-alive 설정을 함께 검토해야 한다.

### 학습 관점

1. **`ls -i` 하나로 대부분의 개념을 실험으로 확인할 수 있다**
   - cp/mv/append/편집 각각의 inode 변화를 직접 찍어보는 것이 교과서 설명보다 빠르다. 추상적 개념(디렉토리 엔트리 vs inode)이 명령 두 줄로 관찰 가능한 사실이 된다.
