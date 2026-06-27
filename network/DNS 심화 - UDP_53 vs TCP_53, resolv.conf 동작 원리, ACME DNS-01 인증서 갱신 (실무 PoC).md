# DNS 심화 - UDP/53 vs TCP/53, resolv.conf 동작 원리, ACME DNS-01 인증서 갱신 (실무 PoC)

## 출처
- **아티클/논문**: Evaluating DNS Resiliency and Responsiveness with Truncation, Fragmentation & DoTCP Fallback
- **저자/출처**: arXiv (2307.06131, 2023) — DNS 트래픽 측정 연구. 보조 근거로 SIDN Labs, ISC BIND KB, Let's Encrypt 공식 문서 참조.
- **링크**: https://arxiv.org/abs/2307.06131

> 본 문서는 위 논문의 "DNS는 왜 UDP와 TCP를 둘 다 쓰는가 / TC 비트 fallback이 실패하면 무슨 일이 벌어지는가"라는 핵심 질문을 중심으로,
> 실무자가 곧장 터미널에서 재현할 수 있는 PoC를 곁들여 정리했다. 모든 PoC는 **macOS 14(Sonoma)에서 직접 실행해 검증**했고,
> glibc 전용 도구(`getent`·`RES_OPTIONS`·`ndots`)가 등장하는 곳은 macOS 대체 명령을 함께 적었다.

---

## AI 요약

### 0. 한 장 요약

| 질문 | 핵심 답 |
|------|---------|
| DNS는 왜 53번을 UDP/TCP 둘 다 여나? | 평소엔 UDP(빠르고 stateless), 응답이 잘려서 TC=1이 오거나 zone transfer면 TCP로 재시도 |
| TCP/53이 막혀 있으면? | DNSSEC·큰 TXT·많은 A 레코드 응답이 **silent fail** → "가끔 안 됨"의 주범 |
| `/etc/resolv.conf`는 누가 읽나? | 앱이 아니라 **glibc `getaddrinfo()`** (+ `nsswitch.conf`). `dig`는 이걸 우회함 |
| 쿠버에서 DNS가 느린 이유? | `options ndots:5` 때문에 외부 도메인 1번 찾는 데 쿼리가 5~6번 나감 |
| 80포트 안 열고 와일드카드 인증서? | ACME **DNS-01** — `_acme-challenge` TXT 레코드로 도메인 소유 증명 |

---

### 1. DNS 메시지와 "512바이트의 저주"

DNS는 1987년 RFC 1035에서 **UDP 응답을 512바이트로 제한**했다. 당시 보장되던 최소 재조립 크기였기 때문이다.
헤더 구조를 보면 핵심 플래그가 보인다.

```
                                1  1  1  1  1  1
  0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                      ID                       |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|QR| Opcode    |AA|TC|RD|RA|   Z    |   RCODE   |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+   ← TC = TrunCated bit
|                    QDCOUNT                     |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
              ... QUESTION / ANSWER ...
```

- **TC (Truncation) 비트**: 응답이 UDP 버퍼에 안 들어가면 서버는 "들어가는 만큼만 보내고 TC=1"로 표시한다.
- 클라이언트는 TC=1을 보면 **같은 질의를 TCP로 다시 던진다**. 이게 DNS가 TCP/53을 여는 첫 번째 이유다.

#### EDNS0 — 512바이트 한계를 푸는 법 (RFC 6891)

EDNS0는 질의에 **OPT pseudo-record**를 끼워서 "나는 UDP로 최대 N바이트까지 받을 수 있다"를 광고한다.
요즘 리졸버는 보통 1232 또는 4096을 광고한다.

```
[클라이언트] --- Query (OPT: UDP payload size = 4096) --->  [서버]
[클라이언트] <-- Response 3800 bytes over UDP (TC=0) -----  [서버]   ← 512 넘어도 OK
```

> **DNS Flag Day 2020**: 권장 EDNS 버퍼를 **1232바이트**로 낮췄다.
> 이유는 §3의 fragmentation 문제. (1280 IPv6 최소 MTU − IPv6 40 − UDP 8 = 1232)

### 2. DNS가 TCP/53을 쓰는 4가지 경우

