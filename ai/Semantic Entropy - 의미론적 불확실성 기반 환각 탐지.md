# Semantic Entropy - 의미론적 불확실성 기반 환각 탐지

## 링크
https://www.nature.com/articles/s41586-024-07421-0

## AI 요약
**Semantic Entropy (SE)**는 LLM의 토큰 확률이 아닌 **의미론적 불확실성(semantic uncertainty)**을 측정하여 환각을 탐지하는 방법입니다. "Paris", "It's Paris", "The capital is Paris"처럼 표현은 다르지만 같은 의미를 가진 생성들을 클러스터링하여 불확실성을 계산합니다. **Nature 2024 논문 (687회 인용)**으로 발표된 이후, **Semantic Entropy Probes (SEPs)**를 통해 단일 생성으로 SE를 근사하여 **10배 비용 절감**을 달성했습니다.

**핵심**: 토큰 확률 대신 의미 공간의 엔트로피를 사용하여 모델이 "무엇을 모르는지" 파악합니다.

---

## 1. 핵심 문제: 토큰 확률의 한계

### 1.1 기존 방법의 문제점

```python
# ❌ 기존: 토큰 확률 기반 불확실성 (잘못된 접근)
prompt = "What is the capital of France?"

# 모델이 알고 있는 경우
generation1 = "Paris"              # P=0.95
generation2 = "It's Paris"         # P=0.02 (낮은 확률!)
generation3 = "The capital is Paris"  # P=0.01 (더 낮음!)

# 토큰 확률로 보면 불확실성이 높아 보임
# 하지만 의미는 모두 동일 → 확실하게 알고 있음

# 모델이 모르는 경우
generation1 = "Naples"  # P=0.3
generation2 = "Rome"    # P=0.3
generation3 = "Berlin"  # P=0.2

# 의미가 다름 → 진짜 불확실함 (환각)
```

### 1.2 Semantic Entropy의 접근

**핵심 아이디어**: 다양한 표현을 하나의 의미로 묶어서 불확실성 계산

- **Lexical/Syntactic Uncertainty**: 어떻게 표현할지 (무시해야 함)
- **Semantic Uncertainty**: 무엇을 말할지 (측정해야 함)

---

## 2. Semantic Entropy 작동 원리

### 2.1 3단계 프로세스

```python
# Step 1: 다중 생성 (N=10, temperature=1.0)
samples = model.generate(prompt, n=10, temperature=1.0)
# ["Paris", "It's Paris", "The capital is Paris", 
#  "Paris is the answer", "Paris.", ...]

# Step 2: 의미론적 클러스터링 (Bidirectional Entailment)
clusters = semantic_clustering(samples, nli_model="DeBERTa-Large")

def semantic_clustering(samples, nli_model):
    """양방향 함의(bidirectional entailment)로 클러스터링"""
    clusters = []
    
    for sample_a in samples:
        found_cluster = False
        
        for cluster in clusters:
            sample_b = cluster[0]  # 대표 샘플
            
            # 양방향 함의 체크
            if (nli_model.entails(sample_a, sample_b) and 
                nli_model.entails(sample_b, sample_a)):
                cluster.append(sample_a)
                found_cluster = True
                break
        
        if not found_cluster:
            clusters.append([sample_a])  # 새 클러스터 생성
    
    return clusters

# 결과: clusters = [
#   ["Paris", "It's Paris", "The capital is Paris", ...],  # C1: 10개
# ]

# Step 3: Semantic Entropy 계산
def compute_semantic_entropy(clusters):
    """클러스터 확률 분포의 엔트로피"""
    K = len(clusters)  # 클러스터 개수
    
    # 각 클러스터의 확률 = 샘플 비율
    cluster_probs = [len(c) / sum(len(c) for c in clusters) 
                     for c in clusters]
    
    # 엔트로피 계산
    H_SE = -sum(p * log(p) for p in cluster_probs if p > 0)
    
    return H_SE

# 확실한 경우: H_SE ≈ 0 (1개 클러스터에 모든 샘플)
# 불확실한 경우: H_SE > threshold (여러 클러스터에 분산)
```

### 2.2 수학적 정의

**일반 엔트로피 (토큰 레벨)**:
$$H[s|x] = \mathbb{E}_{p(s|x)}[-\log p(s|x)]$$

