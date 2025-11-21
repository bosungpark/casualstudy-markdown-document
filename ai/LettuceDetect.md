# LettuceDetect: A Hallucination Detection Framework for RAG Applications

## 링크
- **링크**: https://arxiv.org/abs/2502.17125

---

## AI 요약

### 핵심 문제
- RAG 시스템이 외부 지식을 활용함에도 여전히 hallucination 발생
- 기존 방법의 2가지 한계:
  1. **전통적 인코더 모델의 컨텍스트 윈도우 제약** (BERT 512 토큰, DeBERTA 512-24k)
  2. **LLM 기반 접근법의 계산 비효율성**

### LettuceDetect 모델

**기반 모델: ModernBERT**
- BERT의 현대화 버전 (2024년 발표)
- **확장된 컨텍스트: 최대 8,192 토큰** (Luna 대비 큰 개선)
- Rotary Positional Embeddings (RoPE) 사용
- Alternating local-global attention 메커니즘
- 2조 토큰으로 사전 학습 (텍스트 + 코드)
- 하드웨어 최적화 설계

**아키텍처**
- Token classification 모델
- Context-Question-Answer 삼중 구조 처리
- 토큰 레벨에서 unsupported claim 식별
- AutoModelForTokenClassification 활용
- ModernBERT backbone + 분류 헤드

### 구현 방식

**입력 구조**
```
[CLS] context [SEP] question [SEP] answer [SEP]
```
- 최대 길이: 4,096 토큰 (현재 버전, 8k 미사용)
- Context/Question 토큰: 마스킹 처리 (label=-100)
- Answer 토큰: 0(supported) or 1(hallucinated)

**학습 설정**
- 데이터셋: RAGTruth (18,000 샘플, 인간 주석)
- Optimizer: AdamW (lr=1e-5, weight_decay=0.01)
- Epochs: 6
- Batch size: 8
- GPU: NVIDIA A100
- Dynamic padding 적용

**추론**
- 각 answer 토큰의 hallucination 확률 예측
- Span-level 출력: 연속된 토큰 중 확률 > 0.5를 집계
- 토큰 레벨 F1로 평가

### Luna와의 차이점

| 항목 | Luna | LettuceDetect |
|------|------|---------------|
| 기반 모델 | DeBERTA-large (440M) | ModernBERT-large (396M) / base (150M) |
| 최대 컨텍스트 | 512-24k (chunking 필요) | 8,192 토큰 (네이티브) |
| 사전 학습 | NLI 체크포인트 활용 | ModernBERT 직접 사용 (NLI 없음) |
| 학습 데이터 | 자체 RAG QA (75k, GPT-4 주석) | RAGTruth (18k, 인간 주석) |
| 윈도우 집계 | 토큰별 max → min | 단일 모델 처리 (집계 불필요) |
| 추론 속도 | 0.23초 (평균) | 30-60 examples/sec |

**핵심 개선점**
- ModernBERT의 긴 컨텍스트 네이티브 지원으로 Luna의 복잡한 윈도우 집계 불필요
- 더 가벼우면서도 더 높은 성능
- 오픈소스 (MIT 라이선스)

### 성능 결과

**Example-level Detection (RAGTruth)**
- **LettuceDetect-large**: F1 79.22%
- Luna: F1 65.4% → **14.8% 개선**
- Fine-tuned Llama-2-13B: F1 78.7%
- RAG-HAT (Llama-3-8B, SOTA): F1 83.9%
- GPT-4-turbo: F1 63.4%

**Span-level Detection**
- **LettuceDetect-large**: F1 58.93%
- Fine-tuned Llama-2-13B: F1 52.7% → **6.2% 개선**
- 이전 SOTA 달성

**효율성**
- 모델 크기: Luna 대비 30배 작은 모델들과 비교 시 우위
- 추론 속도: 30-60 examples/sec (단일 GPU)
- RAG-HAT를 제외한 모든 모델 능가 (RAG-HAT는 8B 모델)

### 기술적 세부사항

**데이터셋 특성 (RAGTruth)**
- 평균 토큰 길이: 801
- 중앙값: 741
- 최소: 194, 최대: 2,632
- 3가지 태스크: QA, Data-to-text, Summarization
- Hallucination 타입:
  - Evident Conflict
  - Subtle Conflict
  - Evident Introduction of Baseless Information
  - Subtle Introduction of Baseless Information

**배포**
- GitHub: MIT 라이선스
- pip: `lettucedetect` 패키지
- HuggingFace: base & large 모델 공개
- Web demo: Streamlit 기반

---

## 내가 얻은 인사이트

- Luna 논문 저자가 직접 인용하고 비교한 후속 연구로, Luna의 개선판임
- ModernBERT라는 새로운 기반 모델이 게임 체인저 역할을 함
- 복잡한 구현로직 없이 순수 모델 체급 하나로 짱먹음
- Luna가 차지하던 SOTA 자리를 불과 8개월 만에 SOTA 업데이트함
- 다만 모델 크기의 한계는 여전히 존재
