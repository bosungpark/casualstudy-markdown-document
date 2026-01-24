# Using Lightweight Formal Methods to Validate a Key-Value Storage Node in Amazon S3

## 출처
- **링크**: https://dl.acm.org/doi/10.1145/3477132.3483540
- **PDF**: https://assets.amazon.science/07/6c/81bfc2c243249a8b8b65cc2135e4/using-lightweight-formal-methods-to-validate-a-key-value-storage-node-in-amazon-s3.pdf
- **저자**: James Bornholt, Rajeev Joshi, Vytautas Astrauskas, Brendan Cully, Bernhard Kragl, Seth Markle, Kyle Sauri, Drew Schleit, Grant Slatton, Serdar Tasiran, Jacob Van Geffen, Andrew Warfield
- **게재**: SOSP 2021 (Best Paper Award)

---

## AI 요약

### 1. 논문의 핵심 목적

이 논문은 Amazon S3 클라우드 객체 스토리지 서비스의 새로운 키-값 스토리지 노드 구현인 ShardStore의 정확성을 검증하기 위해 lightweight formal methods를 적용한 경험을 보고한다. "Lightweight formal methods"는 전체 엔지니어링 팀이 지속적으로 기능 개발 중인 프로덕션 스토리지 노드의 정확성을 검증하는 실용적 접근법을 의미한다.

완전한 formal verification을 목표로 하지 않고, 자동화, 사용성, 소프트웨어와 명세가 시간이 지나면서 진화해도 지속적으로 정확성을 보장하는 능력을 강조한다.

### 2. ShardStore 아키텍처

#### 2.1 S3 내에서의 위치

ShardStore 키-값 저장소는 S3에서 스토리지 노드로 사용된다. 각 스토리지 노드는 고객 객체의 샤드를 저장하며, 내구성을 위해 여러 노드에 걸쳐 복제되므로 스토리지 노드는 저장된 데이터를 내부적으로 복제할 필요가 없다.

#### 2.2 온디스크 구조

```
┌─────────────────────────────────────────────────────┐
│                    LSM Tree (Index)                 │
│  ┌───────────────────────────────────────────────┐  │
│  │ shardID 0x13 → [chunk ptr, chunk ptr, ...]    │  │
│  │ shardID 0x28 → [chunk ptr, ...]               │  │
│  │ shardID 0x75 → [chunk ptr, chunk ptr, ...]    │  │
│  └───────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│  extent 17    extent 18    extent 19    extent 20   │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐    │
│  │LSM data│  │ chunk  │  │ chunk  │  │ chunk  │    │
│  │        │  │  hole  │  │        │  │        │    │
│  │        │  │ chunk  │  │        │  │        │    │
│  └────────┘  └────────┘  └────────┘  └────────┘    │
├─────────────────────────────────────────────────────┤
│           Superblock (Extent 0)                     │
│        soft write pointers: {17→0x60, ...}          │
└─────────────────────────────────────────────────────┘
```

ShardStore의 키-값 저장소는 log-structured merge tree (LSM tree)로 구성되지만 샤드 데이터는 write amplification을 줄이기 위해 트리 외부에 저장된다(WiscKey와 유사). LSM tree는 각 샤드 식별자를 청크(포인터) 목록에 매핑하며, 각 청크는 extent 내에 저장된다. Extent는 디스크의 연속적인 물리적 저장 영역으로, 일반적인 디스크에는 수만 개의 extent가 있다.

ShardStore는 각 extent 내의 쓰기가 순차적이어야 하며, 다음 유효한 쓰기 위치를 정의하는 write pointer로 추적되므로, extent의 데이터는 즉시 덮어쓸 수 없다.

#### 2.3 Chunk Reclamation (가비지 컬렉션)

extent는 append-only이므로 샤드를 삭제해도 해당 샤드의 청크가 차지하는 빈 공간을 즉시 회수할 수 없다. 빈 공간을 회수하고 재사용하기 위해 chunk store는 가비지 컬렉션을 수행하는 reclamation 백그라운드 작업을 가진다. Reclamation은 extent를 선택하고 스캔하여 저장된 모든 청크를 찾는다. 각 청크에 대해 인덱스(LSM tree)에서 역방향 조회를 수행한다. 인덱스에서 여전히 참조되는 청크는 새 extent로 대피시키고 인덱스의 포인터를 업데이트하며, 참조되지 않는 청크는 단순히 드롭된다.