**Semantic Entropy (의미 레벨)**:
$$H[C|x] = \mathbb{E}_{p(C|x)}[-\log p(C|x)]$$

**클러스터 확률 (Monte Carlo 근사)**:
$$p(C_k|x) = \frac{1}{N} \sum_{i=1}^N \mathbb{1}[s_i \in C_k]$$

**Discrete SE (실제 구현)**:
$$H_{SE}(x) = -\sum_{k=1}^K p(C_k|x) \log p(C_k|x)$$

---

## 3. Semantic Entropy Probes (SEPs): 10배 고속화

### 3.1 문제: SE의 높은 계산 비용

```python
# 원본 Semantic Entropy
# - 10번 생성 필요 → 10x 비용
# - NLI 모델로 클러스터링 → 추가 비용
# - 실용성 문제

# 해결책: Semantic Entropy Probes (SEPs)
# - 단 1번 생성으로 SE 예측
# - Hidden state에서 Linear probe로 SE 추출
```

### 3.2 SEP 구현

```python
# 1. 훈련 데이터 생성
training_data = []

for query in unlabeled_dataset:
    # Greedy 생성 (훈련용)
    hidden_state = model.generate(query, return_hidden=True, greedy=True)
    
    # SE 계산 (라벨 생성)
    samples = model.generate(query, n=10, temperature=1.0)
    clusters = semantic_clustering(samples)
    H_SE = compute_semantic_entropy(clusters)
    
    training_data.append((hidden_state, H_SE))

# 2. 이진화 (High/Low SE)
def binarize_se(se_scores):
    """최적 분할 임계값 찾기"""
    best_threshold = optimize_split(se_scores)  # MSE 최소화
    return [1 if se > best_threshold else 0 for se in se_scores]

binary_labels = binarize_se([H_SE for _, H_SE in training_data])

# 3. Linear Probe 훈련
from sklearn.linear_model import LogisticRegression

# Hidden state 추출 (2가지 위치)
# - SLT (Second Last Token): 생성 후 마지막 토큰
# - TBG (Token Before Generation): 생성 전 마지막 입력 토큰

probe = LogisticRegression()
X = [h for h, _ in training_data]  # shape: (N, hidden_dim)
y = binary_labels

probe.fit(X, y)

# 4. 추론 (단일 생성)
def detect_hallucination_cheap(query):
    """1번 생성으로 환각 탐지"""
    hidden_state = model.generate(query, return_hidden=True, greedy=True)
    prob_high_se = probe.predict_proba(hidden_state)[0, 1]
    
    return prob_high_se > 0.5  # Hallucination if high SE
```

### 3.3 SEP vs 원본 SE 비교

| 특성 | Semantic Entropy (원본) | Semantic Entropy Probes (SEPs) |
|------|------------------------|-------------------------------|
| **생성 횟수** | 10회 | 1회 |
| **계산 비용** | High (10x) | Low (1x) |
| **추가 모델** | NLI (DeBERTa) | Linear probe만 |
| **훈련 필요** | ❌ (Zero-shot) | ✅ (Probe 학습) |
| **AUROC** | ~0.9 (best) | ~0.8 (good) |
| **일반화** | 좋음 | 더 좋음 (accuracy probe 대비) |

---

## 4. 성능 벤치마크

### 4.1 Short-form Generation (Llama-2-7B)

| Dataset | SE (AUROC) | SEP (AUROC) | Accuracy Probe | Naive Entropy |
|---------|------------|-------------|----------------|---------------|
| TriviaQA | 0.92 | 0.85 | 0.82 | 0.78 |
| SQuAD | 0.90 | 0.83 | 0.80 | 0.75 |
| BioASQ | 0.89 | 0.87 | 0.81 | 0.73 |
| NQ Open | 0.88 | 0.84 | 0.79 | 0.74 |

**Out-of-Distribution 일반화** (Leave-one-out):
```
SEP vs Accuracy Probe (OOD)
- TriviaQA: SEP +0.12 AUROC
- BioASQ: SEP +0.18 AUROC (큰 차이)
- SQuAD: SEP +0.08 AUROC
```

### 4.2 Long-form Generation (Llama-2-70B, Llama-3-70B)

