# LLM-Check: Eigen-Analysis 기반 초고속 환각 탐지

## 출처
- **링크**: https://openreview.net/forum?id=LYx4w3CAgy

---

## AI 요약

**LLM-Check**는 LLM의 **hidden states, attention maps, output probabilities**를 eigen-analysis로 분석하여 환각을 탐지하는 방법입니다. **단일 응답만으로** white-box/black-box 모두 지원하며, **45x-450x 속도 향상**을 달성했습니다. RAG 환경에서 ground-truth 참조 문서가 있을 때 더욱 강력하며, 기존 방법 대비 **극도로 compute-efficient**합니다.

**핵심**: Sampling 없이 단일 forward pass의 내부 신호만으로 환각 감지 → 실시간 분석 가능

**기존 방법의 문제점**

| 방법 | 생성 횟수 | 추가 모델 | 계산 비용 | 문제점 |
|------|----------|----------|----------|--------|
| Semantic Entropy | 10회 | NLI | 10x | 느림 |
| SelfCheckGPT | 5-10회 | - | 5-10x | 느림 |
| RAG-HAT | 1회 | GPT-4 | 추가 API | 외부 의존 |
| SEP | 1회 | Probe | 1x + 학습 | 훈련 필요 |

**공통 문제**: 다중 생성 필요 → 비싸고 느림, 외부 모델 의존 → 복잡도 증가, 실시간 적용 어려움

**LLM-Check의 접근**

```python
# 단일 forward pass의 부산물 활용
output, hidden_states, attention_maps, probs = model.generate(
    prompt, 
    return_dict=True,
    output_hidden_states=True,
    output_attentions=True
)

# Eigen-analysis로 환각 신호 추출
hallucination_score = eigen_analyze(hidden_states, attention_maps, probs)
```

**핵심 통찰**: **Hidden states**는 모델이 "무엇을 아는지" 인코딩, **Attention maps**는 어디에 집중하는지 (불확실하면 분산), **Output probabilities**는 토큰 확률 분포 (낮으면 불확실) → **Eigen-analysis로 이 3가지를 통합 분석**

**Eigen-Analysis란?** **Eigen-analysis** (고유값 분석)는 행렬의 "주성분" 방향과 크기를 찾아 데이터의 본질적 구조를 파악합니다.

```python
# Hidden states를 행렬로 표현
H = hidden_states  # shape: (layers, seq_len, hidden_dim)

# Covariance matrix 계산
C = H.T @ H  # shape: (hidden_dim, hidden_dim)

# Eigen decomposition
eigenvalues, eigenvectors = np.linalg.eig(C)

# 환각 시그널
# - Eigenvalues가 고르게 분산 → 불확실 (환각 가능성)
# - 특정 eigenvalue 지배 → 확실 (정확한 답)
entropy_of_eigenvalues = -sum(p * log(p) for p in normalize(eigenvalues))
```

**Hidden states의 구조 파악**: 확실한 답 (Paris)는 `hidden_states = [[0.8, 0.1, 0.05, ...], [0.82, 0.09, 0.04, ...], ...]` → 1개 eigenvalue 지배 (높은 variance), 불확실한 답 (Naples, Rome, Berlin)은 `hidden_states = [[0.3, 0.25, 0.22, ...], [0.28, 0.27, 0.21, ...], ...]` → Eigenvalues 고르게 분포 (낮은 variance)

**Attention maps도 동일 원리**: 확실하면 → 특정 토큰에 집중 (high eigen-concentration), 불확실하면 → 여러 토큰에 분산 (low eigen-concentration)

**LLM-Check 구현**

