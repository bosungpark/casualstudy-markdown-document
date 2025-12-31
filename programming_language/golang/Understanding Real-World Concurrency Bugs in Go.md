# Understanding Real-World Concurrency Bugs in Go

## 출처
- **링크**: https://songlh.github.io/paper/go-study.pdf
- **학회**: ASPLOS 2019 (24th International Conference on Architectural Support for Programming Languages and Operating Systems)
- **저자**: Tengfei Tu (BUPT/Penn State), Xiaoyu Liu (Purdue), Linhai Song (Penn State), Yiying Zhang (Purdue)
- **GitHub**: https://github.com/system-pclub/go-concurrency-bugs

---

## AI 요약

### 연구 배경 및 목적
Go는 2009년 Google에서 개발한 언어로, "메시지 패싱이 공유 메모리보다 안전하다"는 철학을 바탕으로 설계되었다. 그러나 실제로 Go의 동시성 메커니즘이 버그를 줄이는지에 대한 체계적인 연구는 없었다. 이 논문은 **Go 동시성 버그에 대한 최초의 체계적 실증 연구**이다.

### 연구 대상
6개의 대형 오픈소스 Go 프로젝트에서 **171개의 동시성 버그**를 수집하여 분석:
- **Docker** (48.9K stars): 컨테이너 시스템
- **Kubernetes** (36.5K stars): 컨테이너 오케스트레이션
- **etcd**: 분산 키-값 저장소
- **gRPC-Go**: RPC 라이브러리
- **CockroachDB**: 분산 데이터베이스
- **BoltDB**: 임베디드 키-값 데이터베이스

### 버그 분류 체계 (2차원)
**1차원 - 동작(Behavior)**:
- **Blocking Bug (85개)**: 하나 이상의 goroutine이 영원히 멈춤 (전통적 deadlock보다 넓은 개념)
- **Non-blocking Bug (86개)**: goroutine은 완료되지만 의도와 다른 동작

**2차원 - 원인(Cause)**:
- **Shared Memory (105개)**: 공유 메모리 보호 오류
- **Message Passing (66개)**: 메시지 전달 오류 (채널 등)

### 핵심 발견 1: Goroutine 사용 패턴
- Go 프로그램은 C/C++보다 **훨씬 많은 스레드(goroutine)**를 생성함
- gRPC-Go vs gRPC-C 비교: Go는 KLOC당 0.83개 생성 지점, C는 0.03개
- goroutine은 익명 함수로 생성되는 경우가 많음 (6개 중 5개 프로젝트에서 과반)

### 핵심 발견 2: 동시성 프리미티브 사용
| 프리미티브 | 평균 사용 비율 |
|-----------|--------------|
| Mutex (공유 메모리) | 45-70% |
| Channel (메시지 패싱) | 18-43% |
| atomic, Once, WaitGroup 등 | 나머지 |

→ 공유 메모리 동기화가 여전히 **더 많이 사용**되지만, 채널도 상당 비중 차지

### 핵심 발견 3: Blocking Bug 원인 (가장 충격적)

> **"메시지 패싱이 공유 메모리보다 안전하다"는 믿음과 달리, blocking 버그의 58%가 메시지 패싱에서 발생!**

| 원인 | 버그 수 |
|-----|--------|
| Mutex 오용 | 28개 |
| Channel 오용 | 29개 |
| Channel + 다른 프리미티브 혼용 | 16개 |
| Go 라이브러리 (context, Pipe 등) | 4개 |
| RWMutex | 5개 |
| Wait (Cond, WaitGroup) | 3개 |

#### Blocking Bug 대표 패턴들

**패턴 1: Unbuffered Channel + Timeout**
```go
func finishReq(timeout time.Duration) r ob {
    ch := make(chan ob)      // ❌ unbuffered
    // ch := make(chan ob, 1) // ✅ buffered로 수정
    go func() {
        result := fn()
        ch <- result  // timeout 발생 시 여기서 영원히 block
    }()
    select {
    case result = <- ch:
        return result
    case <- time.After(timeout):
        return nil  // parent가 여기로 가면 child는 영원히 대기
    }
}
```
→ **수정**: unbuffered channel을 buffered channel로 변경