- **SEP AUROC**: 0.75-0.85 (여러 레이어/위치)
- **중간 레이어가 최고 성능**: 마지막 레이어는 다음 토큰 예측에 집중
- **TBG (생성 전) 가능**: 단일 forward pass로 불확실성 예측

---

## 5. 핵심 통찰

### 5.1 왜 SEP가 Accuracy Probe보다 나은가?

```python
# Accuracy Probe: 외부 정답 레이블 필요
accuracy_probe_data = [
    (hidden_state, is_correct),  # is_correct는 외부 지식
    # → Task-specific, 노이즈 많음
]

# Semantic Entropy Probe: 모델 내부 상태만 사용
sep_data = [
    (hidden_state, H_SE),  # H_SE는 모델 자체 불확실성
    # → Model-internal, 일반화 잘됨
]
```

**실험 결과**:
- **In-distribution**: Accuracy Probe ≈ SEP (비슷)
- **Out-of-distribution**: SEP >> Accuracy Probe (훨씬 좋음)

### 5.2 Hidden State가 SE를 인코딩한다

**증거 1: Counterfactual Experiment**
```python
# TriviaQA without context
accuracy = 26%
H_SE_true = 1.84
p(high SE) from SEP = 0.9  # 높은 불확실성 예측

# TriviaQA with context (정답 힌트 추가)
accuracy = 78%
H_SE_true = 0.50
p(high SE) from SEP = 0.3  # 낮은 불확실성 예측

# → SEP가 컨텍스트 변화에 반응 (훈련 안 받았는데!)
```

**증거 2: Layer-wise Analysis**
- **초기 레이어**: 낮은 AUROC (0.5-0.6)
- **중간/후기 레이어**: 높은 AUROC (0.7-0.95)
- **SE 정보가 점진적으로 인코딩됨**

---

## 6. 실전 구현 가이드

### 6.1 Complete Pipeline

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from sklearn.linear_model import LogisticRegression
import numpy as np

class SemanticEntropyDetector:
    def __init__(self, model_name="meta-llama/Llama-2-7b-hf"):
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.nli_model = load_nli_model("microsoft/deberta-large-mnli")
        
    def compute_se_original(self, prompt, n_samples=10):
        """원본 Semantic Entropy (10배 비용)"""
        # 1. 다중 생성
        samples = []
        for _ in range(n_samples):
            output = self.model.generate(
                self.tokenizer(prompt, return_tensors="pt").input_ids,
                max_new_tokens=50,
                do_sample=True,
                temperature=1.0
            )
            samples.append(self.tokenizer.decode(output[0]))
        
        # 2. 의미론적 클러스터링
        clusters = self._cluster_by_entailment(samples)
        
        # 3. SE 계산
        K = len(clusters)
        N = len(samples)
        cluster_probs = [len(c) / N for c in clusters]
        H_SE = -sum(p * np.log(p) for p in cluster_probs if p > 0)
        
        return H_SE
    
    def _cluster_by_entailment(self, samples):
        """양방향 함의로 클러스터링"""
        clusters = []
        
        for sample in samples:
            matched = False
            
            for cluster in clusters:
                representative = cluster[0]
                
                # Bidirectional entailment check
                if (self._entails(sample, representative) and
                    self._entails(representative, sample)):
                    cluster.append(sample)
                    matched = True
                    break
            
            if not matched:
                clusters.append([sample])
        
        return clusters
    
    def _entails(self, text1, text2):
        """NLI로 함의 관계 체크"""
        inputs = self.tokenizer(
            text1, text2, 
            return_tensors="pt", 
            truncation=True
        )
        outputs = self.nli_model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        
        # ENTAILMENT 확률 > 0.5
        return probs[0, 2] > 0.5  # [contradiction, neutral, entailment]

    def train_sep(self, dataset, layer=-5, position="slt"):
        """SEP 훈련 (한 번만 실행)"""
        X, y = [], []
        
        for query in dataset:
            # Hidden state 추출
            hidden = self._extract_hidden(query, layer, position)
            X.append(hidden)
            
            # SE 라벨 계산
            se = self.compute_se_original(query)
            y.append(se)
        
        # 이진화
        y_binary = self._binarize(y)
        
        # Linear probe 훈련
        self.probe = LogisticRegression()
        self.probe.fit(X, y_binary)
    
    def detect_with_sep(self, prompt):
        """SEP로 빠른 탐지 (1배 비용)"""
        hidden = self._extract_hidden(prompt, layer=-5, position="slt")
        prob_high_se = self.probe.predict_proba([hidden])[0, 1]
        
        return {
            "is_hallucination": prob_high_se > 0.5,
            "confidence": prob_high_se
        }
    
    def _extract_hidden(self, prompt, layer, position):
        """Hidden state 추출"""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model(
                **inputs, 
                output_hidden_states=True,
                return_dict=True
            )
        
        hidden_states = outputs.hidden_states[layer]
        
        if position == "slt":  # Second Last Token
            return hidden_states[0, -2, :].cpu().numpy()
        else:  # TBG (Token Before Generation)
            return hidden_states[0, -1, :].cpu().numpy()
    
    def _binarize(self, se_scores):
        """최적 분할 임계값으로 이진화"""
        # MSE 최소화 (regression tree splitting)
        best_threshold = None
        best_mse = float('inf')
        
        for threshold in np.percentile(se_scores, range(10, 91, 10)):
            low = [s for s in se_scores if s < threshold]
            high = [s for s in se_scores if s >= threshold]
            
            if len(low) > 0 and len(high) > 0:
                mse = (np.var(low) * len(low) + 
                       np.var(high) * len(high)) / len(se_scores)
                
                if mse < best_mse:
                    best_mse = mse
                    best_threshold = threshold
        
        return [1 if s > best_threshold else 0 for s in se_scores]