| 상황 | 이유 |
|------|------|
| **응답 truncation (TC=1)** | UDP 버퍼 초과 → TCP 재시도. DNSSEC 서명·많은 A/AAAA·긴 TXT에서 흔함 |
| **Zone Transfer (AXFR/IXFR)** | 존 전체 복제는 수십 KB~MB. 신뢰성 필수 → 항상 TCP |
| **DNS Cookie / 대용량 응답 강제** | 일부 권위 서버는 amplification 방어로 작은 UDP 후 TCP 유도 |
| **DoT (DNS over TLS, 853)** | TLS는 TCP 위에서만. UDP는 DoQ(QUIC)로 별도 |

```
   평상시 (99%)                         큰 응답 / Zone Transfer
 ┌──────────┐   UDP/53   ┌────────┐   ┌──────────┐   TCP/53   ┌────────┐
 │ resolver │ ─────────> │ server │   │ resolver │ ─────────> │ server │
 │          │ <───────── │        │   │          │ <───────── │  (3-way│
 └──────────┘  TC=0      └────────┘   └──────────┘  full data  handshake)
                                          ↑ TC=1 받고 재시도
```

### 3. 진짜 무서운 부분 — "TCP fallback이 막히면 silent fail"

논문(arXiv 2307.06131)과 SIDN Labs 측정이 공통으로 지적하는 실무 함정:

1. **큰 UDP 응답은 IP fragment로 쪼개진다.** 많은 방화벽/미들박스가 IP fragment를 드롭한다 → 응답이 영영 안 옴.
2. 그래서 TC=1로 "TCP로 와"라고 유도하는데, **방화벽에서 TCP/53을 막아둔 곳이 의외로 많다.** "DNS는 UDP니까 TCP는 닫아도 되겠지"라는 오해 때문.
3. 결과: 작은 응답은 잘 되고 **DNSSEC·큰 레코드만 가끔 timeout** → 디버깅 지옥. ("It's always DNS"의 정체)

> **실무 체크리스트**: DNS 권위/재귀 서버 앞단 방화벽에서 **UDP/53과 TCP/53을 반드시 둘 다 열 것.**
> EDNS 버퍼는 1232로 맞춰 fragmentation을 회피할 것.

---

## PoC ①: UDP/TCP/TC 비트를 눈으로 확인하기

### (a) 평소 질의는 UDP로 나간다

```bash
# +short는 답만, 트랜스포트는 안 보임 → 통계를 보자
dig google.com A

# 응답 맨 아래 ;; 줄에서 트랜스포트를 확인
#   ;; Query time: 12 msec
#   ;; SERVER: 1.1.1.1#53(1.1.1.1) (UDP)   ← UDP로 갔다
```

> ⚠️ `(UDP)`/`(TCP)` 트랜스포트 라벨은 **BIND 9.11+에서 추가**됐다. macOS 기본 dig(9.10.x)는
> 이 라벨을 안 찍고 `;; SERVER: 1.1.1.1#53(1.1.1.1)`에서 끝난다. 9.10.x에서 TCP 전환을
> 확인하려면 (c)처럼 **`;; Truncated, retrying in TCP mode.`** 줄을 보거나 (f)의 tcpdump를 쓴다.

### (b) UDP 버퍼를 512로 줄여 TC=1을 강제로 유발

DNSSEC 서명이 붙은 존에 `+dnssec`를 켜고 버퍼를 작게 주면 **응답이 512를 넘칠 때** 잘린다.
여기서 **존의 서명 알고리즘이 결정적**이다. `org`는 RSA(algorithm 8)라 DNSKEY 응답이 ~895B로 512를 넘겨 잘리지만, `cloudflare.com`은 ECDSA P-256(algorithm 13)이라 응답이 313B밖에 안 돼 **512 안에 들어가 절대 안 잘린다.** 그래서 PoC 존으로는 RSA 존(`org` 등)을 써야 한다.

```bash
# EDNS 버퍼를 512로 강제 + DNSSEC 요청 → org 응답(~895B)이 512를 넘쳐 잘림
dig org DNSKEY +dnssec +bufsize=512 +notcp +ignore @1.1.1.1

# 출력에서 flags를 보라:
#   ;; flags: qr tc rd ra; QUERY: 1, ANSWER: 0, ...
#                  ^^  ← tc 비트가 섰다! (응답이 잘렸다는 뜻, ANSWER가 0으로 비어버림)
```

- `+bufsize=512` : 내 UDP 수신버퍼를 512로 광고 (512 미만은 서버가 512로 끌어올리므로 더 줄여도 의미 없음)
- `+notcp` : TCP로 자동 재시도하지 마라 (fallback 끄기)
- `+ignore` : TC 비트를 무시하고 잘린 UDP 응답을 그대로 보여줘라

