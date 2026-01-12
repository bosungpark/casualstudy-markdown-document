# DHT-based Communications Survey: Architectures and Use Cases

## 출처
- **링크**: https://arxiv.org/abs/2109.10787
- **저자**: Yahya Hassanzadeh-Nazarabadi, Sanaz Taheri Boshrooyeh, Safa Otoum, Seyhan Ucar, Ozalp Ozkasap
- **발표일**: 2021년 9월 22일 (arXiv v1)
- **분야**: Distributed Computing (cs.DC)
- **상태**: Preprint (Peer review 전)

---

## AI 요약

### 논문의 목적

**"최초의 종합적인 DHT 기반 애플리케이션 서베이"**

기존 서베이들과의 차이점:
```
기존 서베이:
- 특정 도메인에 국한 (예: MANETs만, OSN만)
- 일반적 DHT 기능만 다룸 (Storage, Routing, Lookup)

이 논문:
- 7개 주요 도메인 횡단 조사
- System architecture & Communication 관점
- 다양한 DHT 기반 솔루션 식별
```

---

### 조사 대상 7개 도메인

**1. Edge and Fog Computing**
**2. Cloud Computing**
**3. Blockchain**
**4. Internet of Things (IoT)**
**5. Online Social Networks (OSNs)**
**6. Mobile Ad Hoc Networks (MANETs)**
**7. Vehicular Ad Hoc Networks (VANETs)**

---

### DHT란 무엇인가? (배경지식)

**Distributed Hash Table (분산 해시 테이블)**

**기본 개념**:
```
일반 Hash Table:
Key → Hash Function → Index → Value
(단일 머신에 저장)

Distributed Hash Table:
Key → Hash Function → Node ID → Value
(여러 노드에 분산 저장)

핵심:
- Key-value 쌍을 여러 노드에 분산 저장
- 어떤 노드든 효율적으로 값 검색 가능
- 노드 추가/제거 시 최소한의 재분배
```

**주요 특징**:
```
1. Autonomy & Decentralization
   - 중앙 조정 없이 노드들이 집합적으로 시스템 형성

2. Fault Tolerance
   - 노드 지속적 join/leave/fail에도 신뢰성 유지

3. Scalability
   - 수백만 노드에서도 효율적 작동
   - O(log n) 복잡도 (n = 참여 노드 수)

4. Efficiency
   - 각 노드는 소수의 다른 노드와만 조정
   - 멤버십 변경 시 제한된 작업량
```

**유명한 DHT 알고리즘** (2001년 등장):
```
1. Chord (MIT)
   - Ring 구조
   - Consistent hashing

2. CAN (Content Addressable Network)
   - 다차원 좌표 공간

3. Pastry (Microsoft Research)
   - Prefix-based routing

4. Tapestry (UC Berkeley)
   - Plaxton-style routing
```

**실제 사용 사례**:
```
BitTorrent: 분산 트래커
Kad Network: eMule/aMule
IPFS (InterPlanetary File System)
Freenet: 익명 파일 공유
Ethereum: 노드 발견
Tox: 탈중앙화 메신저
```

---

### 논문의 핵심 기여

**1. 포괄적 분류 체계**

기존 연구를 넘어서는 DHT 응용:
```
일반적으로 알려진 것:
- Storage (저장)
- Routing (라우팅)
- Lookup (검색)

이 논문이 추가로 식별한 것:
- Aggregation (집계)
- Task Scheduling (작업 스케줄링)
- Resource Management & Discovery (리소스 관리 및 발견)
- Clustering & Group Management (클러스터링 및 그룹 관리)
- Federation (연합)
- Data Dependency Management (데이터 의존성 관리)
- Data Transmission (데이터 전송)
```

**2. 도메인별 심층 분석**

각 도메인에서:
- System Architecture
- Communication Patterns
- Routing Mechanisms
- Technological Aspects

**3. 미해결 문제 및 연구 방향 제시**

---

### 도메인별 상세 분석

### **Domain 1: Cloud Computing**

**DHT 활용 분야**:
```
1. Decentralized Task Scheduling
   - 중앙 스케줄러 없이 작업 분배
   
2. Content Aggregation
   - 분산 데이터 수집 및 종합

3. Resource Management
   - CPU, Memory, Storage 동적 할당

4. Object Storage
   - S3 같은 분산 객체 저장소

5. Load Balancing
   - 노드 간 부하 균등 분배
```

**예시 시스템**:
```
- Dynamo (Amazon)
  → DynamoDB의 기반
  → Consistent hashing 사용

- Cassandra (Apache)
  → Chord-inspired DHT
  → 수천 노드 확장

- Riak
  → Amazon Dynamo 기반

- Voldemort (LinkedIn)
  → DHT 기반 key-value store

- Compute Cost Optimization
  → AWS IaaS 플랫폼 최적화
  → 각 DHT 노드 = VM 인스턴스
```

