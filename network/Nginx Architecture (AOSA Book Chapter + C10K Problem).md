# Nginx Architecture (AOSA Book Chapter + C10K Problem)

## 출처
- **제목**: The Architecture of Open Source Applications (Volume 2) - nginx
- **저자**: Andrew Alexeev
- **링크**: https://aosabook.org/en/v2/nginx.html
- **관련 문서**: The C10K Problem by Dan Kegel (https://www.kegel.com/c10k.html)

---

## AI 요약

### Nginx란?

Nginx(발음: "engine x")는 Igor Sysoev가 개발한 오픈소스 웹 서버. 2004년 공개 이후 **고성능, 고동시성, 저메모리 사용**에 집중. 웹 서버 기능 외에도 로드 밸런싱, 캐싱, 접근 제어, 대역폭 제어 등을 제공.

### C10K 문제란?

**C10K (10,000 Concurrent Connections)**: 1999년 Dan Kegel이 제기한 문제로, 단일 서버에서 10,000개의 동시 연결을 처리해야 하는 과제.

```
문제의 핵심:
- 하드웨어는 충분: 1GHz CPU, 2GB RAM, 1Gbps NIC → $1,200
- 20,000 클라이언트 = 클라이언트당 50KHz, 100KB, 50Kbps
- 병목은 소프트웨어 아키텍처!
```

### Apache의 한계

```
[Apache의 프로세스 모델]
클라이언트 요청 → 새 프로세스/스레드 생성 → 요청 처리 → 프로세스 종료

문제점:
- 연결당 1MB+ 메모리 할당
- 1,000 클라이언트 × 1MB = 1GB 메모리
- Slow client 문제: 100KB 컨텐츠, 80kbps 클라이언트 → 10초 점유
- Context switching 오버헤드
- 비선형 확장성
```

### Nginx의 해결책: Event-Driven Architecture

```
[Nginx의 이벤트 기반 모델]
                    ┌─────────────────────────────────────┐
                    │           Master Process            │
                    │  - 설정 파일 읽기/검증               │
                    │  - 소켓 생성/바인딩                  │
                    │  - Worker 프로세스 관리              │
                    │  - 무중단 재설정                     │
                    └─────────────┬───────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│    Worker 1   │       │    Worker 2   │       │    Worker N   │
│  (single-     │       │  (single-     │       │  (single-     │
│   threaded)   │       │   threaded)   │       │   threaded)   │
│               │       │               │       │               │
│ ┌───────────┐ │       │ ┌───────────┐ │       │ ┌───────────┐ │
│ │Event Loop │ │       │ │Event Loop │ │       │ │Event Loop │ │
│ │           │ │       │ │           │ │       │ │           │ │
│ │ epoll/    │ │       │ │ epoll/    │ │       │ │ epoll/    │ │
│ │ kqueue    │ │       │ │ kqueue    │ │       │ │ kqueue    │ │
│ └───────────┘ │       │ └───────────┘ │       │ └───────────┘ │
│               │       │               │       │               │
│ 수천 개 연결   │       │ 수천 개 연결   │       │ 수천 개 연결   │
└───────────────┘       └───────────────┘       └───────────────┘
```

### 핵심 설계 원칙

| Apache | Nginx |
|--------|-------|
| 프로세스/스레드 per 연결 | 이벤트 기반, 비동기 |
| 블로킹 I/O | Non-blocking I/O |
| 연결당 메모리 1MB+ | 연결당 메모리 ~550 bytes (idle) |
| 선형 확장 | 비선형 확장 (수만 연결 가능) |
| 범용 목적 | 고성능 특화 |

### Worker 프로세스 모델

```c
// Nginx Worker의 핵심 루프 (개념적)
while (true) {
    // 1. epoll/kqueue로 이벤트 대기
    events = epoll_wait(epfd, events, MAX_EVENTS, timeout);
    
    // 2. 준비된 이벤트 처리
    for (event in events) {
        if (event.type == NEW_CONNECTION) {
            accept_connection(event.fd);
            add_to_event_loop(new_fd);
        }
        else if (event.type == READ_READY) {
            read_request(event.fd);
            process_request(event.fd);
        }
        else if (event.type == WRITE_READY) {
            send_response(event.fd);
        }
    }
    
    // 3. 타이머 처리
    process_timers();
}
```

**특징**:
- **단일 스레드**: 각 Worker는 단일 스레드로 수천 개 연결 처리
- **Non-blocking**: 모든 I/O 작업이 비동기
- **No context switching**: 프로세스/스레드 생성 없음
- **CPU 코어당 1개 Worker**: 멀티코어 활용

### 프로세스 역할

| 프로세스 | 역할 |
|----------|------|
| **Master** | 설정 읽기/검증, Worker 생성/관리, 소켓 바인딩, 시그널 처리, 무중단 업그레이드 |
| **Worker** | 클라이언트 연결 수락/처리, 리버스 프록시, 필터링, 실제 작업 수행 |
| **Cache Loader** | 디스크 캐시를 메모리 메타데이터로 로드 (시작 시 1회) |
| **Cache Manager** | 캐시 만료/무효화 관리 |

### I/O Multiplexing 메커니즘

```
┌─────────────────────────────────────────────────────────────┐
│                    I/O Multiplexing 진화                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  select() ──────► poll() ──────► epoll/kqueue               │
│                                                             │
│  • FD_SETSIZE      • 제한 없음      • O(1) 이벤트 알림       │
│    제한 (1024)     • O(n) 스캔      • Edge/Level trigger     │
│  • O(n) 스캔       • 매번 전체       • 커널에 관심 FD 등록    │
│  • 매번 복사         전달 필요       • 변경분만 전달          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**OS별 최적 메커니즘**:
- **Linux**: epoll (2.6+)
- **FreeBSD/macOS**: kqueue
- **Solaris**: /dev/poll, event ports

### Level-Triggered vs Edge-Triggered

```
Level-Triggered (select, poll):
  "데이터가 있으면 계속 알려줌"
  → 읽지 않으면 다음 poll()에서도 ready
  → 프로그래밍 쉬움, 성능 낮음

Edge-Triggered (epoll EPOLLET, kqueue):
  "상태가 변할 때만 알려줌"
  → not-ready → ready 전환 시에만 알림
  → 반드시 EAGAIN까지 읽어야 함
  → 프로그래밍 어려움, 성능 높음
```

### 모듈 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx Core                           │
│  - Run-loop 관리                                            │
│  - 모듈 실행 조율                                            │
│  - 기본 인프라                                               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ Event Modules │     │  HTTP Module  │     │  Mail Module  │
│               │     │               │     │               │
│ • epoll       │     │ • 요청 처리    │     │ • SMTP        │
│ • kqueue      │     │ • 필터 체인    │     │ • POP3        │
│ • select      │     │ • 업스트림     │     │ • IMAP        │
└───────────────┘     └───────────────┘     └───────────────┘
                              │
        ┌─────────┬─────────┬─┴─────────┬─────────┐
        │         │         │           │         │
        ▼         ▼         ▼           ▼         ▼
    Phase      Output    Variable   Upstream    Load
   Handlers    Filters   Handlers    Modules   Balancers
```

### HTTP 요청 처리 흐름

```
1. 클라이언트 → HTTP 요청
2. Nginx Core → location 매칭으로 Phase Handler 선택
3. Phase Handler → 로드 밸런서가 upstream 서버 선택 (프록시 시)
4. Phase Handler → 출력 버퍼 생성 → 첫 번째 필터로 전달
5. 필터 체인 → 순차 처리 (gzip, SSI, charset 등)
6. 최종 응답 → 클라이언트

┌─────────────────────────────────────────────────────────────┐
│                    HTTP 처리 단계 (Phases)                   │
├─────────────────────────────────────────────────────────────┤
│ 1. Server Rewrite Phase                                     │
│ 2. Location Phase (location 블록 매칭)                       │
│ 3. Location Rewrite Phase (→ 2번으로 되돌아갈 수 있음)        │
│ 4. Access Control Phase (인증/인가)                          │
│ 5. Try_files Phase                                          │
│ 6. Content Phase (실제 콘텐츠 생성)                          │
│ 7. Log Phase                                                │
└─────────────────────────────────────────────────────────────┘
```

### 필터 체인

```
Content Handler
      │
      ▼
┌─────────────┐
│ Header Filter│ → 응답 헤더 조작
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  gzip Filter │ → 압축
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Chunked Filter│ → Transfer-Encoding
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ SSI Filter   │ → Server Side Include
└──────┬──────┘
       │
       ▼
    Client

특징: Unix 파이프라인처럼 동작
- 이전 필터 완료 대기 불필요
- 입력 도착 즉시 다음 필터 시작
- 스트리밍 응답 가능
```

### 캐싱 구조

```
┌─────────────────────────────────────────────────────────────┐
│                      Nginx Caching                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Shared Memory                      Filesystem              │
│  ┌─────────────────┐               ┌─────────────────┐      │
│  │ Cache Metadata  │               │  /var/cache/    │      │
│  │ ─────────────── │               │  nginx/         │      │
│  │ • Cache Keys    │◄─────────────►│  ├── a/b/      │      │
│  │ • Expiration    │               │  │   └── hash1 │      │
│  │ • Access Count  │               │  ├── c/d/      │      │
│  └─────────────────┘               │  │   └── hash2 │      │
│         ▲                          │  └── ...       │      │
│         │                          └─────────────────┘      │
│  ┌──────┴──────┐                                            │
│  │Cache Manager│ → 만료/무효화                               │
│  │Cache Loader │ → 시작 시 메타데이터 로드                   │
│  └─────────────┘                                            │
│                                                             │
│  Cache Key = MD5(proxy_url)                                 │
│  Directory = /cache/a/b/MD5hash (계층적)                    │
└─────────────────────────────────────────────────────────────┘
```

### 설정 구조

```nginx
# C-style 문법, 중첩 컨텍스트, 중앙 집중식

main                              # 전역 설정
├── events { }                    # 이벤트 처리 설정
├── http {                        # HTTP 서버 설정
│   ├── upstream backend { }      # 업스트림 서버 그룹
│   ├── server {                  # 가상 호스트
│   │   ├── location / { }        # URI 매칭
│   │   ├── location /api { }
│   │   └── location ~* \.php$ { }
│   │   }
│   └── server { }                # 다른 가상 호스트
│   }
└── mail { }                      # 메일 프록시 설정

특징:
- .htaccess 같은 분산 설정 없음 (성능상 이유)
- 설정 변경 → Master가 검증 → Worker에 전파
- 무중단 재설정 (reload) 지원
```

### 메모리 관리

```
┌─────────────────────────────────────────────────────────────┐
│                    Memory Management                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Pool Allocator                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │ Connection Pool                                 │        │
│  │ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐               │        │
│  │ │Buf 1│→│Buf 2│→│Buf 3│→│Buf 4│→ ...         │        │
│  │ └─────┘ └─────┘ └─────┘ └─────┘               │        │
│  │                                                 │        │
│  │ • 연결 수명 동안 할당                            │        │
│  │ • 연결 종료 시 해제                              │        │
│  │ • Zero-copy: 포인터 전달, memcpy 최소화          │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  Shared Memory (프로세스 간 공유)                            │
│  ┌─────────────────────────────────────────────────┐        │
│  │ • Mutex, Semaphore                              │        │
│  │ • Cache Metadata                                │        │
│  │ • SSL Session Cache                             │        │
│  │ • Rate Limiting 정보                            │        │
│  │ • Slab Allocator로 관리                         │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  Idle Keepalive Connection: ~550 bytes only!                │
└─────────────────────────────────────────────────────────────┘
```

### Upstream과 Load Balancing

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancing                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  upstream backend {                                         │
│      server 10.0.0.1:8080 weight=5;                        │
│      server 10.0.0.2:8080 weight=3;                        │
│      server 10.0.0.3:8080 backup;                          │
│  }                                                          │
│                                                             │
│  알고리즘:                                                   │
│  • Round Robin (기본)                                       │
│  • IP Hash (세션 유지)                                      │
│  • Least Connections                                        │
│  • Generic Hash                                             │
│                                                             │
│  Health Check:                                              │
│  • Passive: 실패 감지 → 제외                                │
│  • max_fails, fail_timeout 설정                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## C10K 문제 해결 전략 (Dan Kegel 정리)

### I/O 전략 비교

| 전략 | 설명 | 예시 |
|------|------|------|
| **Thread per client** | 연결당 스레드 생성 | Apache prefork |
| **Non-blocking + Level-triggered** | select/poll로 준비된 FD 확인 | 전통적 이벤트 서버 |
| **Non-blocking + Edge-triggered** | epoll/kqueue로 상태 변화 감지 | **Nginx**, libevent |
| **Async I/O (AIO)** | 커널이 완료 시 알림 | io_uring, IOCP |
| **In-kernel server** | 서버 로직을 커널에 | TUX, khttpd |

### Nginx가 선택한 전략

```
Non-blocking I/O + Edge-triggered readiness notification
+ Single-threaded event loop per CPU core

이유:
1. 컨텍스트 스위칭 최소화
2. 메모리 효율성 (스택 공간 절약)
3. 캐시 지역성 향상
4. 락 경쟁 최소화
```

---

## 내가 얻은 인사이트

### 1. "문제 정의"의 힘

C10K는 단순히 "10,000 연결"이 아니라, 기존 아키텍처의 근본적 한계를 드러내는 벤치마크였음. Igor Sysoev는 이 문제를 정확히 이해하고 해결책을 설계.

```
Apache의 가정: 연결은 비싸다 → 프로세스로 격리
Nginx의 가정: 연결은 싸다 → 이벤트로 멀티플렉싱

가정이 바뀌면 아키텍처가 바뀜
```

### 2. "하나를 잘하라" (Lampson's Hint)

Nginx는 범용성 대신 고성능에 집중:
- 동적 모듈 로딩 없음 (컴파일 타임 결정)
- .htaccess 없음 (분산 설정 오버헤드 제거)
- Windows 지원은 "proof-of-concept" 수준

```
Apache: 모든 것을 할 수 있음 → 느림
Nginx: 잘하는 것만 함 → 빠름
```

### 3. End-to-End 원칙 적용

캐싱, 로드 밸런싱, SSL 종단을 "edge"에서 처리:

```
[Client] ←→ [Nginx Edge] ←→ [Application Servers]
              │
              ├── SSL Termination
              ├── Caching
              ├── Compression
              ├── Load Balancing
              └── Rate Limiting

Application Server는 비즈니스 로직에만 집중
```

### 4. 점진적 개선의 중요성

Igor Sysoev의 접근:
1. 2002년: 프로토타입 시작
2. 2004년: 첫 공개 릴리스
3. 이후 10년: 지속적 최적화
4. 현재: 2.0 프로토타입 개발 중

```
"초기 프로토타입과 코드 구조가
소프트웨어 제품의 미래에 결정적"
```

### 5. 올바른 추상화 수준

Nginx 설정이 Apache보다 직관적인 이유:

```nginx
# Nginx: 선언적, 계층적
location /api {
    proxy_pass http://backend;
}

# Apache: 명령적, 분산
<Directory /var/www>
    Options +FollowSymLinks
    RewriteEngine On
    RewriteRule ^api/(.*)$ http://backend/$1 [P]
</Directory>
```

---

## Apache vs Nginx 아키텍처 비교

```
┌─────────────────────────────────────────────────────────────┐
│                    Apache (prefork)                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Request 1 ──► [Process 1] ──► Response 1                  │
│   Request 2 ──► [Process 2] ──► Response 2                  │
│   Request 3 ──► [Process 3] ──► Response 3                  │
│       ...           ...            ...                      │
│   Request N ──► [Process N] ──► Response N                  │
│                                                             │
│   메모리: N × ~1MB                                          │
│   Context Switch: 많음                                      │
│   확장성: 선형 (메모리 한계)                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Nginx (event-driven)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Request 1 ─┐                                              │
│   Request 2 ─┼──► [Worker 1] ──► Responses                  │
│   Request 3 ─┘    (Event Loop)                              │
│                                                             │
│   Request 4 ─┐                                              │
│   Request 5 ─┼──► [Worker 2] ──► Responses                  │
│   Request 6 ─┘    (Event Loop)                              │
│                                                             │
│   메모리: 고정 (Worker 수에 비례)                            │
│   Context Switch: 최소                                      │
│   확장성: 비선형 (수만 연결 가능)                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 현대적 의의

### Nginx가 영향을 준 것들

- **Node.js**: 단일 스레드 이벤트 루프
- **Go**: goroutine + epoll 기반 네트워킹
- **Envoy**: 현대적 L7 프록시
- **HAProxy**: 고성능 로드 밸런서

### 남은 과제

1. **Disk I/O 블로킹**: sendfile()도 페이지 폴트 시 블로킹
2. **임베디드 스크립팅**: Lua (OpenResty) 등으로 해결 중
3. **HTTP/3 (QUIC)**: UDP 기반으로 아키텍처 변화 필요
