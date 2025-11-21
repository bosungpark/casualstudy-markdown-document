# Luna: An Evaluation Foundation Model to Catch Language Model Hallucinations with High Accuracy and Low Cost

## 링크
- **링크**: https://arxiv.org/abs/2406.00975

---

## AI 요약

### 핵심 문제
- RAG 시스템에서 LLM이 검색된 컨텍스트와 무관한 정보를 생성하는 hallucination 문제가 심각
- 기존 hallucination 탐지 기법은 정확도, 낮은 지연시간, 저비용을 동시에 만족하지 못함
- 긴 컨텍스트(16k+ 토큰) 처리 시 기존 모델들의 성능이 급격히 저하됨

### Luna 모델 아키텍처

**기본 구조**
- DeBERTA-v3-Large (440M 파라미터) NLI 체크포인트 기반
- NLI의 entailment 개념을 활용: RAG 응답이 컨텍스트에 의해 지지되는지 판단
- 응답의 각 토큰에 대한 support probability를 예측하는 shallow classifier 추가

**학습 방식**
- NLI 분류 헤드 가중치로 hallucination 예측 헤드 초기화
- Hallucinated 토큰: 낮은 entailment 확률 + 높은 contradiction 확률
- Supported 토큰: 높은 entailment 확률 + 낮은 contradiction 확률
- Cross-entropy loss로 3 에포크 학습
- Learning rate: base 모델 5e-6, 분류 헤드 2e-5 (warmup + linear decay)

**데이터 증강 기법**
- Context 문서 삭제/삽입
- 질문과 응답을 배치 내에서 셔플링
- 각 변환에 맞춰 학습 레이블 동적 조정

### 긴 컨텍스트 처리 메커니즘

**문제 상황**
- RAG 시스템은 종종 16k 토큰 이상의 긴 컨텍스트 생성
- Naive chunking: 지지 정보가 여러 청크에 분산되면 false positive 발생

**Luna의 해결 방법: Span-level Prediction**

1. **컨텍스트 윈도우 분할**
   - 최대 시퀀스 길이 L에 맞춰 컨텍스트를 윈도우로 분할
   - 각 윈도우 = 컨텍스트 일부 + 전체 질문 + 전체 응답

2. **토큰 레벨 예측**
   - 각 윈도우에서 응답의 모든 토큰에 대한 support probability 계산
   - 윈도우 내 컨텍스트에 따라 학습 레이블 동적 조정

3. **윈도우 간 집계**
   - 각 응답 토큰에 대해 모든 윈도우의 최댓값 선택
   - 예제 레벨 확률 = min(모든 응답 토큰의 support 확률)
   - Hallucination 확률 = 1 - Support 확률

**장점**
- 정보가 여러 윈도우에 분산되어도 정확한 탐지 가능
- 최대 512 토큰 윈도우로 16k+ 토큰 처리
- GPT-3.5 기반 모델 대비 16k+ 컨텍스트에서 68% 성능 유지 (GPT-3.5는 완전 실패)

### 학습 데이터

**RAG QA 데이터셋 구성**
- 5개 산업 도메인: customer support, finance, biomedical, legal, general knowledge
- 75k 학습, 11k 검증, 11k 테스트 샘플
- GPT-3.5-turbo 및 Claude-3-Haiku로 응답 생성 (temperature=1)

**GPT-4-turbo 기반 자동 레이블링**
- 문장 단위로 컨텍스트와 응답 토큰화
- 각 응답 문장에 대해 어떤 컨텍스트 문장이 지지하는지 판단
- Chain-of-thought 프롬프팅으로 정확도 향상
- 응답 레벨 + 문장 레벨 이중 주석으로 노이즈 감소
- 충돌 발생 시 최대 3회 재주석

### 배포 최적화

**지연시간 최적화 (16k 토큰 기준)**
- Baseline: 3.27초
- TensorRT backend: 2.09초
- 효율적 전/후처리: 1.79초
- 512 토큰 최대 길이: 0.98초
- BLS (Business Logic Scripting): 0.92초
- **최종: 0.23초 (평균 쿼리)**

**배포 아키텍처**
- ONNX 모델을 NVIDIA Triton 서버에 배포
- TensorRT 백엔드 활용
- BLS로 GPU/CPU 자원 지능적 할당
- NVIDIA L4 GPU에서 최대 4 QPS 처리

### 성능 결과

**RAGTruth 벤치마크**
- Overall F1: 65.4% (GPT-4 기반 방법 다음으로 높음)
- 13B Llama-2 fine-tuned와 비교 시 크기 대비 우수한 효율

**도메인별 AUROC**
- Customer Support: 0.76
- Finance: 0.82
- Biomedical: 0.81
- Legal: 0.78
- General Knowledge: 0.83

**비용 효율**
- 월 1,750달러 (10 QPS 기준)
- GPT-3.5: 59,616달러 (97% 절감)
- RAGAS: 79,937달러
- Trulens: 173,016달러

---

## 내가 얻은 인사이트

- 소형 모델의 토큰 크기로 인해 긴 문맥에서의 할루시네이션을 잘 감지하지 못하는 현상을 개선하는 다양한 방법을 찾던 중 루나에 대해 알게됨
- 작게 쪼개서 각각 판단하고 보수적으로 집계하여 할루시네이션의 탐지율을 높인다는 컨셉임
- 다른 논문을 보아도 결국 기본 컨셉은 비슷한 듯 하여, 크기가 작은 모델에서 큰 컨텍스트를 처리할 때는 어쩔수 없이 쪼갠 후 병합하는 전략이 정석이라는 생각이 듬