> ⚠️ 흔한 함정: `cloudflare.com DNSKEY +bufsize=512`로는 TC가 **안 뜬다** (313B < 512). 작은 ECDSA 응답은 버퍼를 0까지 줄여도 안 잘린다 — 잘림을 보려면 응답 자체가 512를 넘어야 한다.

### (c) fallback을 켜면 같은 질의가 TCP로 넘어간다

```bash
# +ignore 빼고 +bufsize=512 유지 → dig가 TC=1 보고 알아서 TCP 재시도
dig org DNSKEY +dnssec +bufsize=512 @1.1.1.1

# 출력 맨 위에 이 줄이 뜨고, 이어 full answer(ANSWER:4)가 온다:
#   ;; Truncated, retrying in TCP mode.    ← UDP에서 잘려서 TCP로 갈아탔다!
# (BIND 9.11+라면 ;; SERVER 줄 끝에 (TCP) 라벨도 함께 찍힌다)
```

### (d) "방화벽이 TCP/53을 막은 상황" 재현 — silent fail 체험

```bash
# TCP 금지 + 작은 버퍼 + TC 무시 → 잘린 반쪽짜리 응답밖에 못 받는 상태
dig org DNSKEY +dnssec +bufsize=512 +notcp +ignore @1.1.1.1
# → flags에 tc, ANSWER:0. TCP를 못 쓰니 완전한 답을 영영 못 받음.
#   실제 운영에서 이게 "DNSSEC만 가끔 실패"로 나타난다.
```

> ⚠️ 여기서 **`+ignore`가 필수**다. `+notcp`만 주면 dig는 truncation을 만났을 때
> `;; Truncated, retrying in TCP mode.`를 띄우며 **`+notcp`를 무시하고 TCP로 재시도해 full answer를
> 받아버린다**(silent fail 재현 실패). `+ignore`가 있어야 잘린 stub에서 멈춰 "TCP 막힘 = 답 못 받음"
> 상황이 그대로 재현된다.

### (e) Zone Transfer는 무조건 TCP

```bash
# AXFR은 UDP로 시도조차 안 한다 (대부분 거부되지만 트랜스포트 확인용)
dig @ns1.example.com example.com AXFR +tcp
# 공개 테스트: zonetransfer.me 는 일부러 AXFR을 열어둔 학습용 도메인
dig @nsztm1.digi.ninja zonetransfer.me AXFR
```

### (f) 패킷으로 직접 보기 (선택)

```bash
# 터미널 1: 53번 포트 트래픽 캡처 (UDP/TCP 둘 다)
sudo tcpdump -ni any 'port 53' -c 20

# 터미널 2: 큰 응답을 유발 (org는 RSA라 응답이 크다)
dig org DNSKEY +dnssec +bufsize=512 @1.1.1.1
# tcpdump에서 UDP 53 질의/응답, 그리고 TC면 이어지는 TCP 53 SYN을 확인
```

---

## PoC ②: `/etc/resolv.conf`는 누가, 어떻게 읽는가

### 핵심 오해 깨기 — `dig`는 resolv.conf를 "거의" 무시한다

`dig`/`nslookup`은 자체 stub 리졸버라 nameserver 목록 정도만 참고하고
`search`·`ndots`·`/etc/hosts`는 무시한다. **반면 우리 앱(curl, python, java, ping)은
glibc `getaddrinfo()`를 거치며, 이 경로가 진짜 resolv.conf를 따른다.** 둘의 결과가 달라서
"dig는 되는데 앱은 안 되는" 사건이 벌어진다.

```
  앱 (curl/python/ping)                 dig / nslookup
        │ getaddrinfo()                       │ 자체 stub resolver
        ▼                                      ▼
  ┌──────────────┐                      (resolv.conf의 nameserver만 참고,
  │ nsswitch.conf│  hosts: files dns     search/ndots/hosts 무시)
  └──────┬───────┘
   files │  → /etc/hosts 먼저
   dns   │  → /etc/resolv.conf (nameserver/search/options)
        ▼
  127.0.0.53 (systemd-resolved stub) 또는 외부 리졸버
```

### resolv.conf 해부

```conf
# /etc/resolv.conf
nameserver 127.0.0.53        # 질의 보낼 서버 (보통 systemd-resolved stub)
search corp.example.com svc.cluster.local   # 짧은 이름에 붙여볼 도메인들
options ndots:5 timeout:2 attempts:2 rotate single-request-reopen
```

