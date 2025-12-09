# Dynamo: Amazon's Highly Available Key-value Store

## 출처
- **논문**: Dynamo: Amazon's Highly Available Key-value Store
- **저자**: Giuseppe DeCandia, Deniz Hastorun, Madan Jampani, Gunavardhan Kakulapati, Avinash Lakshman, Alex Pilchin, Swaminathan Sivasubramanian, Peter Vosshall, Werner Vogels (Amazon.com)
- **발표**: SOSP 2007 (ACM Symposium on Operating Systems Principles)
- **원문**: https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf
- **블로그**: https://www.allthingsdistributed.com/2007/10/amazons_dynamo.html

---

## AI 요약

### 핵심 설계 목표: "Always-On" Experience

Dynamo는 Amazon의 **고가용성(High Availability)**을 최우선 목표로 설계된 분산 키-값 저장소입니다. "장바구니에 담기는 절대 실패하면 안 된다"는 비즈니스 요구사항에서 출발했습니다.

**핵심 Trade-off**: 
- **Availability over Consistency** (가용성 우선, 일관성 양보)
- **Always Writeable** (쓰기는 절대 거부하지 않음)
- **Eventual Consistency** (최종적 일관성)

### CAP 정리의 실무 적용

Dynamo는 **CAP 정리**(Consistency, Availability, Partition tolerance)에서 **AP**를 선택했습니다:
- Network Partition 발생 시에도 서비스 지속
- 일시적 불일치 허용, 나중에 Reconciliation

### 핵심 기술 합성 (Synthesis of Techniques)

Dynamo는 **기존 기술들의 조합**으로 설계되었습니다:

| 문제 | 기술 | 장점 |
|------|------|------|
| **Partitioning** | Consistent Hashing | 점진적 확장성 |
| **High Availability for Writes** | Vector Clocks + Read Reconciliation | 버전 크기가 업데이트 빈도와 독립적 |
| **Temporary Failures** | Sloppy Quorum + Hinted Handoff | 일부 복제본 불가용 시에도 가용성/내구성 보장 |
| **Permanent Failures** | Merkle Trees (Anti-Entropy) | 백그라운드에서 divergent replicas 동기화 |
| **Membership & Failure Detection** | Gossip Protocol | 중앙화된 레지스트리 없이 대칭성 유지 |

### 1. Consistent Hashing (일관된 해싱)

**문제**: 노드 추가/제거 시 데이터 재분배를 최소화해야 함

**해결책**: 
- Hash 공간을 **논리적 Ring**으로 모델링 (0 ~ 2^128)
- 각 노드를 Ring의 여러 지점에 배치 (Virtual Nodes)
- Key는 Ring을 시계방향으로 걷다가 첫 번째 노드에 할당

**장점**:
- 노드 추가/제거 시 인접 노드만 영향받음
- Virtual Nodes로 부하 균등 분산
- Heterogeneity (이질성) 지원: 고성능 노드에 더 많은 Virtual Nodes 할당

### 2. Vector Clocks (벡터 시계)

**문제**: Concurrent Writes로 인한 충돌 버전 관리

**동작 원리**:
```
D1: [(Sx, 1)]           ← 서버 Sx가 첫 쓰기
D2: [(Sx, 2)]           ← Sx가 다시 쓰기 (D1 대체)
D3: [(Sx, 2), (Sy, 1)]  ← 서버 Sy가 D2 기반 쓰기

D4: [(Sx, 2), (Sz, 1)]  ← 서버 Sz가 D2 기반 쓰기 (D3와 병렬)

→ D3와 D4는 인과 관계 없음 (Conflict!)
→ 둘 다 클라이언트에게 반환
→ 클라이언트가 Semantic Reconciliation 수행
```

**핵심**:
- Vector Clock으로 **Causality (인과 관계)** 추적
- 충돌 감지는 시스템이, **해결은 Application**이 담당

### 3. Sloppy Quorum + Hinted Handoff

**전통적 Quorum 문제점**:
- N개 노드 중 정확히 특정 N개가 살아있어야 함
- 노드 장애 시 가용성 저하

**Sloppy Quorum**:
- **"첫 N개의 건강한 노드"**에 쓰기 (원래 노드가 아니어도 OK)
- Preference List에서 순서대로 선택

**Hinted Handoff** (힌트 기반 전달):
```
정상: A, B, C 노드가 Key K 담당
장애: A 노드 다운
해결: D 노드가 A 대신 저장 (metadata에 "원래는 A" 힌트)
복구: A 노드 복구 시 D → A로 데이터 전달 후 D는 삭제
```