**클라우드에서 DHT의 장점**:
```
1. 단일 실패 지점(SPOF) 제거
2. 수평 확장성
3. 데이터 복제 자동화
4. 지리적 분산
5. 비용 효율성
```

---

### **Domain 2: Edge and Fog Computing**

**배경**:
```
Cloud Computing:
- 원격 데이터센터에 작업 위임
- 높은 레이턴시

Edge/Fog Computing:
- 최종 사용자 가까이에서 처리
- 낮은 레이턴시
- 네트워크 대역폭 절약
```

**DHT 역할**:
```
1. Edge Node Discovery
   - 가까운 edge 노드 찾기

2. Task Offloading
   - 모바일 기기 → Edge 서버로 작업 이동

3. Content Caching
   - 인기 콘텐츠 edge에 캐싱

4. Resource Allocation
   - Edge 리소스 동적 관리
```

**특징**:
```
- 낮은 레이턴시 요구사항
- 빈번한 노드 변경 (모바일 기기)
- 지리적 근접성 중요
```

---

### **Domain 3: Blockchain**

**DHT와 블록체인의 결합**:
```
문제:
- 블록체인 노드 발견 어려움
- P2P 네트워크 유지 복잡

DHT 해결책:
- Structured P2P overlay
- 효율적 노드 발견
- 데이터 가용성 보장
```

**활용 사례**:
```
1. Node Discovery
   - 새 노드가 네트워크 참여 시
   - 기존 노드 빠르게 찾기

2. Block Propagation
   - 새 블록을 네트워크에 전파

3. Data Availability
   - 블록체인 데이터 분산 저장
   - Full node가 아니어도 검색 가능

4. Sharding
   - 블록체인 파티셔닝
   - 확장성 향상
```

**예시**:
```
Ethereum:
- Kademlia DHT 사용
- 노드 발견 프로토콜

IPFS (InterPlanetary File System):
- DHT 기반 파일 시스템
- 블록체인과 통합
```

---

### **Domain 4: Internet of Things (IoT)**

**IoT의 특수성**:
```
특징:
- 수백만~수십억 기기
- 리소스 제약 (CPU, Memory, Battery)
- 동적 네트워크 토폴로지
- 이질적 기기

DHT 필요성:
- 중앙 서버 부담 감소
- 확장성
- 자가 조직화
```

**DHT 활용**:
```
1. Service Discovery
   - 특정 기능 제공 기기 찾기
   - 예: "온도 센서 찾기"

2. Data Aggregation
   - 센서 데이터 수집 및 종합

3. Resource Discovery
   - 이용 가능한 리소스 찾기

4. Energy-Efficient Routing
   - 배터리 고려한 라우팅
```

---

### **Domain 5: Online Social Networks (OSNs)**

**중앙화된 OSN의 문제**:
```
Facebook, Twitter 등:
- 단일 기업 통제
- 프라이버시 우려
- 검열 가능
- 서비스 중단 위험
```

**분산형 OSN (DHT 기반)**:
```
목표:
- 탈중앙화
- 사용자 데이터 소유권
- 검열 저항성

DHT 활용:
1. Profile Storage
   - 사용자 프로필 분산 저장

2. Friend Discovery
   - 친구 찾기

3. Content Distribution
   - 포스트, 사진 분산

4. Spam Protection
   - 분산 평판 시스템

5. Data Dependency Management
   - 소셜 그래프 관리
```

**예시**:
```
Diaspora:
- 분산형 소셜 네트워크
- Pod 기반 (DHT 활용)

Scuttlebutt:
- P2P 소셜 네트워크
- 오프라인 동기화
```

---

### **Domain 6: Mobile Ad Hoc Networks (MANETs)**

**MANET 특성**:
```
정의:
- 인프라 없는 무선 네트워크
- 노드들이 직접 통신
- 동적 토폴로지

도전과제:
- 노드 이동성
- 빈번한 연결 끊김
- 제한된 전송 범위
- 네트워크 파티셔닝/병합
```

**DHT 적용의 어려움**:
```
Internet DHT vs MANET DHT:

Internet:
- 상대적으로 안정적
- 높은 대역폭
- 유선 연결

MANET:
- 높은 이동성
- 제한된 대역폭
- 무선 연결
- 배터리 제약

→ 다른 알고리즘과 명세 필요
```

