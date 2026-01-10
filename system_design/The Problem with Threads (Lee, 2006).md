# The Problem with Threads (Lee, 2006)

## 출처
- **링크**: https://www2.eecs.berkeley.edu/Pubs/TechRpts/2006/EECS-2006-1.pdf

---

## AI 요약

### 논문의 핵심 주장
Edward Lee는 스레드 기반 동시성 프로그래밍이 본질적으로 **비결정적(non-deterministic)**이며, 이는 단순한 구현 문제가 아니라 **근본적인 설계 결함**이라고 주장합니다.

### 주요 문제점

**1. 비결정성의 본질**
- 스레드는 실행 순서를 보장하지 않아 같은 입력에도 다른 결과 발생 가능
- Race condition, Deadlock 등은 증상일 뿐, 근본 원인은 스레드 모델 자체
- 테스트로 검증 불가능: 한 번 성공해도 다음 실행에서 실패 가능

**2. 조합 복잡도(Combinatorial Explosion)**
- n개 스레드, 각 m개 명령어 → 가능한 인터리빙 경우의 수가 천문학적
- 예: 2개 스레드, 각 10개 명령어 → 184,756가지 실행 순서
- 정적 분석으로 모든 경우 검증 현실적으로 불가능

**3. Lock의 한계**
- Lock은 문제를 완화할 뿐 해결하지 못함
- Deadlock, Priority inversion, Convoying 등 새로운 문제 유발
- Lock granularity 설정이 성능과 정확성 트레이드오프

**4. 추상화 실패**
- 순차 프로그램은 추상화가 잘 작동 (함수, 모듈 등)
- 스레드는 추상화 경계를 넘어 상호작용 → 캡슐화 파괴
- 라이브러리 내부가 thread-safe한지 항상 확인 필요

### 대안 제시

**1. 메시지 패싱(Message Passing)**
- Erlang, CSP(Communicating Sequential Processes) 모델
- 공유 메모리 없음 → Race condition 원천 차단
- 명시적 통신으로 상호작용 가시화

**2. 데이터플로우(Dataflow)**
- 함수형 프로그래밍의 불변성(Immutability)
- 데이터 의존성만으로 실행 순서 결정
- Kahn Process Networks 등

**3. 동기 언어(Synchronous Languages)**
- Esterel, Lustre 등
- 논리적 시간(Logical time) 개념 도입
- 결정적 동시성 보장

### 핵심 통찰
> "Threads are wildly nondeterministic, and the job of the programmer becomes one of pruning that nondeterminism."

프로그래머의 역할이 비결정성을 제거하는 것이 되어서는 안 되며, 애초에 **결정적인 모델**을 사용해야 한다는 것이 논문의 결론입니다.

---

## 내가 얻은 인사이트

### LLM QA와의 연결점

**1. 비결정성의 유사성**
- 스레드: 같은 코드, 다른 실행 순서 → 다른 결과
- LLM: 같은 프롬프트, 다른 샘플링 → 다른 응답
- 둘 다 **확률적 시스템**으로 테스트의 근본적 어려움 공유

**2. "200번 시도, 95% 통과"의 의미**
- 인터뷰에서 나온 QA 기준이 사실은 **비결정성을 수치로 포착**하려는 시도
- Lee의 주장: 비결정성을 관리하는 것이 아니라 **제거**해야 함
- LLM에 적용: Temperature=0, Top-p=1 등으로 결정성 높이거나, 규칙 기반으로 전환

**3. 추상화 실패 문제**
- 프롬프트 간 의존성 관리 어려움 = 스레드 간 상호작용 문제
- "프롬프트 컴포넌트화" 니즈 = 안전한 추상화 경계 필요성
- 해결: 명확한 입출력 계약(Contract) 정의

**4. 테스트 불가능성**
- "한 번 통과했어도 다음엔 실패" = 스레드의 Heisenbug와 동일
- 현재 수동 테스트 방식은 Lee가 비판한 "비결정성 가지치기"에 불과
- 근본 해결: 결정적 부분(규칙)과 비결정적 부분(LLM) 명확히 분리