```python
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer

class LLMCheck:
    def __init__(self, model_name="meta-llama/Llama-2-7b-hf"):
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    def detect_hallucination(self, prompt, response=None):
        """White-box: hidden states + attention / Black-box: output probabilities만"""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model(
                **inputs,
                output_hidden_states=True,
                output_attentions=True,
                return_dict=True
            )
        
        # 3가지 신호 추출
        hidden_score = self._analyze_hidden_states(outputs.hidden_states)
        attention_score = self._analyze_attention(outputs.attentions)
        prob_score = self._analyze_probabilities(outputs.logits)
        
        # 통합 점수
        hallucination_score = (
            0.4 * hidden_score + 
            0.3 * attention_score + 
            0.3 * prob_score
        )
        
        return {
            "is_hallucination": hallucination_score > 0.5,
            "confidence": hallucination_score,
            "breakdown": {
                "hidden": hidden_score,
                "attention": attention_score,
                "probability": prob_score
            }
        }
    
    def _analyze_hidden_states(self, hidden_states):
        """Hidden states의 eigen-entropy 계산"""
        all_hiddens = torch.cat([h for h in hidden_states], dim=1)
        H = all_hiddens[0].cpu().numpy()
        
        # Covariance matrix & Eigenvalues
        C = H.T @ H / H.shape[0]
        eigenvalues = np.linalg.eigvalsh(C)
        eigenvalues = eigenvalues[eigenvalues > 0]
        
        # Entropy (높을수록 불확실 → 환각)
        eigen_probs = eigenvalues / eigenvalues.sum()
        entropy = -np.sum(eigen_probs * np.log(eigen_probs + 1e-10))
        max_entropy = np.log(len(eigen_probs))
        
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _analyze_attention(self, attentions):
        """Attention maps의 eigen-concentration 계산"""
        scores = []
        for layer_attention in attentions:
            attn = layer_attention[0].mean(dim=0).cpu().numpy()
            eigenvalues = np.linalg.eigvalsh(attn)
            eigenvalues = eigenvalues[eigenvalues > 0]
            
            # Concentration ratio (top eigenvalue / sum)
            concentration = eigenvalues[-1] / eigenvalues.sum()
            scores.append(1.0 - concentration)  # Low concentration → 불확실
        
        return np.mean(scores)
    
    def _analyze_probabilities(self, logits):
        """Output token probabilities의 불확실성"""
        probs = torch.softmax(logits[0], dim=-1).cpu().numpy()
        
        token_entropies = []
        for token_probs in probs:
            top_k = 100
            top_probs = np.sort(token_probs)[-top_k:]
            top_probs = top_probs / top_probs.sum()
            
            entropy = -np.sum(top_probs * np.log(top_probs + 1e-10))
            token_entropies.append(entropy)
        
        avg_entropy = np.mean(token_entropies)
        max_entropy = np.log(top_k)
        
        return avg_entropy / max_entropy

# 사용 예시
checker = LLMCheck()
result = checker.detect_hallucination("What is the capital of France?")
print(result)
# {"is_hallucination": False, "confidence": 0.15, "breakdown": {...}}
```

**Black-box Mode (API only)**

```python
class LLMCheckBlackBox:
    """Output probabilities만 사용 (OpenAI API 등)"""
    def detect_hallucination(self, prompt, response, logprobs):
        if logprobs is None:
            raise ValueError("Black-box mode requires token logprobs")
        
        token_uncertainties = []
        for token_logprob in logprobs:
            prob = np.exp(token_logprob)
            uncertainty = 1.0 - prob
            token_uncertainties.append(uncertainty)
        
        avg_uncertainty = np.mean(token_uncertainties)
        
        return {
            "is_hallucination": avg_uncertainty > 0.5,
            "confidence": avg_uncertainty
        }

# OpenAI API 예시
import openai
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "What is the capital of France?"}],
    logprobs=True,
    top_logprobs=5
)

logprobs = [token['logprob'] for token in response.choices[0].logprobs.content]
checker = LLMCheckBlackBox()
result = checker.detect_hallucination("...", response.choices[0].message.content, logprobs)
```

**RAG 환경에서의 LLM-Check**

```python
class LLMCheckRAG:
    """RAG에서 참조 문서를 활용한 강화 탐지"""
    def detect_with_reference(self, prompt, response, reference_docs):
        # 1. 기본 LLM-Check
        base_score = self.detect_hallucination(prompt, response)
        
        # 2. Reference alignment 체크
        alignment_score = self._check_alignment(response, reference_docs)
        
        # 3. 통합
        final_score = 0.6 * base_score + 0.4 * (1.0 - alignment_score)
        
        return {
            "is_hallucination": final_score > 0.5,
            "confidence": final_score,
            "base_detection": base_score,
            "reference_alignment": alignment_score
        }
    
    def _check_alignment(self, response, reference_docs):
        """응답이 참조 문서와 얼마나 일치하는지"""
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        response_emb = encoder.encode(response)
        ref_embs = encoder.encode(reference_docs)
        
        similarities = [
            np.dot(response_emb, ref_emb) / 
            (np.linalg.norm(response_emb) * np.linalg.norm(ref_emb))
            for ref_emb in ref_embs
        ]
        
        return max(similarities)

# 사용 예시
checker = LLMCheckRAG()
retrieved_docs = [
    "Paris is the capital of France.",
    "France's capital city is Paris, known for the Eiffel Tower."
]
result = checker.detect_with_reference(
    prompt="What is the capital of France?",
    response="The capital of France is Paris.",
    reference_docs=retrieved_docs
)
```

**성능 벤치마크 (OpenReview abstract 기반 추정)**

| 방법 | 생성 횟수 | Speedup | AUROC (추정) |
|------|----------|---------|--------------|
| **LLM-Check (White-box)** | 1회 | **450x** | ~0.85 |
| **LLM-Check (Black-box)** | 1회 | **45x** | ~0.75 |
| Semantic Entropy | 10회 | 1x | 0.92 |
| SelfCheckGPT | 5회 | 2x | 0.80 |
| SEP | 1회 | 10x | 0.85 |
| ORION | 1회 | 10x | 0.83 |

**Speedup 분석**: **450x**는 Hidden states + attention eigen-analysis가 단순 행렬 연산이라 GPU 병렬화 극대화 가능, **45x**는 Probability만 사용 시에도 sampling 없이 즉시 계산

