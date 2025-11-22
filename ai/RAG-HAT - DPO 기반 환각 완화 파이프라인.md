# RAG-HAT - DPO 기반 환각 완화 파이프라인

## 링크
https://aclanthology.org/2024.emnlp-industry.113/

## AI 요약

### 핵심 문제: 환각 탐지를 넘어 모델 자체를 개선하기

**기존 환각 탐지 프레임워크의 한계:**
```
ORION, Luna, LettuceDetect → 환각 "탐지"만 가능
- 탐지 후 어떻게 할까?
- LLM을 다시 프롬프팅? → 비용, 또 환각 가능
- 규칙 기반 수정? → 확장성 없음
```

**RAG-HAT의 근본적 접근:**
```
탐지 (Detection) → 수정 (Correction) → 학습 (Learning)

1. 환각 탐지 모델 훈련 ← Encoder 기반, ORION과 유사
2. GPT-4로 환각 수정 (hallucination description 활용)
3. 수정된 데이터로 DPO 훈련 ← 핵심! 여기가 RAG-HAT의 차별점
   → LLM이 애초에 환각을 덜 만들도록 학습
```

**패러다임 전환:**
```
기존: LLM 생성 → 탐지 → 버리거나 수정
RAG-HAT: 탐지 → 수정 → Preference 학습 → LLM 개선
```

**⚠️ 중요: 외부 API 사용 시 제약**
```
GPT-4, Claude 같은 외부 API 사용 시:
- Phase 1 (탐지): ✅ 가능 (독립적 Encoder 모델)
- Phase 2 (수정): ✅ 가능 (GPT-4 사용)
- Phase 3 (DPO): ❌ 불가능 (모델 가중치 접근 불가)

→ 외부 API에는 "탐지 + 수정"만 가능
→ DPO 학습(핵심 가치)은 자사 모델에만 적용 가능
→ ORION이 외부 API 환경에서 더 실용적
```

### 핵심 해결책: HAT (Hallucination Aware Tuning) 파이프라인

**3단계 파이프라인:**

```
Phase 1: Hallucination Detection Model Training
- 입력: (Query, Context, Response)
- 출력: Binary label + Detailed hallucination description
- 목적: "어디가" 환각인지, "왜" 환각인지 설명

Phase 2: GPT-4 Correction
- 입력: Hallucination description from Phase 1
- 출력: Corrected response (hallucination-free)
- 목적: 높은 품질의 "정답" 버전 생성

Phase 3: DPO (Direct Preference Optimization)
- 입력: (Query, Context, Original ❌, Corrected ✅)
- 출력: Fine-tuned LLM
- 목적: 환각 적은 응답을 선호하도록 학습
```

### 실제 구현: HAT 파이프라인

#### Phase 1: Hallucination Detection Model

**RAG-HAT의 환각 탐지는 ORION과 유사한 Encoder 기반 접근:**

```python
class HallucinationDetector:
    def __init__(self):
        # Encoder-based model (e.g., DeBERTA, BERT)
        # ORION처럼 NLI 또는 Classification 태스크
        self.model = EncoderModel(
            task="hallucination_detection",
            output_format={
                "label": "binary",  # 0: factual, 1: hallucination
                "description": "text"  # 상세 설명 ← ORION과의 차이점
            }
        )
    
    def detect(self, query, context, response):
        """환각 탐지 + 설명 생성"""
        
        # 입력 구성
        input_text = f"""
        Query: {query}
        Context: {context}
        Response: {response}
        """
        
        # 모델 예측
        result = self.model.predict(input_text)
        
        return {
            "has_hallucination": result["label"],
            "description": result["description"]
        }
```

**RAG-HAT 탐지 모델의 핵심:**

1. **Encoder 기반 (ORION과 동일)**
   ```python
   # DeBERTA, BERT 등 Transformer Encoder
   # 입력: [CLS] Query [SEP] Context [SEP] Response [SEP]
   # 출력: Binary classification (환각 O/X)
   ```