| 옵션 | 의미 | 실무 함정 |
|------|------|-----------|
| `search` | 짧은 이름 뒤에 순서대로 붙여 FQDN 시도 | 항목이 많으면 쿼리 수 폭발 |
| `ndots:N` | 점이 **N개 미만**이면 search부터, N개 이상이면 절대도메인부터 | 쿠버 기본 `ndots:5`가 외부도메인 지연 유발 |
| `timeout:N` `attempts:M` | 서버당 N초, 총 M회 시도 | 기본 5초×2 = 장애 시 10초 hang |
| `rotate` | nameserver를 라운드로빈 | 부하분산용 |
| `single-request-reopen` | A/AAAA를 한 소켓 병렬로 안 보냄 (특정 NAT 버그 회피) | glibc 병렬 질의 conntrack 충돌 fix |

### ndots의 동작 = 쿠버네티스 DNS 지연의 정체

`google.com`은 점이 1개. 쿠버 기본 `ndots:5`에선 **5개 미만이므로 search 도메인부터 붙여본다**:

```
google.com.default.svc.cluster.local   → NXDOMAIN
google.com.svc.cluster.local           → NXDOMAIN
google.com.cluster.local               → NXDOMAIN
google.com.corp.example.com            → NXDOMAIN
google.com.                            → 드디어 정답 (절대도메인)
```

> 외부 도메인 1번 찾는데 질의가 **5~6번** 나간다. AAAA까지 치면 2배.
> 그래서 쿠버에선 외부 호출 도메인 끝에 **점을 붙여 FQDN으로 박거나**(`google.com.`),
> Pod `dnsConfig`로 `ndots:2`로 낮추는 게 정석 튜닝이다.

### PoC: search/ndots 동작을 직접 관찰 (macOS / Linux)

> 이 절의 명령은 macOS 14(Sonoma, dig 9.10.6 / `dscacheutil` / `dns-sd`)에서 직접 실행해 검증했다.
> Linux(glibc)와 동작이 다른 부분은 그때그때 명시한다. 핵심 차이: **`getent`·`RES_OPTIONS`·`ndots`는
> glibc 전용**이고, macOS는 별도 시스템 리졸버(`mDNSResponder`/libinfo)를 쓴다.

```bash
# 1) 현재 resolver 설정 확인
#   (macOS)        scutil --dns | head -40        ← mac은 resolv.conf 대신 이걸 씀
#                  (/etc/resolv.conf는 "참고용 사본"이라 첫머리에 "not consulted" 안내가 박혀 있음)
scutil --dns | head -40
#   (Linux systemd) resolvectl status
#   (Linux 비systemd) cat /etc/resolv.conf
```

```bash
# 2) getaddrinfo가 실제로 뭘 질의하는지 추적
#   터미널 1: 53번 포트 캡처 — macOS도 -i any(pktap)를 지원한다
sudo tcpdump -ni any 'port 53'

#   터미널 2: getaddrinfo 경로로 질의를 발생시킨다
#   (macOS) getent가 없으므로 dscacheutil / dns-sd 를 쓴다 — 둘 다 시스템 리졸버를 탄다
dscacheutil -q host -a name google            # 짧은 이름 → search 도메인이 붙는 게 캡처에 보임
dscacheutil -q host -a name google.com.       # 끝에 점 → search 생략, 한 방에 끝남
dns-sd -t 2 -G v4v6 google.com                # 대안: 무엇을 어떻게 resolve하는지 실시간 표시(-t로 타임아웃)
#   (Linux) 같은 자리에서 getent hosts google / getent hosts google.com.

#   캡처를 갱신해 보고 싶으면 mac DNS 캐시를 비운 뒤 다시 질의:
#   sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
```

```bash
# 3) ndots 효과 실험 — ⚠️ 이건 Linux(glibc) 전용이다
#   (Linux) RES_OPTIONS 환경변수로 현재 셸에만 resolv.conf 옵션을 덮어쓴다
export RES_OPTIONS="ndots:1"   # glibc 전용. ndots를 낮춰 search 횟수 줄이기
getent hosts internalservice
#
#   (macOS) Apple 리졸버에는 ndots 개념도 RES_OPTIONS 오버라이드도 없다.
#   실제로 `RES_OPTIONS="ndots:1" dscacheutil ...`를 줘도 "조용히 무시"된다(검증함).
#   mac에서 도메인별 리졸버 옵션을 바꾸려면 /etc/resolver/<도메인> 파일을 쓰지만
#   (man 5 resolver: search_order·nameserver·port 등) ndots는 거기에도 없다.
#   → ndots:5 지연 튜닝은 본질적으로 "Linux/쿠버네티스 노드"의 이야기다.
```

