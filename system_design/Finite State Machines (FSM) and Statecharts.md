# Finite State Machines (FSM) and Statecharts

## 출처
- **문서**: State Design Pattern / Statecharts
- **저자**: Refactoring.Guru / David Harel (Statechart 창시자, 1987)
- **게재**: Refactoring.Guru, Statecharts.dev
- **원문**: 
  - https://refactoring.guru/design-patterns/state
  - https://statecharts.dev/

---

## AI 요약

### FSM(Finite State Machine)이란?
- **유한 상태 머신**: 프로그램이 특정 시점에 가질 수 있는 **유한한 개수의 상태(state)**와, 상태 간의 **전이(transition)** 규칙을 정의한 모델
- 현재 상태에 따라 프로그램의 동작이 달라지며, 특정 이벤트 발생 시 다른 상태로 전환됨
- 예시: 문서의 상태(초안 → 검토 중 → 게시됨), 미디어 플레이어(정지 → 재생 → 일시정지)

### State 패턴 (디자인 패턴)
- **문제**: 상태에 따라 동작이 달라지는 객체를 if/switch 조건문으로 구현하면, 상태가 많아질수록 코드가 복잡해지고 유지보수가 어려워짐
- **해결**: 각 상태를 별도의 클래스로 분리하고, Context 객체가 현재 상태 객체에 작업을 위임
- **핵심 구조**:
  - **Context**: 현재 상태 객체에 대한 참조를 유지하고, 상태별 작업을 위임
  - **State Interface**: 모든 구체 상태 클래스가 구현해야 할 메서드 정의
  - **Concrete States**: 각 상태에 특화된 동작 구현, 상태 전환 로직 포함

### State 패턴 예시 (미디어 플레이어)

```python
# Context
class AudioPlayer:
    def __init__(self):
        self.state = ReadyState(self)
        self.playing = False
    
    def change_state(self, state):
        self.state = state
    
    def click_play(self):
        self.state.click_play()
    
    def click_lock(self):
        self.state.click_lock()

# State Interface
class State:
    def __init__(self, player):
        self.player = player
    
    def click_play(self):
        pass
    
    def click_lock(self):
        pass

# Concrete States
class LockedState(State):
    def click_lock(self):
        if self.player.playing:
            self.player.change_state(PlayingState(self.player))
        else:
            self.player.change_state(ReadyState(self.player))
    
    def click_play(self):
        pass  # 잠금 상태에서는 아무 동작 없음

class ReadyState(State):
    def click_lock(self):
        self.player.change_state(LockedState(self.player))
    
    def click_play(self):
        self.player.playing = True
        self.player.change_state(PlayingState(self.player))

class PlayingState(State):
    def click_lock(self):
        self.player.change_state(LockedState(self.player))
    
    def click_play(self):
        self.player.playing = False
        self.player.change_state(ReadyState(self.player))
```

### Statechart란?
- **강화된 FSM**: 전통적인 FSM의 한계(상태 폭발, 복잡도 증가)를 해결한 확장 모델
- David Harel이 1987년 논문에서 제안한 "복잡한 시스템을 위한 시각적 형식주의"
- **주요 확장 기능**:
  - **계층적 상태(Hierarchical States)**: 상태 안에 하위 상태 포함 가능
  - **병렬 상태(Parallel States)**: 여러 상태가 동시에 활성화
  - **Guard 조건**: 전이에 조건 추가 가능
  - **Entry/Exit 액션**: 상태 진입/퇴장 시 자동 실행
  - **History 상태**: 이전 상태 기억 및 복원

### Statechart vs FSM

| 특성 | FSM | Statechart |
|------|-----|------------|
| 상태 구조 | 평면(flat) | 계층적(hierarchical) |
| 병렬 처리 | 불가능 | 가능 (parallel states) |
| 상태 수 증가 시 | 상태 폭발(state explosion) | 계층화로 관리 가능 |
| 복잡도 | 단순한 경우만 적합 | 복잡한 시스템에 적합 |

### 실전 활용 사례

**1. UI 상태 관리**
```python
# 로그인 폼 상태
states = {
    'idle': 사용자 입력 대기,
    'validating': 입력값 검증 중,
    'submitting': 서버 전송 중,
    'success': 로그인 성공,
    'error': 오류 표시
}
```

**2. 주문 처리 워크플로우 (Uber 사례)**
```
주문 접수 → 배정 중 → 픽업 중 → 배달 중 → 완료
         ↘ 취소됨
```

**3. 게임 AI**
```
대기 → 순찰 → 추적 → 공격 → 후퇴
     ↘ 죽음
```

### State 패턴의 장단점

**장점**:
- **Single Responsibility Principle**: 상태별 코드를 별도 클래스로 분리
- **Open/Closed Principle**: 새 상태 추가가 기존 코드 수정 없이 가능
- **가독성**: 거대한 조건문 대신 명확한 상태 클래스로 코드 단순화
- **테스트**: 각 상태를 독립적으로 테스트 가능

**단점**:
- **오버헤드**: 상태가 적고 변경이 드물면 과도한 설계
- **학습 곡선**: 새로운 패러다임으로 팀 적응 시간 필요
- **코드 증가**: 작은 FSM의 경우 코드 라인 수 증가

### Statechart 도구 및 라이브러리

**JavaScript/TypeScript**:
- **XState**: 가장 인기 있는 Statechart 라이브러리, SCXML 호환
- 시각화 도구 제공, React/Vue 통합 지원

**Python**:
- **transitions**: 경량 FSM 라이브러리
- **sismic**: SCXML 기반 Statechart 인터프리터

**표준**:
- **SCXML**: W3C 표준(2005-2015), Statechart XML 형식
- 다양한 언어에서 SCXML 실행 가능

### 언제 사용하는가?

**FSM/State 패턴 사용 시기**:
- 객체의 동작이 상태에 따라 크게 달라질 때
- 상태 수가 많고, 상태별 코드가 자주 변경될 때
- 거대한 조건문이 클래스를 오염시킬 때

**Statechart 사용 시기**:
- FSM으로는 복잡도를 관리할 수 없을 때
- 계층적 상태나 병렬 상태가 필요할 때
- 팀 간 커뮤니케이션에 시각적 도구가 필요할 때

---

## 내가 얻은 인사이트

**1. "이미 FSM을 코딩하고 있다"는 사실**
대부분의 프로그래머는 이미 상태 머신을 구현하고 있지만, 코드 곳곳에 숨어 있어서 명시적이지 않다. if/switch문으로 상태를 관리하는 순간 이미 FSM을 만드는 것이다. State 패턴은 이를 명시적이고 관리 가능하게 만든다.

**2. "상태 폭발"은 실제 문제다**
전통적인 FSM은 상태가 증가할수록 기하급수적으로 복잡해진다. 5개 독립 변수가 각각 2가지 상태를 가지면 2^5 = 32개 상태가 필요하다. Statechart의 계층적/병렬 상태는 이 문제를 우아하게 해결한다.

**3. "시각화의 힘"**
Statechart는 단순한 코드 패턴이 아니라 비개발자도 이해할 수 있는 시각적 도구다. PM, QA, 디자이너가 같은 다이어그램을 보고 소통할 수 있다는 점이 실무에서 매우 강력하다. 특히 복잡한 워크플로우나 UI 상태 관리에서 오해를 줄이고 모든 엣지 케이스를 탐색하는 데 도움이 된다.
