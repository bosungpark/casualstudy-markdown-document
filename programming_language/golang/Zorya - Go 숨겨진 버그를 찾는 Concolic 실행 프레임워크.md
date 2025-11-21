# Zorya - Go 숨겨진 버그를 찾는 Concolic 실행 프레임워크

## 링크
https://arxiv.org/abs/2505.20183

## AI 요약

### 핵심 문제
Go는 인프라/블록체인 프로젝트에서 널리 사용되지만, 66% 이상의 Go 모듈에 취약점이 존재합니다. 기존 도구들(static analysis, fuzzing)로는 Go의 복잡한 런타임과 동시성 모델(goroutine, channel)의 취약점을 제대로 탐지하기 어렵습니다.

### Zorya의 해결 방법

**Concolic Execution = Concrete + Symbolic Execution**

1. **Concrete Execution (구체적 실행)**
   - 실제 입력값으로 프로그램 실행
   - 빠르고 실용적이지만 특정 경로만 탐색

2. **Symbolic Execution (심볼릭 실행)**
   - 변수를 심볼로 취급해 모든 경로 탐색
   - 완전하지만 path explosion 문제 발생

3. **Concolic = 두 방식의 결합**
   - 구체적 실행으로 경로를 따라가면서
   - 동시에 심볼릭 표현을 구축
   - Path explosion을 완화하면서 깊은 탐색 가능

### 핵심 아키텍처

#### 1. P-Code IR 사용
```
Go Binary → Ghidra → P-Code → Zorya 분석
```

**왜 P-Code인가?**
- LLVM IR은 gollvm이 제대로 유지보수되지 않아 Go 지원 부족
- VEX, BIL, REIL보다 Go 바이너리 분석에 적합
- Ghidra의 Go lifter가 goroutine, channel 메타데이터 보존
- Low-level 세부 사항을 유지해 정밀한 심볼릭 추론 가능

#### 2. 3가지 버그 탐지 전략

**전략 S1: Concrete Execution + Flag Mechanism**
```rust
// panic 함수 호출 직전에 플래그 발생
if program_counter == panic_function_xref {
    raise_flag("approaching panic!");
    halt_analysis();
}
```
- 심볼 리스트에서 panic 함수 식별
- PC가 panic 함수의 cross-reference에 도달하면 감지
- 모든 분석에 기본으로 활성화

**전략 S2: Concolic + Z3 Invariant**
```z3
// Z3 불변 조건
invariant = "PC는 절대 panic 함수로의 cross-reference를 가리키면 안됨"

// 모든 경로에서 검증
for each path:
    if violates(invariant):
        report_vulnerability()
```
- 전체 바이너리를 `start`/`main` 주소부터 분석
- nil pointer dereference 같은 DoS 취약점 예방

**전략 S3: Targeted Function Analysis**
```rust
// 특정 함수에 집중
fn analyze_function(addr) {
    args = symbolic_variables();  // 인자를 심볼릭 변수로
    concrete_values = randomize(); // 구체적 값은 랜덤
    
    execute_from(addr, args, concrete_values);
    verify_custom_invariants();
}
```
- 함수 주소에서 실행 시작
- 인자를 심볼릭 변수로 초기화
- 커스텀 불변 조건 검증

#### 3. 실행 과정

```
1. GDB로 CPU 레지스터/메모리 덤프 생성 (특정 주소)
   ↓
2. 덤프 로드 → 프로그램 상태 초기화
   ↓
3. 바이너리 → Raw P-Code 변환
   ↓
4. Pcode-parser로 P-Code 파싱
   ↓
5. Rust 엔진 (Z3 SMT solver)으로 실행
   - State Manager: 실행 상태 관리
   - CPU State: 레지스터 추적
   - Memory Model: 메모리 모델링
   - Virtual FS: 가상 파일시스템
   ↓
6. P-Code 명령어 에뮬레이션
   - handle_int_add, handle_load 등
   - Concrete + Symbolic 데이터 타입 지원
   ↓
7. 취약점 탐지 및 보고
```

### 실제 예제: Nil Map Panic

