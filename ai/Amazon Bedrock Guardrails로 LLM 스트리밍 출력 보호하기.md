# Amazon Bedrock Guardrails로 LLM 스트리밍 출력 보호하기

## Source
- **블로그**: [Amazon Bedrock Guardrails로 LLM 스트리밍 출력 보호하기](https://aws.amazon.com/ko/blogs/tech/protecting-llm-streaming-output-with-amazon-bedrock-guardrails/)
- **저자**: Kwangwoo Lee (AWS 솔루션즈 아키텍트)
- **발행일**: 2025년 2월 4일
- **분야**: Amazon Bedrock, Amazon Bedrock Guardrails, LLM Safety

## AI Summary

### 1. 배경 및 문제의식
- LLM 스트리밍 출력은 실시간 대화형 AI 애플리케이션에서 핵심 기능이지만, 즉각적인 콘텐츠 제어와 보안 관리가 어려움.
- Amazon Bedrock Guardrails는 원치 않는 콘텐츠 방지, 프롬프트 주입/탈옥 차단, 민감한 개인정보 제거 등 다양한 보안 기능 제공.
- ApplyGuardrail API를 통해 Amazon Bedrock 파운데이션 모델과 외부 3rd party LLM에도 적용 가능.

### 2. Guardrails 적용 방식
#### Amazon Bedrock Model API 통합 방식
- Converse/ConverseStream, InvokeModel/InvokeModelWithResponseStream API 호출 시 온/오프 설정.
- 동기 모드: 응답 버퍼링 후 완전 검사 → 정확도 높으나 지연 발생.
- 비동기 모드: 즉시 전송 후 백그라운드 검사 → 빠르지만 부적절한 콘텐츠 노출 가능.
- 장점: 간편한 통합, 다양한 사용 사례 대응.
- 단점: Bedrock 파운데이션 모델에 최적화, 외부 LLM 통합 제한, 버퍼 크기 조절 제약.

#### ApplyGuardrail API 방식
- 독립적인 API로 Amazon Bedrock Model API 호출과 별개로 Guardrails 적용.
- Amazon Bedrock 파운데이션 모델 + 외부 3rd party LLM 모두 지원.
- 버퍼 크기 세밀 조절 가능 → 응답 지연과 안전성 균형 최적화.

### 3. LLM 스트리밍 응답 Guardrails 적용 패턴
모든 패턴은 **버퍼 매니저** 모듈 필요: LLM 스트리밍 응답 버퍼링 및 ApplyGuardrail API 호출 제어. 최대 버퍼 크기는 비용 최적화를 위해 1000단어 권장.

#### 실시간 스트리밍 (Post-Guardrails)
- **동작**: LLM 생성 텍스트를 즉시 사용자에게 전달 → 이후 Guardrails 적용.
- **흐름**: 
  1. 사용자 입력 → 2. LLM 스트리밍 응답 → 3. 즉시 사용자 전달 + 버퍼 저장 → 4. 버퍼 일정 크기 도달 시 ApplyGuardrail API 호출 → 5-7. 반복.
- **장점**: 빠른 응답, 자연스러운 대화 흐름.
- **단점**: 부적절한 콘텐츠 일시 노출 위험, 마스킹 기능 효과 제한적(이미 표시 후 적용).
- **버퍼 크기 영향**: 작은 버퍼 = 빠른 필터링 + 높은 비용, 큰 버퍼 = 비용 절감 + 긴 노출 시간.

#### 지연 처리 (Pre-Guardrails)
- **동작**: Guardrails 검사 후 승인된 텍스트만 사용자에게 전달.
- **흐름**:
  1. 사용자 입력 → 2. LLM 스트리밍 응답 → 버퍼 저장 → 3. 버퍼 일정 크기 도달 시 ApplyGuardrail API 호출 → 4. 검사 통과 텍스트만 사용자 전달 → 5-7. 반복.
- **장점**: 부적절한 콘텐츠 노출 방지, 마스킹 기능 효과적 활용.
- **단점**: 초기 응답 시간 느림, 사용자 경험 저하 가능.
- **버퍼 크기 영향**: 작은 버퍼 = 빠른 초기 응답 + 높은 비용, 큰 버퍼 = 비용 절감 + 긴 초기 지연.

#### 동적 버퍼 (Dynamic Buffer)
- **동작**: 초기 작은 버퍼 + 이후 큰 버퍼로 안전성과 응답성 동시 최적화.
- **흐름**:
  1. 사용자 입력 → 2. 작은 초기 버퍼 저장 → 3. ApplyGuardrail API 호출 → 4. 검사 통과 텍스트 전달 → 5. 큰 버퍼 사용 → 6-7. 반복.
- **장점**: 빠른 초기 응답 + 콘텐츠 안전성 보장, Pre-Guardrails 방식의 안전성 유지하며 응답 속도 개선.
- **단점**: 버퍼 매니저 구현 복잡도 증가, 버퍼 크기 차이로 인한 일시 지연 가능(출력 비율 조절로 해결).
- **최적화**: 버퍼 크기 비율에 따른 출력 조절(예: 초기 500단어, 이후 1000단어 → 2:1 출력 비율), 버퍼 단계 세분화 가능.

### 4. 데모 결과 및 분석
- **설정**: Claude 3.5 v1, PII 이름 마스킹, "세계 유명 CEO 20명" 프롬프트.
- **버퍼 크기**: Post-Guardrails 1000단어, Pre-Guardrails 1000단어, Dynamic Buffer 250/500/1000단어.
- **분석**:
  - 응답 속도: 실시간 스트리밍 > 동적 버퍼 > 지연 처리
  - 안전성: 지연 처리 = 동적 버퍼 > 실시간 스트리밍
  - 사용자 경험: 실시간 스트리밍 > 동적 버퍼 > 지연 처리

### 5. 권장 사용 사례
- **실시간 스트리밍 (Post-Guardrails)**: 빠른 응답이 중요한 사내 용도, 보안 요구사항 낮은 환경.
- **지연 처리 (Pre-Guardrails)**: 높은 보안 요구(금융, 의료), 민감한 정보 다루는 대고객 서비스.
- **동적 버퍼 (Dynamic Buffer)**: 다양한 시나리오, 보안·성능·비용 효율성 균형 필요한 환경.

## 내가 얻은 인사이트

Amazon Bedrock Guardrails의 ApplyGuardrail API를 활용한 3가지 스트리밍 패턴(Post/Pre/Dynamic)은 안전성·응답성·비용의 트레이드오프를 유연하게 조정할 수 있는 다양한 패턴에 대한 정리이다.