2. **Detailed Description 생성 (ORION과의 차이)**
   ```python
   # ORION: Binary label + Score
   {
     "label": 1,  # 환각
     "score": 0.15  # 낮은 점수
   }
   
   # RAG-HAT: Binary label + Description
   {
     "label": 1,  # 환각
     "description": "Response states 'London' but context says 'Paris'"
   }
   # ↑ 이 description이 GPT-4 수정의 핵심 입력
   ```

3. **훈련 방식**
   ```python
   # RAGTruth 같은 벤치마크로 Supervised Learning
   # Input: (Query, Context, Response)
   # Label: 0 (factual) or 1 (hallucination)
   # Description: Human annotation or GPT-4 생성
   ```

**훈련 데이터 형식:**
```json
{
  "query": "What is the capital of France?",
  "context": "France is a country in Europe. Its capital is Paris.",
  "response": "The capital of France is London.",
  "label": 1,
  "description": "The response states 'London' as the capital, which contradicts the context stating 'Paris' is the capital."
}
```

**ORION vs RAG-HAT Detection 비교:**

| | ORION | RAG-HAT Phase 1 |
|---|-------|-----------------|
| **모델 타입** | Encoder (NLI) | Encoder (Classification) |
| **입력** | (Claim, Context) | (Query, Context, Response) |
| **출력** | Score (0~1) | Label + Description |
| **훈련** | Zero-shot 가능 | Supervised 필요 |
| **목적** | 최종 탐지 | DPO 데이터 생성용 |
| **외부 API** | ✅ 독립 사용 가능 | ✅ 독립 사용 가능 |

**핵심 차이:**
```python
# ORION: 탐지가 최종 목적
detector = ORION()
score = detector.evaluate(response, context)
if score < 0.5:
    print("환각 탐지! 응답 거부")

# RAG-HAT: 탐지는 DPO를 위한 중간 단계
detector = RAGHATDetector()
result = detector.detect(query, context, response)
if result["has_hallucination"]:
    # Description을 GPT-4로 전달 → 수정 → DPO 학습
    corrected = gpt4.correct(response, result["description"])
    dpo_train(original=response, corrected=corrected)
```

**Detection Model의 핵심:**
- Binary label만으로는 부족
- **Detailed description**이 GPT-4 수정의 핵심 입력
- "무엇이" 틀렸는지 명확히 명시

#### Phase 2: GPT-4 기반 Correction

```python
class GPT4Corrector:
    def __init__(self):
        self.gpt4 = OpenAI(model="gpt-4-turbo")
    
    def correct(self, query, context, response, hallucination_desc):
        """환각 설명을 바탕으로 응답 수정"""
        
        prompt = f"""
You are a factual accuracy expert.

**Query**: {query}

**Context**: {context}

**Original Response**: {response}

**Detected Hallucination**: {hallucination_desc}

**Task**: Correct the response to be factually consistent with the context.
- Fix only the hallucinated parts
- Keep other parts unchanged if they are correct
- Maintain the original tone and style

**Corrected Response**:
"""
        
        corrected = self.gpt4.generate(prompt)
        return corrected.strip()
```

**수정 예시:**
```python
# 입력
query = "What is the capital of France?"
context = "France is a country in Europe. Its capital is Paris."
response = "The capital of France is London."
hallucination_desc = "Response states 'London' as capital, contradicts context stating 'Paris'."

# GPT-4 수정
corrected = corrector.correct(query, context, response, hallucination_desc)
# "The capital of France is Paris."
```

**왜 GPT-4를 사용하는가?**
1. **High-quality correction**: 작은 모델보다 정확한 수정
2. **Hallucination description 활용**: 정확한 수정 포인트 제공
3. **One-time cost**: 훈련 데이터 생성에만 사용, 추론엔 불필요

