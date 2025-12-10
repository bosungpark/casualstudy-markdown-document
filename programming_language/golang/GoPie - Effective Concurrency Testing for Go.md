# GoPie - Effective Concurrency Testing for Go via Directional Primitive-constrained Interleaving Exploration

## 출처
- **논문**: Effective Concurrency Testing for Go via Directional Primitive-constrained Interleaving Exploration
- **저자**: Zongze Jiang, Ming Wen, Yixin Yang, Chao Peng, Ping Yang, Hai Jin
- **게재**: ASE 2023 (38th IEEE/ACM International Conference on Automated Software Engineering)
- **원문**: https://chao-peng.github.io/publication/ase23/
- **GitHub**: https://github.com/Mskxn/GoPie

---

## AI 요약

### 핵심 문제: Go 동시성 버그 탐지의 어려움

Go는 **Channel 기반 동시성**을 권장하지만, 이는 **공유 메모리 동시성과 다른 새로운 버그**를 유발합니다:

**전통적 도구의 한계**:
```go
// Race Detector가 놓치는 버그
func worker(ch chan int, done chan bool) {
    for i := range ch {
        process(i)
    }
    done <- true  // Blocking Bug: ch가 닫히지 않으면 영원히 대기
}

func main() {
    ch := make(chan int)
    done := make(chan bool)
    go worker(ch, done)
    
    ch <- 1
    ch <- 2
    // close(ch) 누락! → Goroutine Leak
    
    <-done  // 영원히 블록됨
}
```

**문제**:
- **Race Detector**: Data Race만 탐지 (Channel Blocking은 못 잡음)
- **Random Testing**: Interleaving 조합 폭발 (2^N)
- **Exhaustive Search**: 현실적으로 불가능

### GoPie의 핵심 아이디어

**Primitive-Constrained Interleaving Exploration**:

1. **Primitive**: Channel Send/Receive, Lock, WaitGroup 같은 동시성 연산
2. **Constraint**: 실행 이력(Execution History)을 기반으로 탐색 방향 결정
3. **Directional**: 무작위가 아닌 **목적 지향적** 탐색

**기존 방식 vs GoPie**:

| 방식 | 탐색 전략 | 문제점 |
|------|----------|--------|
| Random Testing | 무작위 스케줄링 | 버그 발견 확률 낮음 |
| Exhaustive | 모든 Interleaving | 조합 폭발 (2^N) |
| **GoPie** | **이력 기반 방향성** | **효율적 탐색** |

### 작동 방식

**1단계: Execution History 수집**

```go
// 예시 프로그램
func main() {
    ch := make(chan int, 1)
    
    go func() {
        ch <- 1  // G1: Send
    }()
    
    go func() {
        <-ch     // G2: Receive
    }()
}
```

**실행 이력 기록**:
```
[G1: ch.Send(1), G2: ch.Receive()] → OK
```

**2단계: 새로운 Interleaving 생성**

```
기존: G1 → G2
새로운: G2 → G1 (Send보다 Receive 먼저)
```

**3단계: Primitive Constraint 적용**

```go
// Constraint: Receive는 Send 전에 실행 불가
G2 먼저 실행 → ch에 데이터 없음 → Blocking!
```

**탐지된 버그**: Channel Blocking Deadlock

### 실제 탐지 사례

**예시 1: Goroutine Leak**

```go
func leakyServer(requests chan Request) {
    for {
        req := <-requests  // 채널이 닫히지 않으면 영원히 대기
        go handleRequest(req)
    }
}

func main() {
    requests := make(chan Request)
    go leakyServer(requests)
    
    requests <- Request{ID: 1}
    // close(requests) 누락!
    
    // 프로그램 종료 시 leakyServer Goroutine이 살아있음
}
```

**GoPie 탐지**:
- Interleaving 탐색 중 `requests` 채널이 닫히지 않는 경로 발견
- Goroutine이 무한 대기 상태임을 확인
- **버그 보고**: Goroutine Leak

**예시 2: Select Starvation**

```go
func worker(high, low chan int, done chan bool) {
    for {
        select {
        case v := <-high:
            process(v)
        case v := <-low:
            process(v)
        case <-done:
            return
        }
    }
}

func main() {
    high := make(chan int, 100)
    low := make(chan int, 100)
    done := make(chan bool)
    
    go worker(high, low, done)
    
    for i := 0; i < 1000; i++ {
        high <- i  // high 채널만 계속 전송
    }
    
    low <- 999  // low는 처리되지 않을 수 있음 (Starvation)
}
```

