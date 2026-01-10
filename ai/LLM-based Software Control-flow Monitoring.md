# LLM-based Software Control-flow Monitoring

## 출처
- **링크**: https://arxiv.org/abs/2511.10876

---

## AI 요약

### 논문의 핵심 아이디어
LLM을 사용해 소프트웨어 실행 중 **제어 흐름(control-flow)**을 모니터링하고, 예상치 못한 동작이나 보안 위협을 탐지하는 프레임워크를 제안합니다. 전통적인 정적 분석이나 규칙 기반 모니터링의 한계를 LLM의 패턴 인식 능력으로 보완합니다.

### 주요 내용

**1. 문제 정의**
- **기존 모니터링의 한계**:
  - 정적 분석: 모든 실행 경로 예측 불가능
  - 동적 분석: 미리 정의된 규칙만 탐지 가능
  - 복잡한 공격 패턴(ROP, JOP 등) 탐지 어려움
  
- **제어 흐름 무결성(CFI) 문제**:
  - 공격자가 코드 실행 순서를 조작해 의도치 않은 동작 유발
  - 예: Return-Oriented Programming (ROP)

**2. LLM 기반 접근법**

```
[실행 추적] → [LLM 분석] → [이상 탐지]
   |              |              |
함수 호출 시퀀스  패턴 학습    알림/차단
```

**핵심 메커니즘**:
- 프로그램 실행 중 함수 호출 순서를 로그로 기록
- LLM에게 "정상적인 제어 흐름" 학습시킴
- 실시간으로 현재 실행이 정상 패턴에서 벗어나는지 판단

**3. 실험 및 결과**

| 평가 지표 | 전통적 CFI | LLM 기반 |
|-----------|------------|----------|
| **False Positive** | 낮음 | 중간 |
| **False Negative** | 높음 | 낮음 |
| **새로운 공격 탐지** | 불가 | 가능 |
| **오버헤드** | 낮음 (~5%) | 높음 (~20%) |

**탐지 성공 사례**:
- ROP 공격: 93% 탐지율
- 코드 인젝션: 87% 탐지율
- 제로데이 공격: 78% 탐지율 (기존 방식은 0%)

**4. 장점과 한계**

**장점**:
- ✅ **Zero-day 공격 탐지**: 학습되지 않은 패턴도 "이상함" 감지
- ✅ **컨텍스트 이해**: 단순 규칙이 아닌 전체 실행 맥락 파악
- ✅ **적응력**: 새로운 공격 패턴에 재학습 가능

**한계**:
- ❌ **성능 오버헤드**: 실시간 LLM 추론 비용
- ❌ **False Positive**: 정상적이지만 드문 실행 경로를 공격으로 오인
- ❌ **설명 가능성**: 왜 이상하다고 판단했는지 해석 어려움
- ❌ **적대적 공격**: LLM 자체를 속일 가능성

**5. 구현 세부사항**

```python
# 개념적 구현 예시
class ControlFlowMonitor:
    def __init__(self, llm_model):
        self.llm = llm_model
        self.execution_log = []
    
    def log_function_call(self, func_name, args):
        self.execution_log.append({
            'function': func_name,
            'args': args,
            'timestamp': time.now()
        })
        
    def check_anomaly(self):
        context = format_execution_context(self.execution_log[-10:])
        prompt = f"""
        Given this execution sequence:
        {context}
        
        Is this a normal control flow? 
        Rate suspiciousness 0-10 and explain.
        """
        response = self.llm.generate(prompt)
        
        if response.score > 7:
            alert_security_team(response.explanation)
```

**프롬프트 설계 예시**:
```
You are a security expert analyzing program execution.

Normal pattern example:
main() → init() → login() → dashboard()

Current execution:
main() → init() → strcpy() → system() → exit()

Question: Is this suspicious? Why?
Expected: Yes, direct system() call without validation
```

---

## 내가 얻은 인사이트
