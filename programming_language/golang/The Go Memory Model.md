# The Go Memory Model

## 출처
- **링크**: https://go.dev/ref/mem

---

## AI 요약

Go에서 **한 고루틴의 메모리 쓰기가 다른 고루틴에서 언제 보이는지**를 정의하는 공식 문서. 동시성 프로그래밍의 정확성을 보장하기 위한 규칙.

> "If you must read the rest of this document to understand the behavior of your program, you are being too clever. **Don't be clever.**"

### 핵심 개념: Happens-Before

**Happens-Before**: 메모리 연산 간의 부분 순서(partial order)
- A happens-before B → A의 쓰기가 B의 읽기에 **반드시 보임**
- Happens-before 관계 없음 → **아무것도 보장 안 됨**

### Data Race 정의

```go
// Data Race: 동기화 없이 같은 메모리에 동시 접근
// (최소 하나가 쓰기일 때)
var x int
go func() { x = 1 }()  // 쓰기
go func() { _ = x }()   // 읽기 - DATA RACE!
```

**DRF-SC 보장**: Data Race가 없으면 Sequential Consistency 보장

### Happens-Before 규칙 정리

| 상황 | Happens-Before 관계 |
|------|---------------------|
| **단일 고루틴** | 코드 순서대로 |
| **패키지 초기화** | `import q` → q.init() < p.init() |
| **main 시작** | 모든 init() < main.main() |
| **고루틴 생성** | `go f()` 문장 < f() 시작 |
| **고루틴 종료** | ❌ 보장 없음! |

### Channel 동기화

```go
ch := make(chan int)
var data string

go func() {
    data = "hello"
    ch <- 1          // send
}()

<-ch                 // receive
fmt.Println(data)    // 반드시 "hello" 출력
```

| Channel 규칙 | 설명 |
|-------------|------|
| **send < receive 완료** | 모든 채널에 적용 |
| **unbuffered** | receive 완료 < send 완료 |
| **buffered (용량 C)** | k번째 receive < (k+C)번째 send 완료 |
| **close** | close < close 이후 receive (zero value) |

### sync 패키지

| 타입 | Happens-Before |
|------|----------------|
| **Mutex** | n번째 Unlock() < m번째 Lock() (n < m) |
| **RWMutex** | 동일 |
| **Once** | once.Do(f) 실행 < 모든 once.Do() 리턴 |
| **WaitGroup** | Done() < Wait() 리턴 |
| **Cond** | Signal/Broadcast < 깨어난 Wait() |

### sync/atomic

Go 1.19부터 공식 명시:
- 모든 atomic 연산은 **sequentially consistent** 순서로 실행
- atomic 연산 A가 B에 관찰되면 → A happens-before B

```go
var flag atomic.Bool
var data string

go func() {
    data = "hello"
    flag.Store(true)  // memory barrier
}()

for !flag.Load() {}
fmt.Println(data)     // 반드시 "hello"
```

### 흔한 실수들

**1. Double-Checked Locking (틀림)**
```go
var done bool
var data string

func setup() {
    data = "hello"
    done = true
}

func doprint() {
    if !done {          // done=true 봐도
        once.Do(setup)  // data="hello" 못 볼 수 있음!
    }
    print(data)
}
```

**2. Busy Waiting (틀림)**
```go
var done bool
var data string

go func() {
    data = "hello"
    done = true
}()

for !done {}      // 영원히 안 끝날 수 있음
print(data)       // 빈 문자열일 수 있음
```

**3. 고루틴 종료 기다리기 (틀림)**
```go
var a string

func hello() {
    go func() { a = "hello" }()
    print(a)  // 빈 문자열일 수 있음 (고루틴 종료 보장 없음)
}
```

### 올바른 패턴

```go
// 1. Channel 사용
ch := make(chan struct{})
go func() {
    data = "hello"
    close(ch)
}()
<-ch

// 2. WaitGroup 사용
var wg sync.WaitGroup
wg.Add(1)
go func() {
    defer wg.Done()
    data = "hello"
}()
wg.Wait()

// 3. Mutex 사용
var mu sync.Mutex
mu.Lock()
data = "hello"
mu.Unlock()
```

### 요약

| 하지 말 것 | 해야 할 것 |
|-----------|-----------|
| 동기화 없이 공유 변수 접근 | Channel, Mutex, Atomic 사용 |
| Busy waiting | Channel이나 sync.Cond |
| 고루틴 종료 가정 | WaitGroup이나 Channel로 명시적 동기화 |
| 영리한 최적화 | **Don't be clever** |

---

## 내가 얻은 인사이트