**적용 시나리오**: **실시간 챗봇** → White-box (450x 속도), **OpenAI API** → Black-box (Logprobs 활용), **RAG 시스템** → RAG mode (참조 문서 alignment), **배치 처리** → Semantic Entropy (정확도 최우선), **의료/법률** → SE + LLM-Check (이중 검증)

**핵심 통찰**

**Eigen-Analysis의 힘**: 행렬 연산은 GPU에서 극도로 빠름, Sampling 없음 → Latency 제로, 병렬 처리 가능, Hidden states의 "방향성" 분석 → 확신 시 1개 주성분 집중, 불확실 시 여러 주성분 분산

**3가지 신호의 상호 보완**

| 신호 | 측정 대상 | 강점 | 약점 |
|------|----------|------|------|
| **Hidden states** | 내부 표현 | 깊은 의미 파악 | White-box only |
| **Attention** | 집중도 | 토큰 관계 분석 | White-box only |
| **Probabilities** | 출력 확률 | Black-box 가능 | 표면적 신호 |

**Trade-off**: **장점** → 극도로 빠름 (450x), 단일 응답 작동, White/Black-box 지원, RAG 강화 가능 **vs 한계** → 정확도 SE (0.92) < LLM-Check (~0.85), White-box 의존, Eigen 계산 메모리, Threshold 튜닝 필요

**실전 적용**

```python
# Production deployment
class ProductionHallucinationDetector:
    def __init__(self):
        self.llm_check = LLMCheck()  # Fast check
        self.semantic_entropy = SemanticEntropyDetector()  # Slow but accurate
        
    def detect(self, prompt, response, risk_level="medium"):
        quick_result = self.llm_check.detect_hallucination(prompt)
        
        if risk_level == "high" and quick_result["confidence"] > 0.3:
            # Double-check with SE
            se_result = self.semantic_entropy.compute_se_original(prompt)
            return {
                "is_hallucination": se_result > threshold,
                "method": "double_check",
                "llm_check": quick_result,
                "semantic_entropy": se_result
            }
        
        return quick_result

# Threshold 튜닝
from sklearn.metrics import roc_curve

def find_optimal_threshold(validation_data):
    scores, labels = [], []
    for prompt, response, is_hallu in validation_data:
        result = checker.detect_hallucination(prompt)
        scores.append(result["confidence"])
        labels.append(is_hallu)
    
    fpr, tpr, thresholds = roc_curve(labels, scores)
    optimal_idx = np.argmax(tpr - fpr)  # Youden's index
    return thresholds[optimal_idx]

# 도메인별 threshold
thresholds = {
    "medical": 0.3,   # Conservative
    "chatbot": 0.5,   # Balanced
    "creative": 0.7   # Permissive
}
```

**LLM-Check vs 다른 방법**

| 방법 | 핵심 원리 | 속도 | 정확도 | Model Access | 강점 |
|------|----------|------|--------|--------------|------|
| **LLM-Check** | Eigen-analysis | ⚡⚡⚡⚡⚡ | ⭐⭐⭐⭐ | White/Black | 초고속 |
| Semantic Entropy | 의미 클러스터링 | ⚡ | ⭐⭐⭐⭐⭐ | Sampling | 정확도 |
| SEP | Hidden probe | ⚡⚡⚡ | ⭐⭐⭐⭐ | White-box | 일반화 |
| ORION | Encoder 임베딩 | ⚡⚡⚡ | ⭐⭐⭐⭐ | White-box | Zero-shot |
| SelfCheckGPT | 일관성 체크 | ⚡⚡ | ⭐⭐⭐ | Sampling | Simple |

**선택 기준**: 실시간 요구 → LLM-Check, 정확도 최우선 → Semantic Entropy, 학습 가능 → SEP, Zero-shot 필요 → ORION 또는 LLM-Check

---

## 내가 얻은 인사이트

1. **Eigenvalue = 데이터의 "방향성" 요약**
   - Hidden states가 한 방향으로 정렬되면 → 확신
   - 여러 방향으로 흩어지면 → 환각
   - 수학적으로 우아하고 계산도 빠름

2. **3가지 신호의 Ensemble 전략**
   - Hidden states: 깊은 의미 이해
   - Attention: 토큰 관계 분석
   - Probabilities: 출력 확률 (API 호환)
   - Hidden states, Attention, Probabilities는 서로의 약점을 보완

3. **속도의 혁신이 실용성을 만든다**
   - 엄청 빠르다는 것이 강점이고 정확도는 조금 어중간한 느낌이 있음
   - 고위험 케이스만 더블 체크하는 용도로 활용되는 것이 권장 사용법이라고 함
   - 확실히 자체 모델이 응답을 반환하는 서비스의 경우, 빠르니 더블 체크 용도로 좋을 것 같음

4. **Black-box mode의 현실성**
   - GPT-4 API도 logprobs 제공하므로 테스트 가능
   - 완벽하지는 않아도 Probability만으로도 어느 정도 탐지 가능
