# Raft: In Search of an Understandable Consensus Algorithm

## 출처
- **논문**: In Search of an Understandable Consensus Algorithm (Extended Version)
- **저자**: Diego Ongaro, John Ousterhout (Stanford University)
- **발표**: USENIX ATC 2014 (Best Paper Award)
- **원문**: https://raft.github.io/raft.pdf
- **공식 사이트**: https://raft.github.io/

---

## AI 요약

### 핵심 문제 정의
Raft는 **이해 가능성(Understandability)**을 최우선 설계 목표로 하는 합의 알고리즘입니다. Paxos와 동등한 결과를 제공하지만, Paxos의 복잡성 문제를 해결하기 위해 설계되었습니다.

### Raft vs Paxos
- **성능**: Paxos와 동등한 효율성 (equivalent to multi-Paxos)
- **내결함성**: 과반수(majority) 노드만 살아있으면 진행 가능 (예: 5대 중 2대 장애 허용)
- **차이점**: Paxos와 **구조적으로 다름** → 핵심 요소를 분리(decompose)하여 이해 가능성 향상
- **검증**: User Study를 통해 Paxos보다 학습이 쉬움을 증명

### 3대 핵심 구성 요소 분리 (Separation of Concerns)
Raft는 합의 알고리즘을 **독립적인 서브 문제**로 분해합니다:

1. **Leader Election (리더 선출)**
   - 기존 리더 장애 시 새 리더 선출
   - Term Number(임기 번호)로 리더 관리
   - Randomized Timeout으로 Split Vote 방지

2. **Log Replication (로그 복제)**
   - 리더가 클라이언트 명령을 로그에 기록
   - 팔로워에게 로그 엔트리 복제
   - 과반수 복제 완료 시 Commit

3. **Safety (안전성)**
   - **Leader Completeness**: 커밋된 엔트리는 모든 미래 리더의 로그에 존재
   - **State Machine Safety**: 동일한 로그 인덱스에 서로 다른 명령 적용 불가
   - **일관성 보장**: 모든 상태 머신이 동일한 순서로 동일한 명령 실행

### Replicated State Machine 패턴
- **목적**: 결함 허용 시스템 구축의 일반적 접근법
- **구조**: 각 서버 = State Machine + Log + Consensus Module
- **동작 원리**:
  1. 합의 알고리즘이 로그 명령 순서 합의
  2. 모든 상태 머신이 동일한 명령 시퀀스 실행
  3. 클라이언트에게는 단일 신뢰 가능 상태 머신으로 보임
  4. 소수 서버 장애에도 서비스 지속

### Stronger Degree of Coherency
Raft는 **더 강한 일관성**을 강제하여 고려해야 할 상태 수를 줄입니다:
- 로그는 반드시 **연속적**이어야 함 (no holes)
- 리더는 **가장 최신 로그**를 가진 후보만 선출됨
- 이전 Term의 로그 엔트리를 간접적으로만 커밋 (새 Term 엔트리로 커밋 확인)

### Cluster Membership Change (새로운 메커니즘)
- **문제**: 실행 중인 클러스터에서 서버 추가/제거 시 안전성 보장
- **해결책**: Overlapping Majorities (겹치는 과반수) 사용
- **Joint Consensus**: 구성 변경 시 과도기에 양쪽 구성의 과반수가 모두 승인해야 함
- **안전성**: Split Brain 없이 안전한 재구성 가능

### Term Numbers (임기 번호)
- **논리적 시계**: Term은 단조 증가하는 번호 (Logical Clock)
- **리더십 관리**: 각 Term은 최대 1명의 리더만 가짐
- **장애 탐지**: 오래된 Term Number를 가진 메시지 거부
- **선거 진행**: Term Number가 더 높은 후보가 우선권

### Log Entry 구조
각 로그 엔트리는 다음을 포함:
- **Command**: 상태 머신에 적용할 명령 (예: `set x to 3`)
- **Term Number**: 엔트리가 생성된 Term
- **Log Index**: 로그 내 위치

### Randomized Timeouts (핵심 설계 결정)
- **문제**: 동시에 여러 후보가 선거 시작 → Split Vote → 재선거 반복
- **해결**: 각 서버마다 **랜덤 선거 타임아웃** 설정 (예: 150-300ms)
- **효과**: 대부분의 경우 단일 서버만 먼저 타임아웃 → 빠른 리더 선출
- **단순성**: 복잡한 알고리즘 없이 간단한 난수로 해결

---

## 내가 얻은 인사이트

**Raft**는 문제를 **Leader Election, Log Replication, Safety로 분해**하고, **더 강한 제약**(로그 연속성, 최신 로그 보유자만 리더)을 강제하여 고려해야 할 상태 수를 줄임

**Paxos**는 합의 문제를 수학적으로 완벽하게 해결했지만, 구조가 불투명하여 구현과 확장이 어려움.

Paxos는 좀 두루뭉술하게 뜬구름 잡는 느낌이 있는데, 레프트는 세부 구현까지 꼼꼼히 설명한게 차이임.