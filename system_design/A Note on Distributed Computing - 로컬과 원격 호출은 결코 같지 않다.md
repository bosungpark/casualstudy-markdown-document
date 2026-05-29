# A Note on Distributed Computing - 로컬과 원격 호출은 결코 같지 않다

## 출처

- **아티클/논문**: A Note on Distributed Computing (Sun Microsystems Laboratories Technical Report, 1994)
- **저자**: Jim Waldo, Geoff Wyant, Ann Wollrath, Sam Kendall
- **링크**: [https://scholar.harvard.edu/files/waldo/files/waldo-94.pdf](https://scholar.harvard.edu/files/waldo/files/waldo-94.pdf)
- **부가 자료**: [Medium - Paper Readings](https://medium.com/paper-readings/a-note-on-distributed-computing-e27525f1123), [Hacker News 토론](https://news.ycombinator.com/item?id=34245875)

---

## AI 요약

### 이 논문의 본질

이 논문은 "분산 시스템을 잘 만드는 법"에 대한 글이 아니다.
**"분산 호출을 로컬 호출처럼 보이게 하려는 모든 시도는 결국 실패한다"** 는 정면 반박이다.

핵심 메시지:

> **로컬 객체와 원격 객체는 인터페이스 수준에서 다르게 다뤄야 한다.**
> 같게 만들려는 순간, robustness와 reliability가 무너진다.

1994년 글이지만 **NFS, CORBA, Java RMI, gRPC, Service Mesh** 까지 지난 30년의 모든 "투명성(transparency)" 시도에 대한 사전 부검(pre-mortem)으로 읽힌다.

---

### 1. 논문이 공격하는 대상: "Vision of Unified Objects"

당시(1990s 초) 산업계는 다음 비전을 믿고 있었다:

```
+-------------------------------------------------+
| "객체는 객체다. 로컬이든 원격이든 차이는 구현일 뿐" |
+-------------------------------------------------+
              |
              v
+-------------------------------------------------+
| 1. 동일 설계가 배포 위치와 무관하게 동작한다       |
| 2. 실패/성능은 "나중에 최적화"할 구현 디테일이다    |
| 3. 인터페이스는 컨텍스트와 독립적이다             |
+-------------------------------------------------+
```

저자들은 이 세 전제 모두를 **근본적으로 잘못됐다**고 본다.

**비유**: 로컬과 원격은 "느린 자동차 vs 빠른 자동차"가 아니라 **"자동차 vs 비행기"**다.
같은 인터페이스로 운전할 수 있을 것 같지만, 고도·실속·기상 같은 새로운 변수가 본질적으로 다르다.

---

### 2. 네 가지 근본적 차이 (The Four Differences)

논문의 가장 유명한 부분. 단순한 성능 차이가 아니라 **인터페이스 설계 자체를 바꿔야 하는** 차이들이다.

| 차이 | 본질 | 인터페이스에 강제되는 것 |
|---|---|---|
| **Latency** | 4~5 자릿수 차이 (ns vs ms) | 동기 호출 깊이 제한, 배치/파이프라이닝 |
| **Memory Access** | 포인터가 주소공간을 못 넘어감 | call-by-reference vs call-by-value 명시 |
| **Partial Failure** | 한쪽만 죽을 수 있음 | 모든 호출은 실패 가능 시그니처 |
| **Concurrency** | 외부 호출자 동시성 통제 불가 | 모든 객체가 동시 호출 안전해야 함 |

#### 2-1. Latency (지연)

```
로컬 메서드 호출:    ~ns  (CPU cycle)
원격 메서드 호출:    ~ms  (TCP RTT + serialization)
                  ──────
                  10,000x ~ 1,000,000x 차이
```

**핵심 주장**: 이건 "느린 함수"가 아니라 **다른 종류의 연산**이다.

- 무어의 법칙으로 CPU는 빨라져도 빛의 속도는 안 빨라진다 → 차이는 **줄지 않고 벌어진다**
- "나중에 최적화"가 안 됨 → 호출 횟수 자체가 설계 변수
- 동기 RPC 체인 10단 = P99 폭발

**설계 강제**:
- 한 번에 가져올 데이터를 미리 결정 (chatty → chunky)
- batch / pipeline / async를 인터페이스에 노출
- "투명한 지연"은 환상

#### 2-2. Memory Access (메모리 접근)

**가장 미묘하지만 가장 치명적인 차이**.

```c
// 로컬에서는 합법
void process(Buffer* b) {
    b->data[0] = 42;   // 같은 주소공간 → OK
}

// 원격이면?
// - 포인터를 보낸다? → 상대 주소공간에서 무효
// - 객체 전체 복사? → 의미가 달라짐 (call-by-value)
// - 객체 참조 발급? → 분산 GC, lease, 네트워크 라운드트립
```

**저자들의 경고**:

> "The danger lies in promoting the myth that *remote access and local access are exactly the same*."

이걸 숨기려면 시스템이 **distributed shared memory** 같은 거대한 추상화를 깔아야 하는데, 그 추상화 자체가 새로운 실패 모드(페이지 폴트가 네트워크 장애로 변함)를 만든다.

**결론**: 인터페이스에서 **"이 인자는 값으로 갈까, 참조로 갈까"** 를 명시적으로 드러내야 한다.

#### 2-3. Partial Failure (부분 실패) — 논문의 핵심

저자들이 "**the central reality of distributed computing**" 이라고 부른 것.

**로컬 시스템**:
```
process → 전체가 살아있거나 전체가 죽는다 (fail-stop)
        → 모니터(OS)가 상태를 안다
```

**분산 시스템**:
```
   Client                       Server
     |                            |
     |---- request --------->     |
     |                          [죽음]
     |       ???? <---- 응답 X
     |
     |  '응답이 늦는 것'인지
     |  '서버가 죽은 것'인지
     |  '네트워크가 끊긴 것'인지
     |  '내 요청이 도착은 한 건지'
     |  알 방법이 없다.
```

**왜 본질적인가**:
- 공통 관찰자(common observer)가 없다 → "지금 누가 살아있나"를 묻는 주체 자체가 부분이다
- 실패는 **확률적이고 비결정적**이다
- "성공도 실패도 아닌" 상태(in doubt)가 정상 상태로 존재

**인터페이스 강제**:
- 모든 원격 호출 시그니처에 **실패 가능성**이 노출돼야 함 (`RemoteException`, `Result<T, E>`)
- 멱등성(idempotency)은 선택이 아닌 필수
- "성공했는지 모르겠다"를 비즈니스 로직이 처리해야 함

> **로컬 호출은 "리턴값이 온다"가 기본.
> 원격 호출은 "리턴값이 안 올 수도 있다"가 기본.**
> 이 차이는 라이브러리로 숨길 수 없다.

#### 2-4. Concurrency (동시성)

```
로컬 객체:
   호출자가 누군지 안다 → 락 전략 설계 가능

원격 객체:
   누가 언제 호출할지 모른다 → 항상 동시 호출 가능
   → 객체는 본질적으로 monitor-like 해야 함
```

로컬 객체는 호출 순서를 통제할 수 있지만, 원격 객체는 **외부 클라이언트들이 임의 순서로 동시에 때린다**. 동시성 제어가 객체 인터페이스의 일부가 된다.

---

### 3. 핵심 비판: Transparency는 거짓말이다

저자들의 가장 강한 주장:

```
+----------------------------------------------------+
|  "프로그래머에게 분산을 숨기면 편할 것"이라는 환상은    |
|   결국 "프로그래머가 분산을 모른 채 분산을 짜는" 재앙으로 |
|   귀결된다.                                          |
+----------------------------------------------------+
```

문제의 구조:

| 단계 | 일어나는 일 |
|---|---|
| 1. 평상시 | 로컬처럼 동작 → 개발자가 분산임을 잊음 |
| 2. 코드량 ↑ | 분산을 가정 안 한 패턴이 쌓임 (포인터, 동기 호출, 가정된 일관성) |
| 3. 장애 발생 | 한 곳 끊김 → 갑자기 모든 추상화가 새기 시작 |
| 4. 디버깅 | 추상화가 숨긴 변수들이 한꺼번에 튀어나옴 |

**저자들의 결론**: 차라리 **인터페이스 레벨에서부터 "이건 원격이다"라고 외쳐야** 한다. 늦게 깨닫는 것보다 처음부터 인지하는 비용이 훨씬 싸다.

---

### 4. 사례: NFS — 잘못된 투명성의 교과서

논문에서 가장 자세히 분석되는 케이스 스터디.

**NFS의 약속**:
> "로컬 파일시스템처럼 보이게 하겠다. `open/read/write`가 똑같이 동작한다."

**실제로 일어난 일**:

```
1. 정상일 때:
   read(fd, buf, n) → 그냥 동작 → 개발자 행복

2. 서버가 죽었을 때:
   read(fd, buf, n) → 영원히 block
                   → Ctrl+C도 안 먹힘 (uninterruptible sleep)
                   → load average 폭주, CPU는 0%
                   → 시스템 전체가 hang

3. 부분 장애일 때:
   stat() 한 번이 수십 ms
   → symlink 체인 따라가면 호출당 수십 번 stat()
   → 평범한 `ls`가 분 단위로 걸림
```

**무엇이 무너졌나**:
- POSIX 파일 API는 **fail-fast하지 않다** → 무한 대기 가능
- 인터럽트 모델이 네트워크 실패와 안 맞음
- 캐시 일관성이 NFS 세만틱과 충돌 (stale handle, close-to-open consistency)

**교훈**: 인터페이스를 그대로 두고 구현만 분산으로 바꿨더니, **인터페이스가 표현하지 못하는 새 실패 모드들**이 시스템 곳곳에서 새어나옴.

> Hacker News 댓글: *"NFS는 분산 컴퓨팅을 잘못 하는 법의 정전(canonical example)이다."*

대조군 — **Google GFS**는 의도적으로 커널 투명성을 포기하고, 클라이언트가 **명시적으로 GFS 라이브러리를 링크**하게 만들었다. "이건 원격이다"를 코드에 박았다.

---

### 5. 그래서 무엇을 하란 말인가

논문이 처방으로 제시하는 것:

| 원칙 | 의미 |
|---|---|
| **인터페이스 분리** | 로컬용 인터페이스와 원격용 인터페이스를 다르게 설계 |
| **실패를 시그니처에** | 원격 호출은 항상 실패 가능성을 타입으로 노출 |
| **데이터 모델 명시** | call-by-value/by-reference를 인터페이스에서 결정 |
| **동시성 가정** | 모든 원격 객체는 동시 호출 안전이 기본 |
| **지연을 비용으로** | "몇 번 호출하는가" 자체가 설계 결정 |

**핵심 문장**:

> "Objects that interact in a distributed system **need to be dealt with in ways that are intrinsically different** from objects that interact in a single address space."

번역하면: **"분산은 구현 디테일이 아니라 설계 변수다."**

---

## 내가 얻은 인사이트

### 엔지니어 관점

1. **"투명성"은 거의 항상 결제 미루기**
   - 분산을 숨긴 추상화는 평상시엔 편하지만, 장애 때 **모든 비용을 한꺼번에 청구**한다.
   - NFS hang, ORM의 N+1, 마이크로서비스의 cascade failure, gRPC deadline 누락 — 본질은 다 같은 패턴이다.
   - **"몰라도 돌아간다"는 "장애 때 모르면 못 고친다"의 다른 말**이다.

2. **실패는 타입에 박혀야 한다**
   - `Result<T, E>` / `Either` / `Try` / Java의 checked exception — 다 같은 직관이다.
   - 원격 호출이 `T`를 리턴하면 거짓말이고, `Result<T, NetworkError>`를 리턴해야 정직하다.
   - 컴파일러가 "넌 실패를 처리해야 해"라고 강제하는 게 30년 전 논문의 처방이었다.

3. **N+1 문제는 latency 차이의 직접 증명**
   - ORM에서 `for user in users: user.orders` 같은 코드가 로컬 객체라면 무해하다.
   - 원격(DB) 호출이 되는 순간 **호출 횟수가 비용**이 된다.
   - "동일 인터페이스"의 비용이 가장 비싸게 드러나는 일상 사례.

### 아키텍처 관점

1. **마이크로서비스 = Waldo가 경고한 그 환상의 재림**
   - "REST/gRPC면 함수 호출처럼 짜면 된다"는 말은 1994년 RPC의 메아리다.
   - 한 모놀리스를 30개 마이크로서비스로 쪼개는 순간, 모든 함수 호출이 latency·partial failure·concurrency 문제를 떠안는다.
   - **서비스 경계는 함수 경계가 아니라 실패 경계**다. 이 차이를 모르고 자르면 분산 모놀리스가 된다.

2. **Service Mesh, Circuit Breaker, Retry — 다 Waldo의 4가지에 대응한다**
   - Latency → timeout, deadline propagation, hedged request
   - Memory Access → schema (protobuf, JSON Schema)로 명시
   - Partial Failure → circuit breaker, bulkhead, retry with backoff
   - Concurrency → idempotency key, exactly-once 시도
   - 30년이 지났지만 우리는 여전히 같은 4개 변수와 싸우고 있다.

3. **GFS / S3가 NFS와 다른 결정적 차이**
   - GFS와 S3는 **분산임을 인터페이스에 박았다**.
   - S3는 `PUT/GET` API, eventual consistency를 처음부터 노출 (지금은 strong이지만 클라이언트 모델은 그대로).
   - 로컬 파일시스템 흉내를 내지 않은 게 핵심 성공 요인이다.
   - "투명한 분산 파일시스템"을 만들려는 모든 후속 시도(Ceph FUSE, JuffleFS 등)가 지금도 NFS의 hang 문제를 변형 형태로 겪고 있다.

### 메타 관점

1. **"새로운 기술"은 보통 같은 환상의 재포장**
   - CORBA(90s) → EJB → Java RMI → SOAP → REST → gRPC → Service Mesh → "Serverless Functions"
   - 각 세대마다 "이번엔 진짜 분산을 투명하게 만들었다"고 주장한다.
   - Waldo 논문을 읽고 나면 어떤 신기술 발표를 보든 **"이 추상화는 4개 차이 중 무엇을 숨기려 하는가? 숨겨진 비용은 어디로 가는가?"** 라는 질문이 자동으로 떠오른다.

2. **"좋은 분산 시스템 책"의 절반은 이 논문의 각주다**
   - DDIA(Designing Data-Intensive Applications)의 ch.8 "분산 시스템의 곤란함"이 다루는 — clock skew, partial failure, network 비신뢰성 — 거의 다 1994년에 짧게 정리돼 있다.
   - End-to-End Arguments(1984), Fallacies of Distributed Computing(1994), 그리고 이 논문이 **분산 시스템 사고의 헌법**처럼 묶여있다.

3. **"분산은 다르다"는 인식이 곧 시니어리티의 절반**
   - 주니어가 만든 분산 코드의 버그 90%는 "로컬처럼 가정"에서 나온다.
   - 시니어가 하는 일의 절반은 그 가정을 짚어내는 것이다.
   - 이 논문은 그 시니어의 직관을 8페이지 PDF로 압축해놓은 문서다.

> **30년 전 글인데 오늘 마이크로서비스 PR 리뷰에서 그대로 쓸 수 있다.
> 이게 좋은 논문의 정의다.**