**장점**:
- W=1 설정 시 단 1개 노드만 살아있으면 쓰기 성공
- Data Center 전체 장애에도 대응 가능

### 4. Merkle Trees (Anti-Entropy)

**문제**: Hinted Handoff로 해결 못한 영구적 불일치 동기화

**동작 원리**:
- 각 Key Range마다 Merkle Tree 유지
- Leaf = Hash(individual keys)
- Parent = Hash(children)

**효율성**:
```
Root Hash 비교 → 같으면 동기화 불필요
다르면 → Children Hash 비교 → 재귀적으로 Divergent Keys만 식별
```

**장점**:
- 전체 데이터셋 전송 없이 차이만 교환
- Disk Read 최소화

### 5. Gossip Protocol (가십 프로토콜)

**Membership 관리**:
- 각 노드가 매초 랜덤 노드 1개와 통신
- Membership 변경 이력을 교환 및 Reconcile
- **Eventually Consistent View** 유지

**Failure Detection**:
- 중앙 레지스트리 없음 (Decentralized)
- 로컬 실패 감지: "B가 내 메시지에 응답 안 함 → B 실패로 간주"
- Periodic Retry로 복구 확인

### Tunable Trade-offs: (N, R, W)

**설정 가능한 파라미터**:
- **N**: 복제본 개수 (Replication Factor)
- **R**: 읽기 성공에 필요한 최소 응답 수
- **W**: 쓰기 성공에 필요한 최소 응답 수

**전형적 설정**: (N=3, R=2, W=2)
- R + W > N → Quorum-like 일관성
- R + W ≤ N → 높은 가용성, 낮은 일관성

**극단적 설정**:
- W=1: 쓰기 절대 실패 안 함 (최고 가용성, 내구성 위험)
- R=1, W=N: 읽기 성능 최적화 (Read Engine 용도)

### 99.9th Percentile SLA

**평균이 아닌 99.9% 기준**:
- Amazon은 **평균/중간값이 아닌 99.9th percentile**로 SLA 측정
- 이유: VIP 고객(구매 이력 많음) = 처리 시간 길음 → 평균으로는 커버 안 됨
- 목표: 300ms 이내 99.9% 요청 처리

**성능 최적화**:
- Write Coordinator를 Load Balancing하여 Hot Spot 방지
- Client-driven Coordination: Load Balancer 홉 제거 (30ms 개선)
- Write Buffer: In-memory 버퍼로 Durability vs Performance Trade-off

### Conflict Resolution: When & Who?

**When to Resolve?**
- **Traditional DB**: Write 시점에 해결 (충돌 시 쓰기 거부)
- **Dynamo**: Read 시점에 해결 (Always Writeable 유지)

**Who Resolves?**
- **Data Store**: "Last Write Wins" 같은 단순 정책
- **Application**: Business Logic 기반 해결 (예: 장바구니 Merge)

**Shopping Cart 예시**:
```
상황: 네트워크 파티션으로 장바구니 2개 버전 발생
- V1: [책, 신발]
- V2: [책, 모자]

해결: Application이 Merge → [책, 신발, 모자]
부작용: 삭제한 아이템이 부활 가능 (Deleted items can resurface)
```

### Production 경험 (2006~2007)

**규모**:
- Shopping Cart Service: **수천만 요청/일**, 3백만+ 체크아웃/일
- Session Management: **수십만 동시 활성 세션**
- 99.9995% 성공률 (타임아웃 없이)
- **데이터 손실 사건 0건**

**Divergent Versions 비율**:
- 99.94% 요청: 정확히 1개 버전
- 0.00057%: 2개 버전
- 0.00047%: 3개 버전
- 0.00009%: 4개 버전

→ **충돌은 매우 드물게 발생** (주로 Concurrent Writers 증가 시)

### 파티셔닝 전략 진화

**Strategy 1** (초기): T random tokens per node
- 문제: 부하 불균등, Bootstrapping 느림, Merkle Tree 재계산 비용

**Strategy 2** (중간): T tokens + Equal-sized partitions
- 문제: 최악의 Load Balancing

**Strategy 3** (최종): Q/S tokens, Equal-sized partitions
- **Q**: 전체 파티션 수 (Q >> N)
- **S**: 노드 수
- 각 노드: Q/S개 토큰 할당
- **장점**: 최고 효율성, 파티션 파일 단위 전송 (Faster Bootstrapping), 간편한 Archival

---

## 내가 얻은 인사이트

다이나모는 일시적 불일치를 허용하되 절대 쓰기를 거부하지 않는 쓰기 장인으로 언제나 새로운 기술에 등장 배경에는 비지니스적 요구사항이 있었다.