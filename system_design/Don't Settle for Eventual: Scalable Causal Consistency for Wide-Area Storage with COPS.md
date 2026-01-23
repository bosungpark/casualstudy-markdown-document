# Don't Settle for Eventual: Scalable Causal Consistency for Wide-Area Storage with COPS

## 출처
- **링크**: https://dl.acm.org/doi/10.1145/2043556.2043593
- **저자**: Wyatt Lloyd, Michael J. Freedman, Michael Kaminsky, David G. Andersen
- **학회**: SOSP 2011 (23rd ACM Symposium on Operating Systems Principles)

---

## AI 요약

### 문제 정의
소셜 네트워크 같은 대규모 웹 애플리케이션은 **ALPS 속성**이 필요하다:
- **A**vailability (가용성)
- **L**ow latency (낮은 지연)
- **P**artition tolerance (파티션 허용)
- **S**calability (확장성)

CAP 정리에 따르면 이런 시스템에서는 Strong Consistency를 제공할 수 없다. 기존 시스템들은 Eventual Consistency를 선택했지만, 이로 인해 직관에 반하는 이상 현상(anomaly)들이 발생한다.

### Eventual Consistency의 문제점 (Anomaly 예시)

**Photo-List 문제**:
```
C1: put(photo)  →  put(list에 photo 추가)
C2:                                       get(list) → get(photo) ← 실패!
```
C2가 list에서 사진 참조를 봤는데, 정작 사진은 아직 복제가 안 됐을 수 있음.

**Privacy 문제**:
```
Alice: unfriend(Bob) → put(private_photo)
Bob:                                      get(friend_list) → get(private_photo)
```
Bob이 구 친구 목록을 읽고, 새 비공개 사진을 볼 수 있음.

### 해결책: Causal+ Consistency

**Causal Consistency**: 인과적으로 연결된 연산들의 순서를 보장
- A → B (A가 B보다 먼저)이면, B를 본 클라이언트는 반드시 A도 봐야 함
- 인과적으로 무관한 연산들은 순서를 강제하지 않음 → 성능 이점

**Causal+의 "+"**: Convergent Conflict Handling
- 동시 쓰기 충돌 시 모든 복제본이 동일한 방식으로 해결 (Last-Writer-Wins 등)

### COPS 아키텍처

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Datacenter 1   │     │  Datacenter 2   │     │  Datacenter 3   │
│  ┌───┐ ┌───┐   │     │  ┌───┐ ┌───┐   │     │  ┌───┐ ┌───┐   │
│  │S1 │ │S2 │   │ ←── │  │S1 │ │S2 │   │ ──→ │  │S1 │ │S2 │   │
│  └───┘ └───┘   │  비동기 └───┘ └───┘   │  복제  └───┘ └───┘   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**핵심 메커니즘**:
1. **클라이언트 Context**: 각 연산의 의존성(dependency) 추적
2. **의존성 전파**: `put(y, value, deps=[x/v2])` 형태로 쓰기 시 의존성 포함
3. **의존성 확인**: 원격 데이터센터는 의존성이 충족될 때까지 쓰기를 블록
4. **Lamport Clock**: 버전 번호 생성 (클럭 드리프트 문제 해결)

### COPS-GT: Get Transactions

여러 키를 일관되게 읽는 기능 추가:
```
get_trans(ACL, photo_list)
1. 먼저 각 키의 최신 버전과 의존성 조회
2. 의존성 체크: 반환된 값들이 서로의 의존성을 만족하는지 확인
3. 불만족 시 2라운드로 특정 버전 요청
```

### 성능
- 단일 서버: 52,000 gets/sec, 30,000 puts/sec
- 서버 수 증가에 따라 선형 확장

### 한계점
- **외부 인과성 미감지**: COPS 외부의 통신(전화, 메신저 등)으로 발생하는 인과관계는 추적 불가
- **충돌 쓰기 처리**: Last-Writer-Wins는 카운터 증가 같은 경우에 부적절
- **트랜잭션 제한**: 읽기 전용 트랜잭션만 지원
- **의존성 오버헤드**: 의존성 추적/전파/검증 비용

---

## 내가 얻은 인사이트

### 1. "타협점"의 명시적 정의가 중요하다
이 논문의 핵심 공헌은 ALPS 환경에서 달성 가능한 **가장 강한 일관성 모델**을 정의한 것이다. "Eventual이 싫으면 Strong으로 가라"가 아니라, 그 사이의 스펙트럼에서 최적점을 찾았다. 이건 시스템 설계에서 매우 중요한 사고방식이다.

### 2. 인과성 추적의 실용성과 한계
COPS의 Context 기반 의존성 추적은 우아하지만, 현실에서는 다음과 같은 이유로 한계가 있다:
- **외부 채널**: 사람들은 Slack, 전화, 이메일로도 소통함
- **클라이언트 복잡성**: 브라우저 탭 여러 개, 모바일 앱 등 단일 Context 유지가 어려움
- **결국 애플리케이션 레벨 고려 필요**: COPS가 모든 인과성을 추적해주지 않음

### 3. AI/LLM 시스템에 적용할 점
RAG 시스템이나 에이전트에서도 비슷한 일관성 문제가 발생한다:
- **Vector DB 업데이트**: 문서 임베딩과 메타데이터가 동시에 업데이트되지 않으면 불일치
- **Multi-Agent 시스템**: 에이전트 A의 결과를 에이전트 B가 읽을 때 인과적 순서 보장 필요
- **분산 메모리**: 여러 노드에 분산된 장기 메모리의 일관성

Causal Consistency는 Strong Consistency보다 구현이 간단하면서도 대부분의 anomaly를 방지할 수 있어, AI 시스템의 상태 관리에 좋은 기준점이 될 수 있다.

### 4. "대부분의 경우"와 "최악의 경우"
논문에서 중요한 관찰: 인과적으로 무관한 연산들은 어떤 순서로 보여도 괜찮다. 이건 시스템 설계에서 **"정말 순서가 필요한 것"**과 **"그냥 언젠가 보이면 되는 것"**을 구분하는 것이 성능에 큰 영향을 준다는 점을 상기시킨다.

### 5. 실제 도입이 적은 이유에 대한 고찰
MIT 강의 노트에서 언급했듯이, Causal Consistency는 학계에서는 인기 있지만 실제 배포된 시스템에서는 드물다. 왜일까?
- **복잡성 대비 이점**: Eventual로도 충분한 경우가 많음
- **Primary-Site 모델**: Facebook처럼 쓰기를 한 곳에서 처리하면 더 단순
- **Strong Consistency도 가능해짐**: Spanner 같은 시스템이 성능 저하를 감수할 만큼 좋아짐

이건 "이론적으로 최적"이 "실용적으로 최선"과 다를 수 있다는 교훈을 준다.