### 3. Soft Updates 기반 Crash Consistency

ShardStore는 soft updates에서 영감을 받은 crash consistency 접근법을 사용한다. Soft updates 구현은 디스크로 전송되는 쓰기 순서를 조율하여 디스크의 모든 crash 상태가 일관되도록 보장한다.

**Dependency 타입:**
```rust
fn append(&self, ..., dep: Dependency) -> Dependency
```

append API의 계약은 입력 dependency가 영속화될 때까지 append가 디스크에 발행되지 않는다는 것이다. append에서 반환된 dependency는 후속 append 연산에 다시 전달되거나, 먼저 다른 dependency와 결합되어(예: dep1.and(dep2)) 더 복잡한 dependency 그래프를 구성할 수 있다.

**PUT 연산의 Dependency Graph 예시:**
```
PUT #1                    PUT #2                    PUT #3
   │                         │                         │
   ▼                         ▼                         ▼
Shard data chunk        Shard data chunk        Shard data chunk
  (extent 27)             (extent 27)             (extent 4)
   │                         │                         │
   ├─────────┬───────────────┘                         │
   ▼         ▼                                         ▼
Soft write ptr         Index entry               Index entry
 (extent 0)            (extent 12)              (extent 12)
   │                         │                         │
   └─────────────────────────┴─────────────────────────┘
                             │
                             ▼
                     LSM-tree metadata (extent 9)
                             │
                             ▼
                     Soft write ptr (extent 0)
```

### 4. 검증 접근법: 정확성 속성 분해

| 실행 유형 | 검증 방법 | 도구 |
|-----------|----------|------|
| **Sequential crash-free** | Reference model과 직접 동등성 검사 | Property-based testing (proptest) |
| **Sequential crashing** | 확장된 reference model로 약화된 동등성 | Property-based testing |
| **Concurrent crash-free** | Linearizability 검사 | Loom (sound), Shuttle (scalable) |

### 5. Reference Models

각 ShardStore 컴포넌트에 대해 reference model을 개발했다—컴포넌트와 동일한 인터페이스를 제공하지만 더 간단한 구현을 사용하는 Rust의 실행 가능한 명세다. 예를 들어, 샤드 식별자를 청크 로케이터에 매핑하는 index 컴포넌트에 대해 persistent LSM-tree 대신 단순한 해시 테이블을 사용하는 reference model을 정의한다.

**핵심 특징:**
- 구현 언어(Rust)와 동일한 언어로 작성 → 엔지니어가 유지보수 가능
- Unit test의 mock으로 재사용 가능
- 크기: 구현 코드의 **약 1%** (450줄)

### 6. Property-Based Testing

```rust
enum IndexOp<Key, Value> {
    Get(Key),
    Put(Key, Value),
    ...
    Reclaim,
    Reboot,
}

#[proptest]
fn proptest_index(ops: Vec<IndexOp<u32, u32>>) {
    let mut reference = ReferenceIndex::new();
    let mut implementation = PersistentLSMTIndex::new();
    for op in ops {
        match op {
            Put(key, value) => {
                compare_results!(
                    implementation.put(key, value),
                    reference.put(key, value),
                );
            }
            Get(key) => { ... }
            ...
        }
        check_invariants(&reference, &implementation);
    }
}
```

**Operation Alphabet 구성:**
- API 연산: Get, Put, Delete, ...
- 백그라운드 연산: Reclaim, Compact
- 장애 연산: FailDiskOnce, DirtyReboot

**Coverage 확보 전략:**
- Argument bias: 이전에 Put된 키를 Get에서 선호하도록
- 코너 케이스 bias: 디스크 페이지 크기 근처의 읽기/쓰기 크기
- Coverage metrics: 새 기능이 검증 범위에서 벗어나지 않도록 모니터링

### 7. Crash Consistency 검증

**두 가지 속성:**
1. **Persistence**: dependency가 크래시 전에 영속화되었다고 하면, 크래시 후에도 읽을 수 있어야 함
2. **Forward progress**: 비크래시 셧다운 후, 모든 연산의 dependency가 영속적임을 나타내야 함

```rust
// Persistence 검사
for (key, dependency) in dependency_map {
    assert!(
        !dependency.is_persistent()
        || reference.get(key) == implementation.get(key)
    );
}
```

### 8. Stateless Model Checking for Concurrency

**두 도구의 Trade-off:**