# 사용 예시
detector = SemanticEntropyDetector()

# 1회성 훈련 (unlabeled data 사용 가능)
detector.train_sep(unlabeled_queries)

# 빠른 탐지
result = detector.detect_with_sep("What is the capital of France?")
print(result)  # {"is_hallucination": False, "confidence": 0.12}
```

### 6.2 레이어/위치 선택 가이드

| 모델 | 레이어 (SEP) | 레이어 (Accuracy Probe) | Hidden Dim |
|------|-------------|------------------------|------------|
| Llama-2-7B | 28-32 (후반) | 18-22 (중반) | 4096 |
| Llama-2-70B | 76-80 (후반) | 75-79 (후반) | 8192 |
| Mistral-7B | 28-32 (후반) | 12-16 (초중반) | 4096 |
| Llama-3-70B | 76-80 (후반) | 31-35 (중반) | 8192 |

**권장사항**:
- **Short-form**: SLT (Second Last Token) 사용
- **Long-form**: 중간 레이어 (마지막 레이어는 next token에 집중)
- **Zero-generation**: TBG (Token Before Generation) 가능

---

## 7. 한계 및 고려사항

### 7.1 계산 비용 트레이드오프

| 방법 | 생성 횟수 | 정확도 (AUROC) | 적용 시나리오 |
|------|----------|---------------|--------------|
| **Semantic Entropy** | 10회 | 0.90-0.92 | 고위험 도메인 (의료, 법률) |
| **SEP** | 1회 | 0.80-0.85 | 일반 애플리케이션 |
| **p(True)** | 10회 | 0.88-0.90 | Few-shot 가능 시 |
| **Log Likelihood** | 1회 | 0.70-0.75 | Baseline |

### 7.2 제약사항

1. **NLI 모델 필요** (원본 SE)
   - DeBERTa-Large 추가 실행
   - GPT-3.5로 대체 가능 (long-form)

2. **훈련 데이터 필요** (SEPs)
   - 1,000-2,000 샘플 권장
   - Unlabeled data 사용 가능 (장점)

3. **Black-box API 제약**
   - Hidden state 필요 → SEP 불가
   - 원본 SE는 가능 (샘플링만 필요)

4. **Domain Shift**
   - Yes/No 질문에서 높은 성능 (BioASQ)
   - Open-ended에서 상대적으로 낮음

---

## 8. SE vs 다른 방법 비교

| 방법 | 핵심 원리 | 생성 횟수 | Model Access | AUROC | 장점 |
|------|----------|----------|--------------|-------|------|
| **Semantic Entropy** | 의미 클러스터 엔트로피 | 10회 | Sampling | 0.92 | 의미론적 정확성 |
| **SEP** | Hidden state probe | 1회 | White-box | 0.85 | 10배 고속, 일반화 |
| **SelfCheckGPT** | 일관성 체크 | 5-10회 | Sampling | 0.80 | Simple |
| **ORION** | Encoder 임베딩 | 1회 | White-box | 0.83 | Zero-shot |
| **RAG-HAT** | DPO 학습 | 1회 (after training) | White-box | 0.84 | 환각 완화 |
| **p(True)** | Few-shot ICL | 10회 | Sampling | 0.88 | No training |

**선택 가이드**:
- **정확도 최우선**: Semantic Entropy (원본)
- **비용 효율**: SEP (훈련 가능 시) 또는 ORION (zero-shot)
- **Black-box API**: Semantic Entropy 또는 SelfCheckGPT
- **환각 완화까지**: RAG-HAT

---

## 9. 핵심 인사이트

### ✅ 강력한 이론적 기반
- **토큰 확률 != 의미론적 불확실성** 명확히 구분
- 수학적으로 엄밀한 정의 (엔트로피 기반)
- Nature 687회 인용 (영향력 큰 연구)

### ✅ 실용적 개선 (SEPs)
- 10배 비용 절감하면서 성능 유지
- Unsupervised 학습 가능 (정답 라벨 불필요)
- OOD 일반화 우수 (Accuracy probe 대비)

### ✅ Hidden State의 통찰
- **모델 내부가 SE를 인코딩함** (실험적 증거)
- 생성 전에도 불확실성 파악 가능 (TBG)
- Mechanistic interpretability 연구 방향 제시

### ⚠️ 실무 고려사항
- Black-box API에서는 원본 SE만 가능
- Long-form에서는 중간 레이어가 최적
- Domain에 따라 성능 차이 존재

---

## 내가 얻은 인사이트

1. **표현 방식이 아닌 전달하고자 하는 의미를 분석하자는 컨셉**
   - 기존 방법들은 토큰 확률에 집착했지만, 진짜 중요한 건 "모델이 답을 아는가?"
   - Lexical/Syntactic uncertainty는 노이즈일 뿐임

2. **Hidden state가 생각보다 많은 정보를 담고 있음**
   - 응답 생성 전에도 이미 모델은 자기가 질문에 대해 아는지 모르는지 암
   - 심지어 컨텍스트를 추가하면 훈련 받고 안 받고에 따라 hidden state가 반응을 함
   - 요는 사람도 모르는 질문 받을 때 쫄리는 것 처럼, 아무리 혼신의 구라로 그럴듯한 추론을 해낸다고 해도 LLM의 뇌를 들여다보면 반드시 흔적이 남는다는 것
   - 확신이 있다면 표현이 달라도 담고자하는 의미는 하나, 확신이 없다면 표현을 아무리 꾸며도 담고 있는 의미는 불안함

3. **Unsupervised 접근의 역설적 우월성**
   - 정답을 학습하는 것은 외부 세계의 지식에 의존하여 과적합과 같은 문제에 취약함, 도메인이 바뀌면 배워온 건 무용지물임
   - 외부 세계가 아닌 LLM 스스로가 아는지 모르는 지를 기준으로 한다면 일관성있는 답을 하는지를 본다는 접근임
   - 이런 접근은 정답을 보는 것이 아니라 일관성을 보는 것임. 도메인이 바뀌어 배운게 사라져도 이 일관성(모르는 답에 대해 불안정하게 대답하는 정도)는 남는다.
   - 그렇기에 할루시네이션 탐지 시 외운 정답을 잘 검증하는 모델보다 정답셋이 없더라도 자신의 현재 상태를 잘 인식하는 모델이 역설적이게도 더 잘한다는 것
   - 재밌는 접근이나 실제로 어떻게 활용할 지? 실제로도 괜찮을지?는 아직 잘 와닿지는 않음, 아직 정답을 외우고 맞추라 해도 잘 못하는데 OOD까지 생각하는 건 너무 앞서가는 느낌이 듬

4. **비용-성능 트레이드오프의 현명한 선택**
   - 원본 SE: 10배 비용, 0.92 AUROC → 고위험 도메인
   - SEP: 1배 비용, 0.85 AUROC → 일반 서비스
   - 10% 성능 포기로 90% 비용 절감 → 실용적인 선택