#### Phase 3: DPO Training

```python
class DPOTrainer:
    def __init__(self, base_model):
        self.model = base_model
        self.preference_dataset = []
    
    def create_preference_pair(self, query, context, original, corrected):
        """Preference 쌍 생성"""
        return {
            "prompt": f"Query: {query}\nContext: {context}\n",
            "chosen": corrected,  # ✅ 선호하는 응답
            "rejected": original  # ❌ 거부하는 응답
        }
    
    def train(self, preference_dataset):
        """DPO 훈련"""
        
        for item in preference_dataset:
            # DPO loss 계산
            # L = -log σ(β log π_θ(chosen|prompt) / π_ref(chosen|prompt) 
            #            - β log π_θ(rejected|prompt) / π_ref(rejected|prompt))
            
            prompt = item["prompt"]
            chosen = item["chosen"]
            rejected = item["rejected"]
            
            # 모델이 chosen을 더 선호하도록 학습
            loss = self.compute_dpo_loss(prompt, chosen, rejected)
            loss.backward()
        
        return self.model
```

**DPO의 핵심 아이디어:**
```python
# 기존 RLHF
1. Reward model 훈련 (복잡)
2. PPO로 policy 학습 (불안정)

# DPO (Direct Preference Optimization)
1. Preference 쌍만 있으면 됨
2. 직접 policy를 학습 (간단, 안정)

# Loss function
chosen_better = log π(chosen|prompt) - log π(rejected|prompt)
# chosen의 확률이 rejected보다 높아지도록
```

**전체 파이프라인 구현:**

```python
class RAGHAT:
    def __init__(self, base_llm):
        self.detector = HallucinationDetector()
        self.corrector = GPT4Corrector()
        self.trainer = DPOTrainer(base_llm)
    
    def build_preference_dataset(self, rag_outputs):
        """RAG 출력들로부터 preference dataset 생성"""
        
        preference_pairs = []
        
        for item in rag_outputs:
            query = item["query"]
            context = item["context"]
            response = item["response"]
            
            # Phase 1: Detect
            detection = self.detector.detect(query, context, response)
            
            if detection["has_hallucination"]:
                # Phase 2: Correct
                corrected = self.corrector.correct(
                    query, context, response,
                    detection["description"]
                )
                
                # Phase 3: Create preference pair
                pair = self.trainer.create_preference_pair(
                    query, context,
                    original=response,
                    corrected=corrected
                )
                preference_pairs.append(pair)
            
            else:
                # 환각 없으면 그대로 사용
                # (선택적으로 positive example로 활용 가능)
                pass
        
        return preference_pairs
    
    def train(self, rag_outputs):
        """전체 HAT 파이프라인 실행"""
        
        # 1. Preference dataset 생성
        print("Building preference dataset...")
        preference_dataset = self.build_preference_dataset(rag_outputs)
        
        # 2. DPO 훈련
        print(f"Training with {len(preference_dataset)} preference pairs...")
        tuned_model = self.trainer.train(preference_dataset)
        
        return tuned_model
```

### 실전 시나리오

#### 시나리오: Customer Support RAG 개선

```python
# 1. 기존 RAG 시스템의 출력 수집
rag_outputs = [
    {
        "query": "반품 정책이 어떻게 되나요?",
        "context": "30일 이내 미개봉 상품만 반품 가능합니다.",
        "response": "60일 이내 반품 가능하며 개봉 여부 무관합니다."
        # ↑ 환각!
    },
    {
        "query": "배송비는 얼마인가요?",
        "context": "5만원 이상 구매 시 무료배송입니다.",
        "response": "3만원 이상 구매 시 무료배송입니다."
        # ↑ 환각!
    },
    # ... 수백~수천 개
]

# 2. RAG-HAT 파이프라인 실행
raghat = RAGHAT(base_llm=Llama2_7B)
tuned_model = raghat.train(rag_outputs)

# 3. 개선된 모델 평가
new_outputs = tuned_model.generate(
    query="반품 정책이 어떻게 되나요?",
    context="30일 이내 미개봉 상품만 반품 가능합니다."
)
# "30일 이내 미개봉 상품만 반품 가능합니다."
# ✅ 정확!
```