| 도구 | 알고리즘 | 특성 | 용도 |
|------|----------|------|------|
| **Loom** | CDSChecker | Sound (모든 인터리빙 탐색), 느림 | 작은 correctness-critical 코드 |
| **Shuttle** | Probabilistic Concurrency Testing | Scalable, 빠름 | 대규모 end-to-end 테스트 |

```rust
loom::model(|| {
    let chunk_store = MockChunkStore::new();
    let index = PersistentLSMTIndex::new(chunk_store);
    
    // 초기 상태 설정
    for (key, value) in &[...] {
        index.put(key, value);
    }
    
    // 동시 작업 생성
    let t1 = thread::spawn(|| chunk_store.reclaim());
    let t2 = thread::spawn(|| index.compact());
    let t3 = thread::spawn(|| {
        for (key, value) in &[...] {
            index.put(key, value);
            assert_eq!(index.get(key), value);  // read-after-write
        }
    });
    
    t1.join(); t2.join(); t3.join();
})
```

### 9. 발견된 버그 (16개 프로덕션 도달 방지)

**Functional Correctness (5개):**
| ID | 컴포넌트 | 설명 |
|----|----------|------|
| #1 | Chunk store | PAGE_SIZE 근처 청크 reclamation에서 off-by-one 에러 |
| #2 | Buffer cache | extent 리셋 후 캐시가 올바르게 drain되지 않음 |
| #3 | Index | extent 리셋 시 셧다운 중 메타데이터가 올바르게 flush되지 않음 |
| #4 | API | 디스크가 서비스에서 제거되었다가 나중에 반환되면 샤드 손실 |
| #5 | Chunk store | 일시적 읽기 IO 에러 후 reclamation이 청크를 잊어버림 |

**Crash Consistency (5개):**
| ID | 컴포넌트 | 설명 |
|----|----------|------|
| #6 | Superblock | 리부트 후 extent 소유권에 대한 Dependency가 잘못됨 |
| #7 | Superblock | extent 리셋 후 크래시에서 soft/hard write pointer 불일치 |
| #8 | Buffer cache | 쓰기가 soft write pointer 업데이트에 대한 dependency 미포함 |
| #9 | Chunk store | reclamation 중 크래시 후 reference model이 올바르게 업데이트되지 않음 |
| #10 | Chunk store | 크래시와 UUID 충돌 후 reclamation이 청크를 잊어버림 |

**Concurrency (6개):**
| ID | 컴포넌트 | 설명 |
|----|----------|------|
| #11 | Chunk store | write와 flush 간 race로 청크 로케이터가 무효화될 수 있음 |
| #12 | Superblock | Buffer pool 고갈로 superblock 업데이트 대기 스레드가 deadlock |
| #13 | API | 샤드 listing과 removal을 위한 control plane 연산 간 race |
| #14 | Index | reclamation과 LSM compaction 간 race로 최근 인덱스 항목 손실 |
| #15 | Chunk store | Reference model이 청크 로케이터를 재사용할 수 있는데, 다른 코드는 유일하다고 가정 |
| #16 | API | 샤드 생성과 제거를 위한 control plane bulk 연산 간 race |

### 10. 상세 버그 사례: Crash Consistency Bug (#10)

청크 데이터는 디스크에서 2바이트 매직 헤더("M")와 랜덤 UUID로 프레이밍되며, 길이 검증을 위해 양쪽 끝에 반복된다.

**시나리오:**
```
1. 청크가 page 0과 page 1에 걸쳐 저장:
   page 0: [M UUID length payload ...]
   page 1: [... UUID]

2. 크래시로 page 1 손실 (page 0은 flush됨)

3. 복구 후 새 청크가 page 1부터 기록:
   page 0: [M UUID length payload (corrupted)]
   page 1: [M UUID length payload UUID]

4. Reclamation이 extent 스캔:
   - 첫 번째 청크의 손실된 UUID 바이트가 매직 바이트와 일치하면
   - Reclamation이 첫 번째 청크를 성공적으로 디코드
   - 두 번째 청크를 건너뜀 (겹치는 청크 예상 안 함)

5. Extent 리셋 후 두 번째 청크 접근 불가 → 일관성 위반
```

이것은 매직 바이트와 충돌하는 특정 랜덤 UUID 선택, 두 번째 페이지로 간신히 넘어가는 정확한 크기의 청크, 두 번째 페이지만 손실하는 크래시가 관련된 미묘한 이슈였다. 그럼에도 우리의 conformance check가 이 테스트 케이스를 자동으로 발견하고 최소화했다.

