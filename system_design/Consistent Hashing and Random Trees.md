# Consistent Hashing and Random Trees

## 출처
- **논문**: "Consistent Hashing and Random Trees: Distributed Caching Protocols for Relieving Hot Spots on the World Wide Web"
- **저자**: David Karger, Eric Lehman, Tom Leighton, Rina Panigrahy, Matthew Levine, Daniel Lewin (MIT)
- **발표**: ACM STOC 1997
- **원문**: https://www.cs.princeton.edu/courses/archive/fall09/cos518/papers/chash.pdf

---

## AI 요약

분산 캐싱에서 **Hot Spot 문제**를 해결하기 위한 **Consistent Hashing** 기법을 제안한 논문. 현재 DynamoDB, Cassandra, Memcached, CDN 등에서 널리 사용됨.

### 문제: Hot Spot

```
      ┌─────────┐
      │ Server  │ ← 수백만 요청 → 💥 Swamped!
      └─────────┘
         ▲▲▲▲▲
    Browser Browser Browser ...
```

특정 서버에 요청이 집중되면 **swamping** 발생:
- JPL 사이트 (Shoemaker-Levy 혜성 충돌)
- IBM 사이트 (Deep Blue vs Kasparov)
- 선거 결과 발표 사이트

### 기존 해결책의 문제

**일반 해시 함수** 사용 시:

```python
cache = hash(object) % n_caches  # n_caches = 3
```

캐시 추가/제거 시:

```
n=3: object → cache 1
n=4: object → cache 3  # 거의 모든 객체 재배치!
```

→ 캐시 변경 시 **대부분의 객체가 재할당**됨

---

### 해결책: Consistent Hashing

#### 핵심 아이디어

```
        0 (= 2π)
           │
    ●──────┼──────●  ← Cache A
           │
   ●───────┼───────●  ← Cache B
           │
      ●────┼────●  ← Cache C
           │
        Object → 시계방향 첫 번째 캐시
```

1. 캐시와 객체를 **원형 공간** [0, 1)에 해시
2. 객체는 **시계방향으로 가장 가까운 캐시**에 할당
3. 각 캐시는 **여러 개의 가상 노드(virtual node)**를 가짐

#### 속성 정의

| 속성 | 정의 |
|------|------|
| **Balance** | 객체가 캐시에 균등 분배 (≈ 1/n) |
| **Monotonicity** | 캐시 추가 시 객체는 기존 → 새 캐시로만 이동 (기존 간 이동 없음) |
| **Spread** | 서로 다른 뷰에서 한 객체가 할당되는 캐시 수가 적음 |
| **Load** | 서로 다른 뷰에서 한 캐시에 할당되는 객체 수가 적음 |

#### 구현

```python
# 각 캐시마다 k개의 가상 노드 생성 (k = O(log C))
for cache in caches:
    for i in range(k):
        point = hash(f"{cache}:{i}")  # [0, 1) 구간에 매핑
        ring[point] = cache

def get_cache(object):
    point = hash(object)
    # point보다 크거나 같은 첫 번째 캐시 찾기
    return ring.ceiling(point)  # O(log n)
```

**시간 복잡도**:
- 해시 계산: O(1) (expected)
- 캐시 추가/제거: O(log C)

---

### Consistent Hashing의 장점

#### 1. Minimal Redistribution

캐시 n개 → n+1개 추가 시:

| 방식 | 재배치되는 객체 |
|------|----------------|
| 일반 해시 (mod n) | ~100% |
| Consistent Hashing | ~1/n (최소 필요량) |

```
Before: [A]───[B]───[C]───[A]
After:  [A]─[D]─[B]───[C]───[A]
              ↑
         D에 할당된 객체만 이동
```

#### 2. Inconsistent Views 허용

각 클라이언트가 **서로 다른 캐시 목록**을 알아도 동작:

```
Client 1 view: {A, B, C}
Client 2 view: {A, C, D}
Client 3 view: {B, C, D}
```

→ 같은 객체가 여러 캐시에 복제되지만, **spread** 가 좋은 해시를 사용하면 보완이 가능함

