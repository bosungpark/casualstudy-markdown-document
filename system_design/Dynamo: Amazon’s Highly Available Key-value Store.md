# **Dynamo: Amazon’s Highly Available Key-value Store**

## 출처

* **링크**: [https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)
* **논문 공개 요약/리뷰**: Amazon Science 페이지, RiakKV 요약 등 ([Amazon Science][1])

---

## AI 요약

**Dynamo**는 아마존의 핵심 서비스들(예: 쇼핑 카트, 세션 상태 저장 등)의 **항상 가용성(always-on)** 요구를 충족하기 위해 설계된 **분산 키-값 저장소 (distributed key-value store)** 시스템이다. 이는 수만 대의 서버와 전 세계 여러 데이터센터를 가로지르는 크고 작은 실패가 계속 발생하는 환경에서 **높은 가용성, 확장성, 예측 가능한 지연**을 제공하는 것을 목표로 한다. ([Amazon Science][1])

논문에서 Dynamo는 **일관성(consistency)**을 일부 포기하고(즉, CAP 정리를 받아들이고) 대신 **가용성(availability)과 partition tolerance**를 최우선으로 설계되었다. 이를 위해 **분산/비집중적 구조**, **유연한 일관성 조정**, **낙관적 버전 관리**, **자율 복제 관리** 등 여러 기술을 결합했다. ([Amazon Science][1])

---

## Dynamo의 디자인 목표

**핵심 요구** (SLA 기준) ([Amazon Science][1])

| 목표                             | 설명                                    |
| ------------------------------ | ------------------------------------- |
| **항상 쓰기 가능 (Always writable)** | 네트워크 파티션 혹은 노드 장애가 있어도 쓰기 요청을 거부하지 않음 |
| **확장성 (Scalability)**          | 새로운 노드를 추가함으로써 수평 확장 가능               |
| **대칭성 (Symmetry)**             | 모든 노드는 동일한 역할                         |
| **이기종 지원 (Heterogeneity)**     | 서로 다른 성능의 하드웨어 활용 가능                  |
| **예측 가능한 레이턴시**                | 99.9% 요청이 SLA 내 처리                    |
| **가용성 최우선**                    | 일관성보다 가용성을 우선하는 트레이드오프                |

---

## 주요 설계 요소

### 1) **Partitioning + Consistent Hashing**

Dynamo는 **consistent hashing**을 사용하여 키 공간을 원형 토폴로지로 분할하고, 키를 노드에 분배한다. 노드가 추가/제거되더라도 전체 키 재분배 비용이 낮다. ([Docslib][2])

* **가상 노드 (virtual nodes)**를 도입해 각 물리 노드가 여러 위치를 차지, 부하 균형을 개선하는 구조를 제공 ([Docslib][2])

---

### 2) **Replication (복제)**

키는 consistent hashing으로 결정된 기본 노드 및 그 뒤따르는 N-1개의 노드에 **N 중복**으로 저장된다. 이로써 장애 시 다른 복제본에서 서비스를 계속 제공할 수 있다. ([Docslib][2])

---

### 3) **Tunable Consistency (Quorum-like)**

읽기 R, 쓰기 W, 복제 N 설정을 통해 **R + W > N** 또는 **R + W ≤ N** 같은 조합으로 **일관성과 가용성 간 트레이드오프**를 조절할 수 있다. ([Docslib][2])

---

### 4) **Versioning + Conflict Resolution**

Dynamo은 **충돌을 서버 수준에서 해결하지 않고**, **애플리케이션 수준에 위임**한다. 이를 위해 **vector clocks**과 **object versioning**을 도입한다.

* **Vector clock**은 객체의 진화 히스토리를 나타내며
* 충돌이 감지되면 애플리케이션이 이를 병합하거나 결정하게 한다. ([Never stop learning!][3])

---

### 5) **Sloppy Quorum + Hinted Handoff**