> **macOS 정리**: macOS의 `/etc/resolv.conf`는 시스템이 만든 **참고용 사본**이라 직접 수정해도 안 먹는다.
> 실제 설정 확인은 `scutil --dns`, search 도메인 변경은 시스템 설정 또는
> `networksetup -setsearchdomains <서비스명> corp.example.com`으로 한다.

---

## PoC ③: ACME DNS-01 — 80포트 없이 와일드카드 인증서 갱신

### 왜 DNS-01인가

| 챌린지 | 증명 방식 | 와일드카드 | 80/443 필요 |
|--------|-----------|:---:|:---:|
| HTTP-01 | `/.well-known/acme-challenge/<token>` 파일 | ❌ | 80 필요 |
| TLS-ALPN-01 | 특수 TLS 핸드셰이크 | ❌ | 443 필요 |
| **DNS-01** | `_acme-challenge` **TXT 레코드** | ✅ **유일** | ❌ (포트 노출 0) |

DNS-01은 포트를 하나도 안 열어도 되고, **`*.example.com` 와일드카드를 발급받는 유일한 방법**이며,
방화벽 안쪽 내부 서버 인증서도 발급할 수 있다.

### 동작 흐름

```
  ACME client (certbot 등)                       Let's Encrypt CA
        │  1. "*.example.com 주세요" (newOrder)         │
        │ ───────────────────────────────────────────> │
        │  2. token 발급 + DNS-01 challenge             │
        │ <─────────────────────────────────────────── │
        │                                               │
        │  3. TXT 값 계산 후 DNS에 등록                  │
        │     _acme-challenge.example.com TXT "<digest>"│
        │  (DNS provider API로 자동 등록)                │
        │                                               │
        │  4. "확인해줘" (challenge ready)               │
        │ ───────────────────────────────────────────> │
        │                          5. CA가 권위 NS에 직접│
        │                             TXT 질의해서 대조  │
        │  6. 일치 → 인증서 발급                          │
        │ <─────────────────────────────────────────── │
        │  7. TXT 레코드 삭제 (cleanup)                  │
```

### 핵심: TXT 값은 어떻게 만들어지나 (RFC 8555)

```
keyAuthorization = token + "." + base64url( SHA256( JWK_thumbprint(계정키) ) )
TXT 레코드 값    = base64url( SHA256( keyAuthorization ) )
레코드 이름       = _acme-challenge.<도메인>
```

- **와일드카드 함정**: `*.example.com`의 레코드 이름은 `_acme-challenge.example.com`이다
  (`_acme-challenge.*.example.com`이 **아님**). apex에 단다.
- apex 도메인과 와일드카드를 한 인증서에 SAN으로 묶으면 **같은 이름에 TXT 2개**가 붙는다 (둘 다 허용).

### PoC: certbot이 만드는 TXT 값을 openssl로 손수 계산해보기

certbot이 내부에서 하는 계산을 그대로 재현한다. (개념 검증용 — 실제 thumbprint는 계정 JWK에서 나옴)

```bash
# base64url 헬퍼 (패딩 제거 + URL-safe 치환)
b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }

# 1) 실제론 계정 공개키 JWK의 정규화 JSON을 SHA256한 것. 여기선 예시로 대체.
ACCOUNT_THUMBPRINT="QmcW3N9b...example...X0kLpZ"     # base64url(SHA256(JWK))
TOKEN="ev6kqj9PqXyZ-Y4l9z0token_from_CA"             # CA가 준 토큰

# 2) keyAuthorization = token + "." + thumbprint
KEY_AUTH="${TOKEN}.${ACCOUNT_THUMBPRINT}"

# 3) TXT 값 = base64url(SHA256(keyAuthorization))
TXT_VALUE=$(printf '%s' "$KEY_AUTH" | openssl dgst -sha256 -binary | b64url)
echo "_acme-challenge.example.com.  IN  TXT  \"$TXT_VALUE\""
```

이 값이 바로 DNS provider API로 올라가는 레코드다. **certbot이 마법을 부리는 게 아니라 그냥 이 해시다.**

### PoC: 실제 발급 — certbot --manual (수동 hook으로 흐름 체감)

