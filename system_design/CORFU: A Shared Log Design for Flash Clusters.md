# **CORFU: A Shared Log Design for Flash Clusters (NSDI’12)**

## 출처

* **링크**: [https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/balakrishnan](https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/balakrishnan)
* **PDF**: [https://www.usenix.org/system/files/conference/nsdi12/nsdi12-final30.pdf](https://www.usenix.org/system/files/conference/nsdi12/nsdi12-final30.pdf)

---

## AI 요약

### 1. 문제 정의: “로그”가 병목이 되는 이유

기존 분산 시스템에서 **글로벌 순서를 가진 로그**는 항상 다음 중 하나를 선택해왔다.

* **중앙 로그 서버**
  → ordering은 쉬움, 하지만 *throughput / fault tolerance / scale*에서 병목
* **분산 합의 기반 로그 (Paxos/Raft)**
  → ordering + fault tolerance는 확보
  → 하지만 *append 하나당 합의* → latency·throughput 모두 비쌈

논문의 핵심 질문은 명확하다.

> *“강한 전역 순서를 유지하면서도, 로그 append를 scale-out할 수 없는가?”*

CORFU의 답은 **“ordering과 storage를 분리하자”** 이다.

---

### 2. CORFU의 핵심 아이디어

#### (1) **로그는 ‘순서’와 ‘데이터’를 분리할 수 있다**

CORFU는 로그를 다음 두 문제로 쪼갠다.

1. **어떤 append가 몇 번째 위치인가?** → *Ordering*
2. **그 데이터는 어디에 저장되는가?** → *Storage*

기존 시스템은 이 둘을 한 컴포넌트에서 해결하려 했고, 그게 병목이었다.

CORFU에서는:

| 책임         | 담당                               |
| ---------- | -------------------------------- |
| 로그 위치 할당   | **Sequencer**                    |
| 실제 데이터 쓰기  | **Flash storage cluster**        |
| 위치→스토리지 매핑 | **Projection Map (client-side)** |

이 분리가 CORFU의 모든 성질을 결정한다.

---

### 3. 로그 Append의 실제 흐름

**Append 하나가 실제로 어떻게 처리되는지**를 단계별로 보면:

#### Step 1. Sequencer에게 토큰 요청

* 클라이언트는 “다음 로그 위치”를 요청
* Sequencer는 **monotonic increasing token** 반환
* 이 시점에는 **아직 데이터 쓰기 X**

👉 Sequencer는 *ordering only*
👉 데이터 payload를 절대 보지 않음 → bottleneck 최소화

---

#### Step 2. Projection Map으로 물리 위치 결정

* 클라이언트는 `(log position → flash nodes chain)`을
  **자기 로컬 Projection Map**에서 계산
* 이 맵은 **epoch 단위**로 관리됨 (configuration version)

👉 스토리지는 dumb
👉 클라이언트가 “어디에 쓸지”를 알고 있음

---

#### Step 3. Chain Replication으로 기록

* 해당 로그 위치는 **f+1개의 flash node 체인**에 기록
* Head → Tail 순으로 데이터 전파
* Tail write 완료 시 **append 성공**

여기서 중요한 점:

* 서로 다른 로그 위치는 **완전히 병렬 append 가능**
* ordering은 이미 Step 1에서 끝났기 때문에 충돌 없음

---

### 4. “강한 일관성”은 어디서 오나?

CORFU의 strong consistency는 **storage가 아니라 log ordering에서 온다.**

* 모든 append는 **총순서(total order)**를 가진다
* 어떤 reader든:

  * log position *i*를 읽으면
  * 반드시 *i 이전의 모든 append*가 보장됨

즉 CORFU는:

> **Shared log = single global serialization point**

이 성질 덕분에:

* SMR
* 트랜잭션
* 키-값 스토어
  를 로그 위에 얹을 수 있다.

---

### 5. Failure / Corner Case

#### (1) Client crash → 로그 hole

클라이언트가:

* Sequencer에서 토큰을 받아놓고
* 실제 write 전에 죽으면?

→ **log hole 발생**

CORFU의 해결:

* 다른 클라이언트가 `fill(position)` 수행
* hole에 **special no-op entry**를 기록
* 이후 log는 정상 진행

👉 이걸 명시적으로 API 레벨에서 다룬다는 점이 중요

---

#### (2) Sequencer failure

Sequencer는 state가 거의 없음:

* 단순히 monotonically increasing counter

실패 시:

* 새 sequencer election
* counter는 **storage를 scan하지 않아도 됨**
* epoch 증가로 stale token 무효화

👉 sequencer는 hot path지만 *recovery는 가볍다*

---

#### (3) Storage failure

* chain replication 기반 → f개까지 tolerance
* reconfiguration 시:

  * **Projection Map epoch 증가**
  * 클라이언트가 새 map으로 전환

---

### 6. Get / Read는 왜 빠른가

* Reads는 **sequencer를 전혀 거치지 않음**
* 클라이언트가 projection map으로 직접 flash node 접근
* 서로 다른 log position read는 완전 병렬

결과:

* read throughput은 **클러스터 크기에 선형 비례**

---

### 7. 성능 결과

논문에서 강조하는 포인트는 단순 “빠르다”가 아니다.

* append throughput:

  * **수십만 ops/sec**
  * 서버 수 증가 시 계속 증가
* latency:

  * Paxos 기반 로그 대비 **order of magnitude 감소**
* sequencer CPU 사용률:

  * 매우 낮음 → ordering만 담당하기 때문

👉 “central ordering ≠ bottleneck”을 실험으로 증명

---

## 내가 얻은 인사이트

### 1. CORFU는 “로그 시스템”이 아니라 **아키텍처 패턴**

* ordering과 storage를 분리하면
* strong consistency도 scale할 수 있다는 증명

### 2. Client-driven 설계의 극단

* CORFU는 서버를 똑똑하게 만들지 않는다
* **클라이언트를 똑똑하게 만든다**
  → 이후 시스템들(TiKV, FaRM, Calvin류)에 강한 영향

### 3. 로그는 단순한 append-only 파일이 아니다

* CORFU에서 로그는:

  * 일관성
  * 복제
  * 트랜잭션
    의 *기초 인프라*


> **CORFU는 “합의를 확장하지 말고, 합의의 역할을 쪼개라”.**
