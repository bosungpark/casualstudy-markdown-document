# Sloppy Quorum과 Hinted Handoff의 한계

## 출처
- **아티클/논문**: Sloppy Quorum and Hinted Handoff: Quorum in the times of failure
- **저자/출처**: Distributed Computing Musings, GeeksforGeeks
- **링크**:
  - https://distributed-computing-musings.com/2022/05/sloppy-quorum-and-hinted-handoff-quorum-in-the-times-of-failure/
  - https://www.geeksforgeeks.org/system-design/what-is-sloppy-quorum-and-hinted-handoff/

---

## AI 요약

### 1. 문제의 시작: Strict Quorum의 한계

기존 쿼럼 모델의 문제점:

```
정상 상황:
Client → [Node A] [Node B] [Node C]
         W=2 만족 → 성공

네트워크 파티션 발생:
         ┌─────────────┐    ║    ┌─────────────┐
         │  Cluster 1  │    ║    │  Cluster 2  │
         │ [A]    [B]  │    ║    │    [C]      │
         └─────────────┘    ║    └─────────────┘
                          파티션

Client(Cluster 1) → W=2 필요, but C 접근 불가 → 실패
```

Strict Quorum은 **가용성을 희생**하고 일관성을 선택한다.

---

### 2. Sloppy Quorum: 가용성을 위한 타협

#### 핵심 아이디어
> 원래 담당 노드가 불가능하면, **임시 대리 노드**에 저장하고 성공 처리

```
Preference List: [A, B, C] (원래 담당)
Fallback List:   [D, E, F] (대리 후보)

C 장애 시:
Client → [A] ✓  [B] ✓  [C] ✗ → [D] ✓ (대리 저장)
         W=2 만족 → 성공으로 처리
```

#### Strict vs Sloppy 비교

| 항목 | Strict Quorum | Sloppy Quorum |
|------|---------------|---------------|
| 장애 시 동작 | 쓰기 실패 | 대리 노드에 저장 |
| 가용성 | 낮음 | 높음 |
| 일관성 | 강함 | Eventual |
| 쿼럼 보장 | 항상 N개 중 선택 | N 외부 노드 포함 가능 |

---

### 3. Hinted Handoff: 복구 메커니즘

#### 동작 과정

```
1. 장애 발생
   [A] [B] [C]  →  [A] [B] [X]
                          ↓
                    [D]가 C 대신 저장
                    + hint 메타데이터 기록

2. 복구 대기
   [D]: "이 데이터는 C의 것" (hint 보관)
        주기적으로 C에 ping

3. 장애 복구
   [C] 복구됨
        ↓
   [D] → [C]: 데이터 전송 (handoff)
        ↓
   [D]: hint 삭제
```

#### Hint 구조

```json
{
  "target_node": "C",
  "data": { "key": "user:123", "value": "..." },
  "timestamp": "2024-01-15T10:30:00Z",
  "ttl": 3600
}
```

---

### 4. 치명적인 한계들

#### 한계 1: Strict Majority가 아님

```
동시 쓰기 시나리오:

Writer 1: [A, B, D] 에 x=1 저장  (C 장애, D가 대리)
Writer 2: [A, C, E] 에 x=2 저장  (B 장애, E가 대리)

겹치는 노드: A뿐
→ 두 값이 공존, 충돌 감지 불가
```

| 문제 | 설명 |
|------|------|
| 쿼럼 겹침 깨짐 | 대리 노드 포함 시 R + W > N 무효화 |
| 충돌 감지 불가 | 다른 노드셋에 동시 쓰기 허용 |
| 버전 분기 | 어느 것이 "최신"인지 판단 불가 |

#### 한계 2: Hinted Handoff 실패 시 데이터 유실

```
시나리오:
1. C 장애 → D가 대리 저장
2. D도 장애 발생 (hint 보관 중)
3. C 복구, but D의 데이터는 영원히 유실

Timeline:
──────────────────────────────────────────────
C:     ████████ 장애 ████████████████ 복구
D:            ▓▓ 대리 저장 ▓▓ 장애 ████
                              ↑
                         데이터 유실 지점
```

#### 한계 3: 일관성 지연 (Consistency Lag)

```
파티션 지속 시간 동안:

Cluster 1 (A, B):     x = 새로운 값
Cluster 2 (C):        x = 오래된 값

Reader가 C에서 읽으면 → Stale Read 발생
```

| 지연 요인 | 설명 |
|-----------|------|
| 파티션 지속 시간 | 복구까지 불일치 지속 |
| Handoff 큐 처리 | 누적된 hint 순차 처리 |
| 대량 복구 병목 | 장기 장애 후 동기화 폭주 |

#### 한계 4: 리소스 오버헤드

```
장기 장애 시 Hint 누적:

[D] Hint Storage:
├── hint_001: target=C, size=1KB
├── hint_002: target=C, size=2KB
├── hint_003: target=C, size=1KB
│   ... (수천 개)
└── hint_999: target=C, size=3KB

→ 메모리 압박, 복구 시 I/O 폭주
```

---

### 5. 사용해야 할 때 vs 피해야 할 때

| 적합한 경우 | 부적합한 경우 |
|-------------|---------------|
| Eventual Consistency 허용 | 강한 일관성 필수 |
| Write-heavy 워크로드 | 실시간 일관성 요구 |
| 높은 가용성 우선 | 금융/의료 등 크리티컬 시스템 |
| 일시적 장애가 대부분 | 장기 장애 빈번 |
| 데이터 유실 일부 허용 | Zero data loss 요구 |

---

### 6. 실제 시스템 적용 사례

| 시스템 | 적용 방식 | 특이사항 |
|--------|-----------|----------|
| **Amazon DynamoDB** | Sloppy Quorum + Hinted Handoff | 원조 Dynamo 논문 기반 |
| **Apache Cassandra** | 설정으로 활성화 가능 | `hinted_handoff_enabled` |
| **Riak** | 기본 활성화 | 3시간 hint TTL |
| **Voldemort** | LinkedIn 내부 사용 | Dynamo 클론 |

---

## 내가 얻은 인사이트

### 트레이드오프 관점

1. **"성공"의 정의가 달라진다**
   - Strict Quorum: N개 중 W개에 저장 = 성공
   - Sloppy Quorum: 아무 W개에 저장 = 성공
   - 같은 "W=2 성공"이라도 의미가 완전히 다름

2. **가용성의 비용**
   - Sloppy Quorum은 "쓰기 실패" 대신 "나중에 정리"를 선택
   - 하지만 "나중"이 오지 않을 수도 있음 (hint 노드 장애)
   - 가용성을 얻는 대가로 데이터 유실 위험을 감수

### 설계 관점

1. **Hinted Handoff는 보험이 아니다**
   - "어차피 handoff가 있으니까 괜찮아"는 위험한 사고
   - Hint 노드도 장애날 수 있고, hint가 누적되면 복구가 느려짐
   - 추가적인 Anti-Entropy 메커니즘(Merkle Tree 등)이 필수

2. **멤버십 변동이 적을 때만 효과적**
   - Hinted Handoff는 "일시적 장애"를 가정
   - 노드가 영구 제거되거나 자주 바뀌면 hint가 영원히 처리 안 됨
   - 클러스터 안정성이 전제 조건