### 11. 상세 버그 사례: Concurrency Bug (#14)

LSM tree 구현은 현재 디스크에 LSM tree 데이터를 저장하는 데 사용되는 청크 집합을 추적하는 인메모리 메타데이터 객체를 사용한다. 이 메타데이터는 두 개의 동시 백그라운드 작업에 의해 변경된다: (1) LSM tree compaction은 인덱스의 인메모리 섹션을 디스크로 flush하여 메타데이터에 추가할 새 청크를 생성하고 내용이 compaction된 청크를 제거한다; (2) chunk reclamation은 LSM tree가 사용하는 extent를 스캔하여 빈 공간을 회수하고 재배치된 청크를 가리키도록 메타데이터를 업데이트한다.

**Race 시나리오:**
```
초기: metadata = {chunk A, chunk B, chunk C}
       extent 0: [A][B]  extent 1: [C]  extent 2: []

1. Compaction이 새 청크 D를 extent 0에 기록:
   extent 0: [A][B][D]

2. Compaction이 메타데이터 업데이트 전에 선점됨

3. Reclamation이 extent 0 선택:
   - A, B는 메타데이터에 있으므로 extent 2로 대피
   - D는 메타데이터에 없으므로 드롭
   - extent 0 리셋

4. Compaction 재개, 메타데이터에 D 포인터 추가:
   - D는 이제 dangling pointer!
```

수정: compaction이 새 청크를 기록하는 extent를 메타데이터를 가리키도록 업데이트할 수 있을 때까지 잠그도록 함

### 12. 코드베이스 규모 및 비용 효율성

| 컴포넌트 | 라인 수 |
|----------|---------|
| **ShardStore Implementation** | 44,048 |
| Unit & integration tests | 19,540 |
| **Reference models** | 450 |
| Functional correctness checks | 4,860 |
| Crash consistency checks | 2,661 |
| Concurrency checks | 901 |
| **Total** | 72,460 |

**비용 효율성:**
- Reference model + 검증 harness = 구현의 **약 13%**
- FSCQ, VeriBetrKV 등 full formal verification의 3-10x 오버헤드와 비교하면 매우 경제적

### 13. 엔지니어링 팀 채택

이러한 lightweight formal methods를 엔지니어링 워크플로우에 통합함으로써 팀은 복잡한 crash consistency와 concurrency 문제를 포함해 16개의 이슈가 프로덕션에 도달하는 것을 방지했다. 특히 이 접근법은 비-formal-methods 전문가들에 의해 채택되어 엔지니어들이 reference model의 개발과 유지보수에 기여했다.

**채택 지표:**
- 테스트 harness 코드의 18%는 비-formal-methods 전문가가 작성
- 3명의 엔지니어가 각각 100줄 이상의 검증 코드 작성
- 4명의 엔지니어가 새로운 stateless model checking harness 작성
- 코드 리뷰 시 "동시성 harness가 필요한가?"가 표준 질문이 됨

### 14. 핵심 교훈

#### 조기 탐지

ShardStore 개발 초기, 설계가 아직 반복되고 코드가 점진적으로 전달되고 있을 때 formal methods 작업을 시작했다. API가 안정된 컴포넌트를 모델링하는 데 집중함으로써 명세와 모델 코드의 과도한 변경을 피했다.

#### 지속적 검증

Reference model을 코드베이스에 긴밀하게 통합하는 것이 검증이 코드 변경에 따라 효과적으로 유지되도록 하는 데 중요했다. 개발자는 빌드를 깨지 않기 위해 코드가 변경될 때마다 모델을 업데이트해야 한다. Rust로 모델을 작성하면 이러한 업데이트의 오버헤드가 실용적일 정도로 낮아진다.

#### 언어 선택

초기에는 익숙한 모델링 언어(Alloy, SPIN, Yggdrasil 스타일 Python)로 reference model을 작성하고 Rust 코드를 이에 대해 검사하는 도구를 개발할 것을 상상했다. 팀과 장기 유지보수 영향을 논의한 후에야 Rust로 직접 모델을 작성하는 것이 훨씬 나은 선택임을 깨달았고, reference model이 unit testing의 mock으로 이중 역할을 할 수 있다는 것을 나중에 깨달았다.

---

## 내가 얻은 인사이트