**처리 흐름 상세:**
```
Input: "60일 이내 반품 가능..." (환각)

↓ Phase 1: Detection
Label: 1 (hallucination)
Description: "Response states '60일' but context says '30일'. 
              Response states '개봉 여부 무관' but context requires '미개봉'."

↓ Phase 2: GPT-4 Correction
Corrected: "30일 이내 미개봉 상품만 반품 가능합니다."

↓ Phase 3: DPO Training
Preference: {
  chosen: "30일 이내 미개봉 상품만 반품 가능합니다.",
  rejected: "60일 이내 반품 가능하며 개봉 여부 무관합니다."
}

↓ Result
Model learns: "반품 정책" → "30일" ✅ (not "60일" ❌)
              "미개봉" ✅ (not "개봉 여부 무관" ❌)
```

### 벤치마크 결과: RAGTruth

**F1 Score 비교:**

| 방법 | 모델 크기 | 훈련 | F1 | 비고 |
|-----|----------|-----|-----|-----|
| **RAG-HAT** | Large | ✅ RAGTruth | **0.84** | 1위 |
| ORION | Small | ❌ Zero-shot | 0.83 | 2위 |
| LettuceDetect | Medium | ✅ RAGTruth | 0.79 | |
| Finetuned Llama-2-13B | 13B | ✅ RAGTruth | 0.79 | |
| Luna | Medium | ❌ OOD | 0.65 | |
| GPT-4-turbo (Prompt) | Very Large | ❌ OOD | 0.63 | |

**RAG-HAT이 1위인 이유:**

1. **학습 기반 접근**
   - ORION: Zero-shot (학습 없음)
   - RAG-HAT: RAGTruth로 학습 → 0.01 더 높음

2. **Large 모델 사용**
   - ORION: Small encoder (~500M)
   - RAG-HAT: Large model → 더 정확한 탐지

3. **Description + Correction**
   - 단순 binary label 넘어 상세 설명
   - GPT-4로 고품질 수정

### 핵심 기술 분석

#### 1. Hallucination Description의 중요성

```python
# Bad: Binary label만
{
  "label": 1  # 환각 있음
}
# → GPT-4가 뭘 고쳐야 할지 모름

# Good: Detailed description
{
  "label": 1,
  "description": "Response states 'London' as capital, but context clearly states 'Paris' is the capital of France."
}
# → GPT-4가 정확히 London → Paris 수정
```

**Description이 만드는 차이:**
```
Without description:
GPT-4 prompt: "Fix the hallucination in this response"
→ GPT-4가 컨텍스트 전체 재해석 필요
→ 비용 높음, 불확실성 높음

With description:
GPT-4 prompt: "Response says London but should be Paris per context"
→ GPT-4가 정확한 포인트만 수정
→ 효율적, 정확함
```

#### 2. DPO vs RLHF

**RLHF (Reinforcement Learning from Human Feedback):**
```python
# 복잡한 2-step 프로세스
1. Reward model 훈련
   - Preference 데이터로 reward model 학습
   - (chosen, rejected) → scalar reward

2. PPO로 policy 학습
   - Reward model 사용해 RL 수행
   - 불안정, 하이퍼파라미터 민감
```

**DPO (Direct Preference Optimization):**
```python
# 단순한 1-step 프로세스
Preference 데이터로 바로 policy 학습
- Reward model 불필요
- 안정적, 빠름
- 수학적으로 RLHF와 동등
```