**패턴 2: WaitGroup 잘못된 위치**
```go
var group sync.WaitGroup
group.Add(len(pm.plugins))
for _, p := range pm.plugins {
    go func(p *plugin) {
        defer group.Done()
    }
    group.Wait()  // ❌ 루프 안에서 Wait 호출 - goroutine 생성 차단
}
// group.Wait()  // ✅ 루프 밖으로 이동
```

**패턴 3: RWMutex의 Go 특유 동작**
Go의 RWMutex는 **Write Lock이 Read Lock보다 우선권**을 가짐 (C의 pthread_rwlock_t와 다름!)
```
th-A: RLock() → 성공
th-B: Lock() → th-A 때문에 대기
th-A: RLock() → th-B가 대기 중이라 block (Go 특유!)
```
→ 둘 다 영원히 대기 (C에서는 발생하지 않음)

**패턴 4: Channel + Lock 혼용**
```go
func goroutine1() {
    m.Lock()
    ch <- request  // block - goroutine2가 lock 대기 중
    m.Unlock()
}

func goroutine2() {
    for {
        m.Lock()    // block - goroutine1이 lock 보유 중
        m.Unlock()
        request <- ch
    }
}
```
→ **수정**: select + default 사용하여 non-blocking으로 변경

### 핵심 발견 4: Non-blocking Bug 원인

| 원인 | 버그 수 | 비율 |
|-----|--------|-----|
| 전통적 공유 메모리 버그 | 46개 | 53% |
| 익명 함수 관련 | 11개 | 13% |
| WaitGroup 오용 | 6개 | 7% |
| Go 라이브러리 | 6개 | 7% |
| Channel 오용 | 16개 | 19% |
| 메시징 라이브러리 | 1개 | 1% |

→ **80%가 공유 메모리 관련**, 20%만 메시지 패싱 관련

#### Non-blocking Bug 대표 패턴들

**패턴 1: 익명 함수의 변수 캡처 (Data Race)**
```go
for i := 17; i <= 21; i++ {
    go func() {  // ❌ i를 참조로 캡처
        apiVersion := fmt.Sprintf("v1.%d", i)  // i 값이 불확정
    }()
}

// ✅ 수정: i를 인자로 전달하여 복사본 생성
for i := 17; i <= 21; i++ {
    go func(i int) {
        apiVersion := fmt.Sprintf("v1.%d", i)
    }(i)
}
```

**패턴 2: WaitGroup.Add()의 위치**
```go
func (p *peer) send() {
    p.mu.Lock()
    defer p.mu.Unlock()
    switch p.status {
    case idle:
        // p.wg.Add(1)  // ✅ 여기로 이동
        go func() {
            p.wg.Add(1)  // ❌ Wait()보다 늦게 실행될 수 있음
            p.wg.Done()
        }()
    }
}

func (p *peer) stop() {
    p.mu.Lock()
    p.status = stopped
    p.mu.Unlock()
    p.wg.Wait()  // Add() 전에 실행될 수 있음!
}
```

**패턴 3: Channel 중복 close**
```go
select {
case <- c.closed:
default:
    close(c.closed)  // ❌ 여러 goroutine이 동시에 실행 가능
}

// ✅ 수정: Once 사용
Once.Do(func() {
    close(c.closed)
})
```

**패턴 4: select의 비결정적 선택**
```go
for {
    f()  // 무거운 함수
    select {
    case <- stopCh:
        return
    case <- ticker:  // stopCh와 동시에 ready되면 둘 중 랜덤 선택!
    }
}

// ✅ 수정: 루프 시작에 stopCh 먼저 체크
for {
    select {
    case <- stopCh:
        return
    default:
    }
    f()
    select {
    case <- stopCh:
        return
    case <- ticker:
    }
}
```

### 핵심 발견 5: 버그 탐지 도구 평가

**Go 내장 Deadlock Detector**:
- 재현된 21개 blocking 버그 중 **단 2개만 탐지** (9.5%)
- 이유: 일부 goroutine이라도 실행 중이면 deadlock으로 판단 안 함

**Go 내장 Race Detector (-race 플래그)**:
- 재현된 20개 non-blocking 버그 중 **10개 탐지** (50%)
- 전통적 버그 7/13, 익명함수 버그 3/4 탐지
- 한계: 모든 버그가 data race는 아님, interleaving 의존성

### 버그 수정 패턴