```bash
# DNS-01로 와일드카드 발급. certbot이 등록할 TXT 값을 화면에 띄워줌
sudo certbot certonly \
  --manual \
  --preferred-challenges dns \
  -d 'example.com' -d '*.example.com'

# certbot이 멈추고 알려줌:
#   _acme-challenge.example.com 에 TXT "xxxxx" 를 등록하고 Enter 치세요
# → DNS에 등록 후 전파 확인:
dig +short TXT _acme-challenge.example.com @1.1.1.1
# → 값이 보이면 Enter → CA가 검증 → fullchain.pem 발급
```

### PoC: 자동 갱신 (실무 정석) — DNS provider 플러그인

```bash
# 예: Cloudflare. API 토큰만 주면 certbot이 TXT 등록·검증·삭제를 전부 자동화
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /root/.secrets/cf.ini \
  -d 'example.com' -d '*.example.com'

# 갱신은 cron/systemd-timer가 돌리는 이 한 줄이 전부 (만료 30일 전 자동 갱신)
sudo certbot renew --dry-run
```

> **전파 지연 주의**: TXT 등록 후 권위 NS에 반영되기까지 수 초~수 분. certbot은 잠깐 기다린 뒤
> 검증하지만, provider가 느리면 실패한다. **CA는 캐시 리졸버가 아니라 권위 NS에 직접 질의**하므로
> 디버깅할 땐 `dig +trace`로 권위 서버까지의 경로를 확인하라:
> ```bash
> dig +trace TXT _acme-challenge.example.com
> ```

> **보안 팁**: 발급 권한을 좁히려면 `CAA` 레코드로 발급 가능한 CA를 못박고
> (`example.com. CAA 0 issue "letsencrypt.org"`), DNS API 토큰은 **TXT 레코드 한정 권한**으로 발급하라.

---

## 내가 얻은 인사이트

### 운영/SRE 관점
1. **방화벽에서 TCP/53을 절대 닫지 마라.**
   - "DNS는 UDP"라는 통념 때문에 TCP/53을 막아두면, 평소엔 멀쩡하다가 DNSSEC·큰 TXT(SPF/DKIM)·
     많은 A 레코드가 등장하는 순간 **간헐적 timeout**으로 터진다. 가장 디버깅하기 어려운 종류의 장애.
   - EDNS 버퍼를 1232로 맞춰 IP fragmentation까지 회피하면 fallback 자체를 덜 타게 된다.
2. **"dig는 되는데 앱은 안 된다"는 트랜스포트가 아니라 리졸버 경로 차이다.**
   - dig는 자체 stub, 앱은 `getaddrinfo()`+`nsswitch.conf`+`/etc/hosts`+search 도메인을 탄다.
     장애 분리할 땐 **앱과 같은 경로**를 재현해야 한다 — Linux는 `getent hosts <name>`,
     macOS는 `dscacheutil -q host -a name <name>`(둘 다 시스템 리졸버를 탄다).

### 성능/아키텍처 관점
3. **`ndots:5`는 클라우드 비용이자 지연이다.**
   - 쿠버 Pod가 외부 API를 도메인으로 호출할 때마다 search 도메인이 줄줄이 붙어 NXDOMAIN 폭탄이 난다.
     외부 도메인은 **FQDN(끝에 점)으로 박거나** `dnsConfig.options`로 `ndots`를 낮추는 게
     코드 한 줄 안 고치고 p99 latency를 깎는 방법.
4. **DNS는 캐시 계층이 깊다.** stub(127.0.0.53) → 재귀 리졸버 → 권위 NS. TXT 갱신이 "안 보이는" 건
   대개 전파가 아니라 **중간 캐시 TTL** 때문. ACME 디버깅에 `dig +trace`로 권위까지 직접 보는 습관이 중요.

### 보안 관점
5. **DNS-01은 자동화의 열쇠이자 권한 위임의 위험이다.**
   - 와일드카드·내부망 인증서를 포트 노출 0으로 받는 대신, DNS API 토큰이 새면 **임의 도메인 인증서
     발급**으로 이어진다. 토큰은 `_acme-challenge` TXT만 건드리도록 최소권한으로, CAA로 CA를 못박아
     blast radius를 줄여야 한다.
6. **인증서 갱신의 본질은 "도메인 소유권의 주기적 재증명"이다.**
   - certbot이 부리는 마법은 없다. token+thumbprint를 SHA256해서 TXT에 박는 단순 해시(§PoC③)일 뿐.
     원리를 알면 갱신 실패 시 "TXT 값이 틀렸나 / 전파가 안 됐나 / CA가 다른 NS를 보나"로 빠르게 분해된다.