**DPO Loss 수식:**
```
L_DPO = -E[(x,y_w,y_l)~D] [log σ(β log π_θ(y_w|x) / π_ref(y_w|x)
                                  - β log π_θ(y_l|x) / π_ref(y_l|x))]

where:
- y_w: chosen (winner) response
- y_l: rejected (loser) response
- π_θ: policy being trained
- π_ref: reference policy (base model)
- β: temperature parameter
```

**실제 구현:**
```python
def dpo_loss(model, ref_model, prompt, chosen, rejected, beta=0.1):
    """DPO loss 계산"""
    
    # Log probabilities
    log_p_chosen = model.log_prob(chosen, prompt)
    log_p_rejected = model.log_prob(rejected, prompt)
    
    log_ref_chosen = ref_model.log_prob(chosen, prompt)
    log_ref_rejected = ref_model.log_prob(rejected, prompt)
    
    # Ratios
    ratio_chosen = log_p_chosen - log_ref_chosen
    ratio_rejected = log_p_rejected - log_ref_rejected
    
    # DPO loss
    loss = -torch.log(torch.sigmoid(beta * (ratio_chosen - ratio_rejected)))
    
    return loss.mean()
```

#### 3. Hallucination-free vs Hallucinated Pairs

```python
# Preference pair 구성
{
  "prompt": "Query: ... Context: ...",
  "chosen": "Corrected response (GPT-4)",  # Hallucination-free
  "rejected": "Original response (LLM)"    # Hallucinated
}

# DPO가 학습하는 것:
P(chosen | prompt) ↑  # 환각 없는 응답 확률 증가
P(rejected | prompt) ↓  # 환각 있는 응답 확률 감소
```

**결과:**
- LLM이 애초에 환각을 덜 생성
- Post-processing 탐지 의존도 감소
- 프로덕션에서 더 안전

### RAG-HAT vs ORION 비교

| | RAG-HAT | ORION |
|---|---------|-------|
| **접근법** | Learning (DPO) | Detection (NLI) |
| **목표** | LLM 개선 | 환각 탐지 |
| **훈련** | ✅ RAGTruth | ❌ Zero-shot |
| **F1** | 0.84 | 0.83 |
| **모델 크기** | Large | Small (~500M) |
| **프로덕션** | LLM 재훈련 필요 | 즉시 적용 가능 |
| **외부 API** | ❌ DPO 불가 | ✅ 탐지만 가능 |
| **장점** | 근본적 해결 | 경량, 빠름, 독립적 |
| **단점** | 비용, 시간, 자사 모델 필요 | 탐지만 가능 |

**언제 RAG-HAT을 쓸까?**
```
Use RAG-HAT when:
✅ 자사 LLM을 보유/파인튜닝 가능 (Llama, Mistral 등)
✅ 높은 정확도 최우선
✅ 재훈련 비용 감당 가능
✅ Long-term 솔루션 원함
❌ GPT-4, Claude 같은 외부 API만 쓰면 DPO 불가!

Use ORION when:
✅ 외부 LLM API 사용 (GPT-4, Claude 등) ← 핵심!
✅ 빠른 배포 필요
✅ 경량 솔루션 원함
✅ Zero-shot 성능으로 충분
✅ 모델 재훈련 불가능한 환경
```

**외부 API 환경에서의 현실:**
```python
# GPT-4 API 사용 시
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)

# RAG-HAT Phase 1 (탐지): ✅ 가능
detector = RAGHATDetector()
result = detector.detect(query, context, response)

# RAG-HAT Phase 2 (수정): ✅ 가능
if result["has_hallucination"]:
    corrected = gpt4.correct(response, result["description"])

# RAG-HAT Phase 3 (DPO): ❌ 불가능!
# GPT-4 모델 가중치에 접근 불가
# Fine-tuning API 있지만 DPO 학습 불가
# → RAG-HAT의 핵심 가치(0.84 F1) 사용 못 함

# 반면 ORION: ✅ 탐지만으로 완결
orion = ORION()
score = orion.evaluate(response, context)
if score < 0.5:
    # 환각 탐지 → 사용자에게 경고 또는 응답 차단
    return "컨텍스트 기반 응답 불가"
```