**GoPie 탐지**:
- `high` 채널이 계속 선택되는 Interleaving 탐색
- `low` 채널이 무한정 대기하는 경로 발견
- **버그 보고**: Channel Starvation

### 성능 결과

**Benchmark 테스트**:
- **기존 도구 대비 2.3배 더 많은 버그 탐지**
- **탐색 시간**: 평균 15분 (기존 도구: 1시간+)

**오픈소스 프로젝트 적용**:
- **11개 새로운 버그 발견** (이전에 발견되지 않음)
- **9개 확인됨** (개발자가 버그로 인정)
- 프로젝트: Kubernetes, Etcd, Docker 등

**버그 유형**:
- Channel Blocking: 5개
- Goroutine Leak: 3개
- Race Condition: 2개
- WaitGroup Misuse: 1개

### GoPie vs 기존 도구

| 도구 | Channel 버그 | Goroutine Leak | 탐색 효율성 |
|------|--------------|----------------|-------------|
| Go Race Detector | ❌ | ❌ | N/A |
| Random Testing | △ (낮은 확률) | △ | 낮음 |
| Exhaustive Search | ✅ (이론적) | ✅ | 매우 낮음 (조합 폭발) |
| **GoPie** | **✅** | **✅** | **높음 (방향성)** |

### 핵심 기법: Directional Exploration

**무작위 vs 방향성**:

```
Random Testing:
실행 1: G1 → G2 → G3
실행 2: G2 → G1 → G3  (무작위)
실행 3: G1 → G3 → G2  (무작위)
→ 버그 발견 확률 낮음

GoPie:
실행 1: G1 → G2 → G3
분석: "G2가 먼저 실행되면?"
실행 2: G2 → G1 → G3  (목적 지향적)
→ Blocking 발견!
```

**Primitive Constraint 예시**:

```go
ch := make(chan int)

// Constraint: Send는 Receive가 준비되지 않으면 Block
// GoPie는 이를 인지하고 의도적으로 테스트
go func() {
    ch <- 1  // Send
}()

go func() {
    time.Sleep(1 * time.Second)  // Receive 지연
    <-ch
}()
```

**GoPie 탐색**:
1. 정상 실행: Receive 준비 → Send 성공
2. 방향성 탐색: Send 먼저 → Receive 없음 → **Blocking 탐지**

### 한계

**1. False Positive**
```go
// 의도적 Blocking (버그 아님)
func server(requests chan Request) {
    for req := range requests {  // 채널이 닫힐 때까지 대기 (정상)
        handle(req)
    }
}
```
→ GoPie가 Blocking으로 오탐할 수 있음

**2. 복잡한 Control Flow**
```go
// 조건부 Channel 사용
if config.EnableCache {
    cache <- data
} else {
    disk <- data
}
```
→ 모든 경로 탐색 어려움

**3. External Dependencies**
```go
// 네트워크 I/O, 파일 시스템
conn, _ := net.Dial("tcp", "example.com:80")
```
→ 외부 의존성은 탐색 불가

---

## 내가 얻은 인사이트

**Go 동시성 버그는 "타이밍"이 아니라 "구조" 문제다.** Race Detector가 잡는 Data Race는 타이밍 버그지만, Channel Blocking/Goroutine Leak은 프로그램 구조 자체의 문제다. `close(ch)` 누락, `done` 신호 없음 같은 것들. GoPie는 이런 **구조적 결함을 Interleaving 탐색으로 드러낸다**.

**"방향성 있는 랜덤"이 효율적이다.** 완전 무작위(Random Testing)는 비효율적이고, 완전 탐색(Exhaustive)은 불가능하다. GoPie의 **실행 이력 기반 방향성 탐색**은 "이미 본 패턴을 피하고, 의심스러운 경로를 우선 탐색"하는 전략. 이게 2.3배 더 많은 버그를 찾는 비결.

**Production 코드에도 동시성 버그가 많다.** Kubernetes, Etcd, Docker 같은 성숙한 프로젝트에서도 11개 신규 버그 발견. 동시성 코드는 **테스트하기 어렵고, 리뷰하기 어렵고, 재현하기 어렵다**. 자동화 도구 없이는 버그가 계속 숨어있을 수밖에 없다.
