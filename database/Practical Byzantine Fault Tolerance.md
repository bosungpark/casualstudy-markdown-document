# PBFT (Practical Byzantine Fault Tolerance)

## 논문 정보

- **제목**: Practical Byzantine Fault Tolerance
- **저자**: Miguel Castro, Barbara Liskov (MIT Laboratory for Computer Science)
- **발표**: OSDI 1999 (Third Symposium on Operating Systems Design and Implementation), New Orleans
- **링크**: http://pmg.csail.mit.edu/papers/osdi99.pdf
- **확장판**: ACM TOCS 2002 (Proactive Recovery 추가)

---

## 핵심 개념

PBFT는 **Byzantine Fault**를 견딜 수 있는 최초의 실용적인 합의 알고리즘. 이전 BFT 알고리즘들은 이론적 증명용이거나 동기 네트워크를 가정해서 실제 사용이 어려웠음.

### Byzantine Fault란?

- 노드가 임의의 악의적 행동을 할 수 있음
- 거짓 메시지 전송, 다른 노드에게 다른 값 전송, 의도적 지연 등
- Crash Fault (단순 정지)보다 훨씬 강력한 장애 모델

### Byzantine Generals Problem (비잔틴 장군 문제)

- Lamport가 1982년 제시한 문제
- N명의 장군 중 f명이 배신자일 때, 충성스러운 장군들이 동일한 결정에 도달해야 함
- 배신자는 서로 다른 장군에게 서로 다른 메시지를 보낼 수 있음

---

## 시스템 모델

### 노드 구성

- 총 **3f + 1** 개의 replica 필요 (f = 허용 가능한 Byzantine 노드 수)
- Raft는 2f + 1개면 충분 (Crash Fault만 가정)
- 왜 3f + 1인가? → 2f + 1 quorum이 반드시 f + 1개의 정직한 노드 포함

### 가정

- 비동기 네트워크 (메시지 지연/순서 보장 없음) → Safety 보장
- Partial Synchrony (약한 동기성) → Liveness 보장
- 암호학적 기법: 디지털 서명, MAC, 해시 함수
- 독립적 장애 확률 (다른 OS, 다른 관리자 권장)

### 역할

- **Primary (Leader)**: 클라이언트 요청 수신, 순서 할당, 합의 시작
- **Backup (Replica)**: Primary 검증, 합의 참여
- **Client**: 요청 전송, f+1개 동일 응답 수신 시 확정

---

## 3-Phase 프로토콜 (Normal Case)

```
Client → Primary → All Replicas → Client
         │
         ├─ PRE-PREPARE ──→ 모든 Replica
         │
         ├─ PREPARE ←────→ 모든 Replica (all-to-all)
         │
         └─ COMMIT ←─────→ 모든 Replica (all-to-all)
```

### Phase 1: Pre-Prepare

- Primary가 클라이언트 요청 수신
- 요청에 **sequence number (n)** 할당
- `<PRE-PREPARE, v, n, d>` 메시지를 모든 Backup에게 전송
  - v: view number
  - n: sequence number
  - d: 요청의 digest

### Phase 2: Prepare

- Backup이 Pre-Prepare 검증 후 `<PREPARE, v, n, d, i>` 브로드캐스트
- 검증 조건:
  - 서명/MAC 유효
  - view number가 현재 view와 일치
  - 같은 n에 다른 요청이 없음
  - n이 watermark 범위 내
- **prepared 상태**: Pre-Prepare + 2f개의 일치하는 Prepare 수신

### Phase 3: Commit

- prepared 상태 도달 시 `<COMMIT, v, n, d, i>` 브로드캐스트
- **committed-local 상태**: 2f + 1개의 일치하는 Commit 수신
- 이 시점에서 요청 실행 후 클라이언트에 응답

### 왜 3 Phase가 필요한가?

- 2 phase만 있으면 view change 시 안전성 보장 불가 -> 리더 교체 시, 최대한 합의 후 새로운 리더 시작
- Prepare: "이 요청을 이 순서로 처리하겠다"에 동의
- Commit: "충분한 노드가 동의했음"을 확인

---

## 메시지 구조

```
PRE-PREPARE: <PRE-PREPARE, v, n, d>_σp, m
  - v: view number
  - n: sequence number  
  - d: digest of request m
  - σp: primary's signature
  - m: client request

PREPARE: <PREPARE, v, n, d, i>_σi
  - i: replica identifier

COMMIT: <COMMIT, v, n, d, i>_σi
```

---

## View Change 프로토콜

Primary가 장애이거나 악의적일 때 새로운 Primary 선출.

### 트리거 조건

- Backup의 타이머 만료 (요청이 제시간에 처리되지 않음)
- f + 1개의 VIEW-CHANGE 메시지 수신

### 과정

1. Backup이 `<VIEW-CHANGE, v+1, n, C, P, i>` 브로드캐스트
   - n: 마지막 stable checkpoint의 sequence number
   - C: checkpoint 증명
   - P: prepared 상태인 요청들의 증명