---

### Random Trees (캐시 트리)

Hot spot 방지를 위한 두 번째 도구:

```
           [Server]
          /    \
      [Cache1] [Cache2]
      /  \      /  \
   [C3] [C4] [C5] [C6]  ← Leaf caches
     ↑
  Browser requests start here
```

**핵심 아이디어**:
1. 각 페이지마다 **다른 랜덤 트리** 사용
2. 요청은 leaf에서 시작 → root(server)로 올라감
3. 중간 캐시가 페이지를 가지고 있으면 거기서 반환

**장점**:
- 특정 페이지가 인기 있어도, 트리가 다르므로 **load balancing**
- 서버는 **tree depth**만큼만 요청받음
- 캐시는 q번 이상 요청받은 페이지만 저장 → **메모리 효율**

---

### 이론적 보장

| 측정값 | 보장 |
|--------|------|
| **지연시간** | O(log_d C) - 트리 깊이 |
| **캐시당 요청 수** | O(2 log_d C + log N / log log N) w.h.p. |
| **캐시당 저장 페이지** | O(R/qC + log R) w.h.p. |
| **Spread** | O(t log C) w.h.p. |
| **Load** | O(t log C) w.h.p. |

- C = 캐시 수
- R = 총 요청 수
- N = 신뢰도 파라미터
- t = 각 클라이언트가 아는 캐시 비율의 역수
- q = 캐시 저장 임계값

---

### 실제 적용 사례

| 시스템 | 용도 |
|--------|------|
| **Amazon DynamoDB** | 데이터 파티셔닝 |
| **Apache Cassandra** | 노드 간 데이터 분산 |
| **Memcached** | 분산 캐시 클러스터 |
| **Akamai CDN** | 콘텐츠 배포 (논문 저자들이 창업) |
| **Discord** | 메시지 라우팅 |
| **Chord DHT** | P2P 네트워크 |

---

### 가상 노드 (Virtual Nodes)

실제 구현에서 **load balancing**을 위해 사용:

```
Physical: [Node A] [Node B] [Node C]
                ↓
Virtual:  [A1][A2][A3] [B1][B2][B3] [C1][C2][C3]
                ↓
Ring:     A1--B2--C1--A3--B1--C2--A2--B3--C3
```

**장점**:
1. 더 균등한 부하 분배
2. 이질적 노드 처리 (강한 노드 = 더 많은 가상 노드)
3. 노드 추가/제거 시 점진적 재분배

**권장**: 가상 노드 수 = O(log C) per physical node

---

### Jump Consistent Hash (2014, Google)

Karger 방식의 단점:
- 메모리: O(n log n) - 가상 노드 저장
- 조회: O(log n) - 트리 탐색

**Jump Consistent Hash** (Lamping & Veach):

```python
def jump_hash(key, num_buckets):
    b, j = -1, 0
    while j < num_buckets:
        b = j
        key = ((key * 2862933555777941757) + 1) & 0xFFFFFFFFFFFFFFFF
        j = int((b + 1) * (2**31 / ((key >> 33) + 1)))
    return b
```

| 속성 | Karger | Jump Hash |
|------|--------|-----------|
| 메모리 | O(n log n) | O(1) |
| 조회 | O(log n) | O(log n) expected |
| 동적 추가 | O(log n) | N/A (순차만) |

---

### 핵심 인용

> "Consistent hashing differs substantially from that used in Plaxton/Rajaraman and other practical systems. Typical hashing based schemes do a good job of spreading load through a known, fixed collection of servers. The Internet, however, does not have a fixed collection of machines."

> "A consistent hash function is one which changes minimally as the range of the function changes."

---

### 역사적 의의

- **Daniel Lewin**: 논문 공저자 → **Akamai** 공동 창업자 (CDN 선구자)
  - 2001년 9/11 테러로 사망 (American Airlines Flight 11)
- **Tom Leighton**: 논문 공저자 → Akamai CEO
- 이 논문의 아이디어가 **현대 분산 시스템의 기반**이 됨

---