**Go 코드:**
```go
package main

func nilMapPanic() {
    var m map[string]int  // nil map
    m["key"] = 42         // panic 발생!
}

func main() {
    nilMapPanic()
}
```

**Zorya 분석 과정:**
1. TinyGo로 컴파일
2. P-Code로 변환
3. `main.main` 주소부터 실행
4. 각 P-Code 명령마다 concolic 상태 업데이트
5. PC가 `0x2034c5` (panic 주소)에 도달
6. 전략 S1이 플래그 발생
7. "add entry to nil map" 보고 후 분석 중단

### 구현 세부사항

#### Pcode-parser (Rust 구현)
- 기존 `sleigh-rs` 불완전 → 처음부터 새로 구현
- Ghidra x86-64 명세에 정확히 맞춤
- Symbol mapping (.text, .rodata 섹션)
- Low-level P-Code 파서

#### 현재 지원 범위
✅ **지원:**
- Single-threaded Go 프로그램 (TinyGo 컴파일)
- x86-64 명령어/syscall
- Concrete + Symbolic 데이터 타입
- Jump table 처리
- 공유 라이브러리 (libc.so, ld-linux-x86-64.so)
- C 프로그램 분석 (null dereference, uninitialized variable 등)

❌ **미지원 (향후 계획):**
- Multi-threading
- Goroutine
- 표준 Go 컴파일러 (현재는 TinyGo만)

### 평가 결과

#### RQ1: P-Code를 Ghidra 외부에서 사용 가능한가?

| 바이너리 타입 | True Positive | False Positive | 총합 |
|--------------|--------------|----------------|------|
| Go           | 10           | 0              | 10   |
| C            | 9            | 1              | 10   |

✅ Go 바이너리는 100% 정확도
✅ C 바이너리도 대부분 정확 (복잡한 구조에서만 오류)
✅ 파일 생성 시간 수 초 (바이너리 크기 의존)

#### RQ2: 기존 도구와 비교

**TinyGo 런타임 패닉 탐지:**

| 취약점 유형 | DuckEEGO | Radius2 | MIASM | Zorya |
|-----------|----------|---------|-------|-------|
| Nil Pointer Dereference | ❌ | ❌ | ❌ | ✅ |
| Index Out Of Range | ❌ | ❌ | ❌ | ✅ |
| Nil Map Assignment | ❌ | ❌ | ❌ | ✅ |
| Too Large Channel | ❌ | ❌ | ❌ | ✅ |
| Negative Shift | ❌ | ❌ | ❌ | ✅ |

**경쟁 도구의 한계:**
- **DuckEEGO**: Go 1.10용으로 개발, 최신 Go 모듈 시스템 미지원
- **Radius2**: 분석이 임의 지점에서 종료, 결과 정보 없음
- **MIASM**: Go의 panic 처리 메커니즘 미지원

**Zorya의 강점:**
- False Positive 0
- 1분 이내 분석 완료
- 간단한 인터페이스: `zorya <path/to/bin>`
- 대화형 모드로 시작 주소/불변 조건 커스터마이징

#### RQ3: C 바이너리 분석 가능한가?

✅ **성공적으로 탐지:**

1. **Null Dereference**
   ```rust
   // STORE/LOAD 시 포인터가 null인지 체크
   if pointer == null {
       report_vulnerability();
   }
   ```

2. **Misaligned Memory**
   ```rust
   // LOAD 주소가 로드 크기로 나누어떨어지는지 체크
   if (load_address % load_size) != 0 {
       report_misaligned_memory();
   }
   ```

3. **Uninitialized Variable**
   ```rust
   // 로드된 주소가 이전에 저장된 적 있는지 체크
   if !previously_stored(address) {
       report_uninitialized();
   }
   ```

### 기술적 차별점

#### 1. Go 런타임 이해
- Goroutine 스케줄러 메타데이터 보존
- Channel 통신 패턴 인식
- 가비지 컬렉터 고려
- Unsafe 메모리 연산 탐지

#### 2. P-Code의 장점
```
LLVM IR (high-level) -----> P-Code (low-level) -----> x86 (too low)
                            ↑ Zorya가 사용하는 위치
```
- High-level: gollvm 유지보수 부족
- Low-level: 추상화 부족, 유지보수 어려움
- P-Code: 세밀한 의미론 보존 + 분석 가능한 구조