### 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│                    RAG Outputs                          │
│         [(Query, Context, Response), ...]               │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────▼─────────────┐
        │ Phase 1: Detection Model  │
        │ (Encoder-based)            │
        │                            │
        │ Input: (Q, C, R)           │
        │ Output: Label + Description│
        └─────────────┬───────────────┘
                      │
        ┌─────────────▼─────────────┐
        │ Has Hallucination?         │
        └─────┬──────────────────┬───┘
              │ Yes              │ No
              │                  │
    ┌─────────▼─────────┐        │ Skip
    │ Phase 2: GPT-4    │        │ (or use as positive)
    │ Correction        │        │
    │                   │        │
    │ Input: Desc       │        │
    │ Output: Corrected │        │
    └─────────┬─────────┘        │
              │                  │
    ┌─────────▼──────────────────▼────┐
    │ Phase 3: Preference Dataset     │
    │                                  │
    │ {prompt, chosen, rejected}      │
    └─────────┬────────────────────────┘
              │
    ┌─────────▼─────────┐
    │ DPO Training       │
    │                    │
    │ Loss: -log σ(...)  │
    └─────────┬──────────┘
              │
    ┌─────────▼─────────┐
    │ Fine-tuned LLM     │
    │ (Hallucination ↓)  │
    └────────────────────┘
```

### 구현 시 고려사항

#### 1. Detection Model 품질이 핵심

```python
# Bad detector → Bad preference dataset
If detector FP rate high:
→ Correct responses 잘못 수정
→ DPO가 좋은 응답 거부 학습 ❌

If detector FN rate high:
→ 환각 놓침
→ DPO 학습 데이터 부족 ❌

# Solution: High-quality detector 필수
- 충분한 훈련 데이터
- RAGTruth 같은 벤치마크로 검증
- Threshold tuning (precision vs recall)
```

#### 2. GPT-4 비용 관리

```python
# 모든 응답을 GPT-4로 수정하면 비싼
# Strategy 1: Batch processing
corrections = gpt4.batch_generate([
    (response1, desc1),
    (response2, desc2),
    # ...
], batch_size=100)

# Strategy 2: Confidence-based filtering
if detection["confidence"] > 0.9:  # 확실한 환각만
    corrected = gpt4.correct(...)

# Strategy 3: Self-correction first
try:
    corrected = smaller_model.correct(...)  # 7B model
    if still_hallucinated(corrected):
        corrected = gpt4.correct(...)  # Fallback
except:
    corrected = gpt4.correct(...)
```

#### 3. DPO 하이퍼파라미터

```python
# β (beta): 중요!
β too small (< 0.01):
→ Policy가 reference에서 거의 안 벗어남
→ 학습 효과 미미

β too large (> 1.0):
→ Policy가 reference에서 너무 멀어짐
→ 다른 능력 손실 (language fluency 등)

# Recommended: β = 0.1 ~ 0.5
trainer = DPOTrainer(beta=0.1)

# Learning rate
lr too high:
→ 불안정, catastrophic forgetting

lr too low:
→ 학습 느림

# Recommended: 1e-6 ~ 1e-5
optimizer = AdamW(lr=5e-6)
```

#### 4. Preference Dataset 크기

```python
# 얼마나 많은 preference pairs 필요?
Minimum: 1,000 pairs
- 작은 LLM (7B)
- 특정 도메인

Recommended: 10,000+ pairs
- 중간 LLM (13B)
- 일반 목적