네트워크 파티션 등으로 인해 특정 노드가 담당 위치에 쓰기 불가능할 때, 다른 노드가 대신 쓰기를 수행하고 나중에 원래 노드로 이를 **전달(handoff)**한다. 이 메커니즘이 Dynamo의 **가용성 제일주의**를 실현한다. ([Docslib][2])

---

### 6) **Anti-entropy + Merkle Trees**

비정상적 상태나 오래된 복제본이 있는 경우 Dynamo는 **Anti-entropy 프로토콜**을 통해 노드 사이 데이터를 동기화한다. 이때 **Merkle 트리**를 활용해 효율적으로 불일치하는 키만 비교하고 전송한다. ([Never stop learning!][3])

---

### 7) **Gossip-based Membership**

노드 상태와 ring 정보 등은 **Gossip 프로토콜**을 통해 분산적으로 공유 및 유지되어 중앙 관리 없이 각 노드가 최신 정보를 유지한다. ([Never stop learning!][3])

---

## Dynamo Operations (핵심 워크플로우)

### **Put(Key, Context, Object)**

1. 클라이언트는 partitioning을 통해 N 복제본이 어디인지 결정
2. **W**개의 복제본에 쓰기 시도
3. 만약 일부 노드가 불능이면 **sloppy quorum** 경로의 노드가 대신 처리
4. 성공한 replica set의 vector clock을 기반으로 버전 관리용 context를 반환

(이 구조로 항상 중단 없이 쓰기 가능) ([Docslib][2])

---

### **Get(Key)**

1. N replica 중 R개 노드로부터 버전 정보 요청
2. vector clock 충돌 검출
3. 중복 버전이 있으면 어플리케이션이 병합/결정

→ 결국 Dynamo는 **클라이언트가 일관성 문제를 일부 책임지는 API 모델**을 제공 ([Docslib][2])

---

## Dynamo의 트레이드오프와 특성

✔ **Availability 최우선** – Partition 상황에서도 쓰기/읽기 중단 없음 ([Amazon Science][1])
✔ **Eventual Consistency** – 최종 수렴만 보장 ([Riak Documentation][4])
✔ **Tunable Consistency** – SLA 목적에 맞게 R, W 조절 가능 ([Docslib][2])
✔ **Conflict Resolution 유연성** – 애플리케이션 수준 충돌 관리 ([Never stop learning!][3])
✔ **Decentralized Self-Managing** – Gossip 기반으로 노드 상태 유지 ([Never stop learning!][3])

---

## 내가 얻은 인사이트

### ≫ **CAP과 Dynamo**

Dynamo는 **가용성/partition tolerance**를 최우선으로 두는 설계 사례 그 자체다.
즉 **weak/loose consistency를 받아들이고**, 그 책임을 **애플리케이션 쪽으로 옮기는 구조적 선택**이 명확하다 — 이것이 현대 분산 스토어 설계 근간이 되었다. ([Amazon Science][1])

---

### ≫ **버전 분기와 충돌 처리의 본질**

vector clock과 object versioning은 단순히 충돌 탐지가 아니라, **분산 업데이트의 히스토리와 partial ordering**을 표현하는 추상이다. 이로써 Dynamo는 단일 linearized store 대신 *애플리케이션이 의미 있는 충돌 해결을 하도록 유도한다.* ([Never stop learning!][3])

---

### ≫ **Quorum + Hinted Handoff 조합**

sloppy quorum과 hinted handoff는 Dynamo에서 “available but temporarily sloppy”인 상태를 실용적으로 수용하는 핵심 메커니즘이며, 이 트레이드오프는 CAP의 현실적 적용 사례라고 볼 수 있다. ([Docslib][2])

---

### ≫ **영향**

이 논문의 기술들은 **Cassandra, Riak, Voldemort** 같은 시스템들의 기초가 되었고, 현대 NoSQL 스토어의 많은 디자인 패턴이 Dynamo에서 유래했다. ([off77th.github.io][5])