#### 3. Rust + Z3 엔진
```rust
struct ZoryaEngine {
    state_manager: StateManager,
    cpu_state: CPUState,
    memory_model: MemoryModel,
    vfs: VirtualFileSystem,
    z3_solver: Z3Solver,
}

impl ZoryaEngine {
    fn handle_int_add(&mut self, op1, op2, dest) {
        // Concrete execution
        let concrete_result = op1.concrete + op2.concrete;
        
        // Symbolic execution
        let symbolic_result = z3_solver.add(op1.symbolic, op2.symbolic);
        
        self.write(dest, Value {
            concrete: concrete_result,
            symbolic: symbolic_result,
        });
    }
}
```

### 고급 기능

#### Jump Table 처리
```go
switch num {
case 0: // ...
case 1: // ...
case 2: // ...
// 컴파일러가 jump table로 최적화
}
```
- Binary search 대신 직접 점프
- Zorya가 정확히 처리 (jump_table.json)

#### Cross-Reference 추적
```
xref_addresses.txt:
0x2034c5 → runtime.nilPanic
0x2034d0 → runtime.indexPanic
0x2034e5 → runtime.slicePanic
```
- Panic 함수로의 모든 참조 자동 문서화
- 타겟팅된 취약점 평가

#### 상세 실행 로그
```
execution_log.txt:
[0x401000] LOAD 8 bytes from rsp+0x10 → rax
[0x401004] INT_ADD rax, 0x8 → rax
[0x401008] STORE rax → [rbx+0x20]
...

execution_trace.txt:
main.nilMapPanic(args=[])
  └─ runtime.mapassign(m=0x0, key="key")
      └─ runtime.nilPanic() ← DETECTED!
```

### 향후 개선 방향

#### 1. Multithreading & Goroutine 지원
```go
go func() {
    // Zorya가 분석해야 할 동시성 패턴
}()
```
- Race condition 탐지
- Channel 데드락 분석
- Goroutine 스케줄링 모델링

#### 2. Symbolic Execution 개선
- 현재: 제한적인 symbolic exploration depth
- 목표: 더 깊은 경로 탐색으로 복잡한 패닉 발견

#### 3. 취약점 패턴 자동 분류
```
Concolic logs → ML classifier → Vulnerability patterns
```

#### 4. 표준 Go 컴파일러 지원
- 현재는 TinyGo만 지원
- 표준 Go의 더 복잡한 런타임 처리 필요

### 주요 도구 비교

| 도구 | 언어 | 방법 | IR | Go 지원 | SMT Solver | UI |
|-----|------|------|----|---------|-----------|----|
| MAAT | C++ | SE with CE | LLVM IR | ❌ gollvm | Z3 | CLI |
| Angr | Python | SE with CE | VEX, P-Code | ❌ 부분 지원 | Z3, Boolector, CVC4 | CLI, GUI |
| DuckEEGO | Go | SE with CE | Go AST | ⚠️ 제한적 | Z3 | CLI |
| Radius2 | Rust | SE + Taint | ESIL | ⚠️ 제한적 | Z3, Boolector | CLI |
| **Zorya** | **Rust** | **CE + SE** | **P-Code** | **✅ 중간** | **Z3** | **CLI, Ghidra GUI** |

## 내가 얻은 인사이트

### 1. Concolic Execution의 실용성
Concrete + Symbolic의 조합은 단순히 두 방법을 합친 것이 아니라, 각각의 약점을 상호 보완하는 시너지 효과를 낸다. 

- 수십만 개 조건문을 가지는 70MB 실전 바이너리를 1분 내 분석했다는 점에서 인상적임
- Concrete execution 기반이라 실제 실행 경로만 분석하여 False positive가 없는데, 보안 도구의 신뢰도는 false alarm에 크게 영향받는다는 점에서 현명한 선택이라고 느껴짐
- 66% 이상의 Go 모듈에 취약점이 있다는 통계는 좀 충격적었음
- 크게 관심이 있는 분야는 아니지만 재밌었음
