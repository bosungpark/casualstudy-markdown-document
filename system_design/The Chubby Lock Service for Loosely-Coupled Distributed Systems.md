# The Chubby Lock Service for Loosely-Coupled Distributed Systems

## 출처
- **링크**: https://static.googleusercontent.com/media/research.google.com/en//archive/chubby-osdi06.pdf
- **저자**: Mike Burrows (Google)
- **학회**: OSDI 2006

---

## AI 요약

Google 내부에서 사용하는 **분산 락 서비스**. GFS, BigTable, MapReduce 등 Google의 핵심 인프라에서 **리더 선출**과 **메타데이터 저장**에 사용됨. 오픈소스 버전이 **Apache ZooKeeper**.

> "Building Chubby was an engineering effort... it was not research. We claim no new algorithms or techniques."

### Chubby가 해결하는 문제

분산 시스템에서 **리더 선출**은 어려운 문제:
- 여러 노드 중 누가 마스터인지 합의 필요
- Paxos를 직접 구현하면 복잡하고 에러 prone
- Chubby가 이 복잡성을 추상화해서 **간단한 파일/락 인터페이스**로 제공

### 핵심 설계

| 항목 | 내용 |
|------|------|
| **인터페이스** | UNIX 파일시스템과 유사 (파일, 디렉토리, 락) |
| **합의 알고리즘** | Paxos |
| **목표** | 가용성, 신뢰성 (성능은 부차적) |
| **락 종류** | Coarse-grained (초~분 단위, fine-grained 아님) |
| **구조** | Chubby Cell (보통 5개 서버) → 1개 Master 선출 |

### 왜 락 서비스인가? (vs Paxos 라이브러리)

1. **프로그램 구조 유지** - 기존 코드 최소 수정
2. **클라이언트 수 감소** - Paxos는 참여자 수에 민감
3. **익숙한 인터페이스** - 파일/락은 개발자에게 친숙
4. **부가 기능** - 소량 데이터 저장, 이벤트 알림

### 사용 예: 리더 선출

```
1. 노드들이 /ls/foo/primary 파일에 락 획득 시도
2. 락 획득 성공한 노드가 자신의 identity를 파일에 기록
3. 다른 노드들은 파일을 읽어 누가 리더인지 확인
4. 리더 죽으면 락 해제 → 새 리더 선출
```

### 주요 메커니즘

**Session & KeepAlive**
- 클라이언트는 주기적 KeepAlive로 세션 유지
- 세션 만료 = 락 자동 해제

**Lease**
- Master는 일정 시간(기본 12초→60초) 동안 리더십 보장
- Lease 갱신 실패 시 재선출

**Caching**
- 클라이언트가 파일 내용 캐시
- 변경 시 Master가 invalidation 전송

**Sequencer**
- 락 소유자가 변경되어도 stale 요청 방지
- 락 획득 시 sequencer 발급 → 서버가 검증

### 스케일링

| 방법 | 효과 |
|------|------|
| Chubby Cell 추가 | 지역별 분산 |
| Lease 시간 증가 (12s→60s) | KeepAlive 트래픽 감소 |
| Proxy 도입 | KeepAlive, Read 처리 분산 |
| 네임스페이스 파티셔닝 | Master 부하 분산 |

### 운영 통계 (논문 기준)

- 수만 클라이언트 동시 처리
- 61건 장애 중 52건은 30초 이내 복구
- 6건 데이터 손실 (4건 SW 버그, 2건 운영 실수)

### 교훈 & 실수

1. **개발자는 API를 예상과 다르게 사용함** - 락 서비스를 Name Service로 사용
2. **RPC 대신 KeepAlive에 데이터 피기백** - 트래픽 감소
3. **Aggressive caching 필요** - 읽기 비율 높음
4. **Quota 없으면 남용됨** - 나중에 추가

### ZooKeeper와의 관계

| | Chubby | ZooKeeper |
|---|--------|-----------|
| 개발 | Google (비공개) | Apache (오픈소스) |
| 인터페이스 | 파일시스템 + 락 | 계층적 key-value + watch |
| 용도 | 동일 (리더 선출, 설정 저장, 서비스 디스커버리) |

---

## 내가 얻은 인사이트