**Blocking Bug 수정**:
| 전략 | 건수 |
|-----|-----|
| 동기화 추가 | 31 |
| 동기화 제거 | 21 |
| 동기화 이동 | 14 |
| 동기화 변경 | 9 |

- 평균 패치 크기: **6.8줄**
- 90%가 동기화 프리미티브 조정으로 해결

**Non-blocking Bug 수정**:
| 전략 | 건수 |
|-----|-----|
| 타이밍 제한 (동기화 추가/이동) | 59 |
| 명령어 우회/제거 | 17 |
| 변수 private 복사본 생성 | 14 |

| 수정에 사용된 프리미티브 | 건수 |
|----------------------|-----|
| Mutex | 32 |
| Channel | 19 |
| Atomic | 10 |
| WaitGroup | 7 |
| 프리미티브 없이 | 19 |

→ 흥미롭게도 **Channel이 공유 메모리 버그를 수정하는 데도 사용됨** (개발자들이 메시지 패싱을 더 안전하다고 인식)

### 논문의 9가지 관찰 (Observations)

1. Goroutine은 C 스레드보다 짧지만 더 자주 생성됨
2. 공유 메모리 동기화가 여전히 많이 사용되지만, 메시지 패싱도 상당량 사용
3. **일반적 믿음과 달리, blocking 버그의 대부분이 메시지 패싱에서 발생**
4. 공유 메모리 blocking 버그는 대부분 전통적 원인이지만, Go 특유의 구현 차이도 존재
5. 모든 메시지 패싱 blocking 버그가 Go의 새로운 메시지 패싱 메커니즘과 관련
6. Blocking 버그 대부분이 단순한 해결책으로 수정 가능하며, 원인과 수정 방법 간 상관관계 높음
7. 공유 메모리 non-blocking 버그의 2/3가 전통적 원인, 1/3이 Go 특유
8. Non-blocking 버그에서 메시지 패싱은 공유 메모리보다 훨씬 적음
9. Non-blocking 버그 수정에 전통적 방법이 주로 사용되지만, Channel도 일부 사용

### 논문의 8가지 시사점 (Implications)

1. Goroutine과 새로운 동시성 프리미티브의 많은 사용으로 **더 많은 동시성 버그 발생 가능성**
2. 메시지 패싱이 blocking 버그를 더 많이 유발할 수 있음 → 연구 필요
3. Go blocking 버그의 원인-수정 간 높은 상관관계 → **자동 수정 도구 개발 유망**
4. 단순한 런타임 deadlock 탐지기는 효과적이지 않음 → 정적+동적 분석 조합 필요
5. Go의 새로운 프로그래밍 모델과 라이브러리가 **새로운 동시성 버그의 원인**이 될 수 있음
6. 올바르게 사용하면 메시지 패싱이 non-blocking 버그에 덜 취약하나, 복잡한 설계 시 찾기 어려움
7. Go 개발자들이 메시지 패싱을 더 안전하다고 인식하여 버그 수정에도 사용
8. 기존 data race 탐지기는 모든 Go non-blocking 버그를 탐지 못함 → Go 특화 도구 필요

---

## 내가 얻은 인사이트

### 1. "메시지 패싱이 더 안전하다"는 Go의 철학에 대한 재고
- Go의 공식 슬로건 "Share Memory By Communicating"이 항상 옳지 않다
- Channel을 사용한다고 버그가 줄어드는 것이 아니라, **올바르게 사용해야만** 줄어든다
- 특히 Channel + Lock 혼용, Channel + select + timeout 조합에서 blocking 버그 다발

### 2. Goroutine 생성의 용이함이 양날의 검
- `go func()` 한 줄로 goroutine 생성이 쉬워서 남발하게 됨
- 익명 함수의 변수 캡처(closure)가 **암묵적으로 참조**를 캡처하므로 data race 유발
- Java의 람다는 **값으로만 캡처**, C++은 **명시적으로 선택** → Go만의 함정

### 3. Go 특유의 구현 차이 주의
- `RWMutex`: Write Lock 우선권 때문에 C와 다른 blocking 패턴 발생
- `WaitGroup`: `Add()`가 `Wait()` 전에 호출되어야 함 → goroutine 안에서 Add 호출 금지
- `select`: 여러 case가 ready면 **랜덤 선택** → 의도치 않은 동작 가능