**DHT 기반 MANET Routing**:
```
1. Scalable Routing
   - 대규모 MANET에서 확장성

2. Data Transmission
   - 효율적 데이터 전달

3. Dynamic Topology Management
   - 변화하는 토폴로지 적응

4. Traffic Overhead Mitigation
   - 라우팅 오버헤드 감소
```

**기존 서베이와의 차이**:
```
기존 MANET DHT 서베이:
- Routing protocols만 연구

이 논문:
- Routing 넘어서
- Data transmission
- Dynamic topology management
- Traffic overhead mitigation
```

---

### **Domain 7: Vehicular Ad Hoc Networks (VANETs)**

**VANET 특성**:
```
MANET의 특수 케이스:
- 노드 = 차량
- 매우 높은 이동성 (시속 100km+)
- 예측 가능한 이동 패턴 (도로 따라)
- 안전 관련 애플리케이션
```

**DHT 활용**:
```
1. Distributed Cluster Management
   - 차량 그룹화
   - 클러스터 헤드 선출

2. Service Discovery
   - 주변 서비스 찾기
   - 예: 주차장, 주유소

3. Scalable Routing
   - 대규모 차량 네트워크

4. Security & Privacy
   - 익명 통신
   - 위치 프라이버시
```

**기존 서베이와의 차이**:
```
기존 VANET DHT 서베이:
- Cluster management만

이 논문:
- Service discovery
- Scalable routing
- Security
- Privacy
```

**안전 애플리케이션**:
```
- 사고 경보
- 교통 정보 공유
- 협력 주행
```

---

### 논문의 방법론

**분류 체계 (Taxonomy)**:

**1. System Architecture 관점**:
```
- Hierarchical vs Flat
- Hybrid architectures
- Layer-based designs
```

**2. Communication 관점**:
```
- Overlay vs Underlay communication
- Hop-to-hop routing
- End-to-end delivery
```

**3. Routing 관점**:
```
- Proactive vs Reactive
- Geographic routing
- Content-based routing
```

**4. Technological 관점**:
```
- Chord, Kademlia, Pastry 등 알고리즘
- 구현 플랫폼
- 성능 메트릭
```

---

### Overlay vs Underlay Communication

**핵심 개념**:

```
Underlay Network:
- 물리적 네트워크
- IP, Ethernet, WiFi 등
- 실제 연결

Overlay Network:
- 논리적 네트워크
- Underlay 위에 구축
- DHT가 만드는 가상 토폴로지
```

**예시**:
```
DHT Overlay:
Node A → Node B → Node C (논리적 경로)

Underlay Network:
A → Router1 → Router2 → B → Router3 → C (물리적 경로)

핵심:
- Overlay에서 1 hop = Underlay에서 여러 hop
- DHT는 overlay에서 효율적 라우팅 제공
```

**논문의 Figure 11 설명**:
```
좌측: Underlay network (물리적)
우측: DHT overlay (논리적)

일대일 대응:
- 각 물리 노드 ↔ DHT 노드
- DHT routing path → 물리 경로로 매핑
```

---

### 미해결 문제 (Open Problems)

**각 도메인별로 식별**:

**Cloud Computing**:
```
- Multi-cloud 환경에서 DHT 통합
- Cost-performance trade-off 최적화
- 실시간 탄력성
```

**Edge/Fog Computing**:
```
- 매우 낮은 레이턴시 요구사항
- 이질적 edge 기기 관리
- 모바일 edge 노드 처리
```

**Blockchain**:
```
- DHT 기반 sharding 성능
- Cross-shard 통신 효율성
- 합의 알고리즘과 DHT 통합
```

**IoT**:
```
- 극도로 리소스 제약된 기기
- 에너지 효율성
- 보안 및 프라이버시
```

**OSN**:
```
- 확장성과 일관성 균형
- 소셜 그래프 효율적 저장
- 검열 저항성 vs 불법 콘텐츠
```

**MANETs**:
```
- 높은 이동성 처리
- 네트워크 파티셔닝 대응
- 에너지 효율적 라우팅
```

**VANETs**:
```
- 극도로 높은 이동성 (시속 100km+)
- 안전 관련 실시간 요구사항
- 프라이버시 보장
```

---

### 연구 방향 (Future Research Guidelines)

**Cross-domain 이슈**:
```
1. Heterogeneity
   - 다양한 도메인 통합
   - 범용 DHT 프레임워크

2. Security & Privacy
   - Malicious node 방어
   - Sybil attack 대응
   - 익명성 보장

3. Scalability
   - 수십억 노드 지원
   - 효율적 상태 관리

4. Performance
   - 레이턴시 최적화
   - 대역폭 효율성
   - 에너지 소비 감소
```

---

## 내가 얻은 인사이트