2. 새 Primary (v+1 mod n)가 2f + 1개의 VIEW-CHANGE 수신
3. 새 Primary가 `<NEW-VIEW, v+1, V, O>` 브로드캐스트
   - V: 수신한 VIEW-CHANGE 메시지들
   - O: 새 view에서 re-propose할 PRE-PREPARE 메시지들
4. Backup들이 NEW-VIEW 검증 후 새 view 진입

### 핵심 보장

- committed된 요청은 view change 후에도 유지됨
- 새 Primary는 이전 view의 모든 committed 요청 포함

---

## Garbage Collection & Checkpoint

로그가 무한히 커지는 것을 방지.

### Checkpoint 프로토콜

- 매 K개 요청마다 checkpoint 생성 (보통 K=100)
- `<CHECKPOINT, n, d, i>` 메시지 브로드캐스트
  - n: 마지막으로 실행된 sequence number
  - d: state digest
- 2f + 1개의 일치하는 CHECKPOINT 수신 → **stable checkpoint**

### Garbage Collection

- stable checkpoint 이전의 모든 메시지 삭제 가능
- watermark 업데이트:
  - low watermark = stable checkpoint의 n
  - high watermark = low + K (또는 설정값)

---

## Safety & Liveness

### Safety (안전성)

- 모든 non-faulty replica가 동일한 순서로 요청 실행
- 비동기 네트워크에서도 보장
- Byzantine 노드가 f개 이하일 때 보장

### Liveness (활성성)

- 클라이언트 요청이 결국 처리됨
- **Partial Synchrony** 필요: 결국 메시지 지연에 상한이 생김
- View Change로 faulty primary 교체

### FLP Impossibility와의 관계

- 완전 비동기 시스템에서는 합의 불가능 (FLP 정리)
- PBFT는 Safety는 비동기에서, Liveness는 partial synchrony에서 보장

---

## PBFT vs Raft 비교

| 항목 | PBFT | Raft |
|------|------|------|
| **장애 모델** | Byzantine Fault (악의적 노드) | Crash Fault (단순 정지) |
| **필요 노드 수** | 3f + 1 | 2f + 1 |
| **통신 복잡도** | O(n²) - all-to-all | O(n) - leader to followers |
| **Phase 수** | 3 (Pre-prepare, Prepare, Commit) | 2 (AppendEntries + 응답) |
| **암호화** | 필수 (서명/MAC) | 불필요 |
| **성능** | 상대적 느림 | 상대적 빠름 |
| **확장성** | 제한적 (수십 노드) | 상대적 좋음 |
| **사용 환경** | 신뢰할 수 없는 환경, 블록체인 | 신뢰할 수 있는 환경, 내부 시스템 |

### 성능 수치 (Hyperledger Fabric 연구)

- Latency: Raft 1.89s vs PBFT 5.07s (Raft가 2.7배 빠름)
- Throughput: Raft 8.9 TPS vs PBFT 5.5 TPS
- 노드 증가 시: Raft는 latency 유지, PBFT는 최대 71% 증가

---

## 실제 사용 사례

### 블록체인

- Hyperledger Fabric (v0.6까지 PBFT, 이후 Raft로 전환)
- Tendermint (PBFT 변형)
- NEO (dBFT - delegated BFT)
- Zilliqa

### 파생 알고리즘

- Zyzzyva: Speculation 기반, 낙관적 실행
- HotStuff: Linear view change (O(n) 복잡도), Diem/Libra에서 사용
- RBFT: Redundant BFT
- MinBFT, FastBFT: Trusted hardware 활용

---

## PBFT의 한계

1. **O(n²) 통신 복잡도**: 노드 증가 시 메시지 폭발
2. **확장성 제한**: 실질적으로 수십 노드가 한계
3. **Byzantine 노드 비율**: 1/3 초과 시 안전성 붕괴
4. **Sybil 공격 취약**: Permissionless 환경에서 PoW/PoS 필요
5. **View Change 복잡성**: 구현 난이도 높음, 성능 저하 요인

---

## 핵심 인사이트

### 이론과 실용의 균형

- 이전 BFT 알고리즘들은 이론적 증명용 또는 동기 네트워크 가정
- PBFT는 "Practical"을 강조 - 실제 인터넷 환경에서 동작

### 암호화의 역할

- Crash Fault: 메시지 위조 불가 가정 → 암호화 불필요
- Byzantine Fault: 악의적 위조 가능 → 암호화 필수

### Quorum의 수학

- 3f + 1 노드에서 2f + 1 quorum
- 두 quorum의 교집합 ≥ f + 1 → 최소 1개의 정직한 노드 포함

### Phase 수와 안전성

- 2 phase: 합의 도달 가능하지만 view change 시 불안전
- 3 phase: view change 시에도 committed 상태 보존

### 블록체인과의 관계

- PBFT: Permissioned blockchain의 기반
- PoW/PoS: Permissionless에서 Sybil 저항 + 합의
- 최근 트렌드: PBFT의 finality + PoS의 Sybil 저항 결합