Optimal: 100,000+ pairs
- 큰 LLM (70B+)
- 높은 품질 요구
```

### 실전 배포 전략

#### Strategy 1: 온라인 학습

```python
class OnlineRAGHAT:
    def __init__(self):
        self.detector = HallucinationDetector()
        self.buffer = []
        self.update_threshold = 1000  # 1000개 모이면 재훈련
    
    def serve_and_collect(self, query, context):
        """서빙하면서 데이터 수집"""
        
        # 1. 현재 모델로 생성
        response = self.model.generate(query, context)
        
        # 2. 실시간 탐지
        detection = self.detector.detect(query, context, response)
        
        # 3. 버퍼에 저장
        if detection["has_hallucination"]:
            self.buffer.append({
                "query": query,
                "context": context,
                "response": response,
                "description": detection["description"]
            })
        
        # 4. 임계치 도달 시 재훈련
        if len(self.buffer) >= self.update_threshold:
            self.retrain()
        
        return response
    
    def retrain(self):
        """주기적 재훈련"""
        print(f"Retraining with {len(self.buffer)} new samples...")
        
        # GPT-4로 일괄 수정
        corrected = self.batch_correct(self.buffer)
        
        # DPO 훈련
        self.model = self.dpo_train(self.buffer, corrected)
        
        # 버퍼 초기화
        self.buffer = []
```

#### Strategy 2: 도메인별 전문화

```python
# Customer Support
customer_raghat = RAGHAT(
    base_model=Llama2_7B,
    domain="customer_support"
)
customer_model = customer_raghat.train(customer_support_data)

# Medical QA
medical_raghat = RAGHAT(
    base_model=Llama2_7B,
    domain="medical"
)
medical_model = medical_raghat.train(medical_qa_data)

# Legal Documents
legal_raghat = RAGHAT(
    base_model=Llama2_7B,
    domain="legal"
)
legal_model = legal_raghat.train(legal_documents_data)
```

#### Strategy 3: 하이브리드 (RAG-HAT + ORION)

```python
class HybridSystem:
    def __init__(self):
        self.raghat_model = RAGHATModel()  # DPO로 튜닝된 LLM
        self.orion_detector = ORIONDetector()  # 실시간 탐지
    
    def generate_safe(self, query, context):
        """생성 + 실시간 검증"""
        
        # 1. RAG-HAT 모델로 생성 (이미 환각 적음)
        response = self.raghat_model.generate(query, context)
        
        # 2. ORION으로 이중 검증
        score = self.orion_detector.evaluate(response, context)
        
        # 3. 추가 안전 장치
        if score["score"] < 0.5:  # 여전히 환각 발견
            # Fallback: Conservative response
            response = "Based on the provided context, I cannot confidently answer this question."
        
        return response
```

**하이브리드의 장점:**
```
RAG-HAT: 환각률 80% → 20% 감소
ORION: 남은 20% 중 90% 탐지
→ 최종 환각률: 2% (80% → 20% → 2%)

비용:
- RAG-HAT: One-time training cost
- ORION: Low inference cost (small model)
- 합리적 trade-off
```

## 내가 얻은 인사이트

### 1. Detection → Correction → Learning 순환
환각 탐지만으로는 한계. RAG-HAT은 탐지→수정→학습 순환으로 **근본적 해결**을 시도. 단, **자사 모델 필수**.

### 2. 환각 탐지 원리는 ORION과 유사
RAG-HAT Phase 1도 Encoder 기반 NLI/Classification. 탐지 성능 자체는 ORION과 비슷할 것. 차이는 **Description 생성**과 **DPO 활용**.

**환각 탐지 원리 자체는 비슷**. 차이는 훈련 여부와 모델 크기. RAG-HAT의 진짜 가치는 탐지가 아니라 **DPO 학습**.

### 3. Hallucination Description의 가치
Binary label (환각 O/X)이 아닌 **상세 설명**이 GPT-4 수정의 핵심. "무엇이 틀렸는지" 명시하면 수정 품질 급상승. 하지만 이것도 **외부 API 환경에선 DPO 못 쓰면 무용지물**.
