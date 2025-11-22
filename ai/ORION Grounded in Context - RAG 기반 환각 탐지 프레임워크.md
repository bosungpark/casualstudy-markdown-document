# ORION Grounded in Context - RAG 기반 환각 탐지 프레임워크

## 링크
https://arxiv.org/abs/2504.15771

## AI 요약

### 핵심 문제: 512 토큰으로 10,000+ 토큰 검증하기

**프로덕션 RAG 시스템의 딜레마:**
```
검색된 컨텍스트: 10,000 토큰 (여러 문서, noisy)
LLM 생성 답변: 500 토큰
Encoder NLI 모델: 512 토큰 윈도우만 지원 ← 어떻게 검증?
```

**기존 접근법의 한계:**
1. **Windowing (Luna)**: 전체 답변을 512 토큰 윈도우로 슬라이딩 → 컨텍스트가 잘림
2. **Long-context 모델 (LettuceDetect)**: 8K ModernBERT → 모델 크기 커지고, 노이즈 많음
3. **LLM Prompting (GPT-4)**: 비싸고 느리고, precision 낮음

### ORION의 핵심 해결책: Per-Claim Retrieval

**역발상: 생성은 전체 컨텍스트 → 검증은 부분 컨텍스트**

```
생성 (RAG):
Query → Retrieve ALL docs → LLM sees 10K tokens → Generate answer

검증 (ORION):
Answer → Split to claims → Each claim retrieves RELEVANT 500 tokens → NLI check
```

**이게 작동하는 이유:**
```python
# 전체 검증 (불가능)
NLI(answer_500_tokens, context_10000_tokens)  # 512 초과!

# Per-claim 검증 (가능)
for claim in claims:  # claim: 30~60 토큰
    relevant = retrieve_top_k(claim, context)  # 200~400 토큰
    score = NLI(claim, relevant)  # 총 230~460 토큰 ✓
```

### 실제 구현: 6단계 파이프라인

#### 1단계: Claim 분할 (Adaptive Chunking)

```python
class AdaptiveChunker:
    def __init__(self, max_size=60, max_overlap=10):
        self.max_size = max_size  # 토큰
        self.max_overlap = max_overlap
    
    def chunk(self, text):
        """재귀적으로 텍스트를 의미 단위로 분할"""
        separators = ["\n\n", "\n", ". ", ", ", " "]
        
        for sep in separators:
            chunks = text.split(sep)
            if all(len(c) <= self.max_size for c in chunks):
                return self._add_overlap(chunks)
        
        # 강제 분할
        return self._split_by_tokens(text, self.max_size)
```

**60 토큰 선택 근거:**
```
데이터 분석 결과 (Figure 1):
- 평균 문장 길이: 40~50 토큰
- 60 토큰: 95% 문장을 자연스럽게 포함
- 100 토큰: 여러 주장 섞임 → NLI 혼란
- 30 토큰: 문장 중간에서 자름 → 의미 손실
```

#### 2단계: Non-factual Filtering

```python
class FactualFilter:
    def __init__(self):
        # 경량 BERT 분류기 (100M 파라미터)
        self.classifier = BERTClassifier(
            classes=["factual", "non_factual"]
        )
    
    def filter(self, claims):
        filtered = []
        for claim in claims:
            if self.is_factual(claim):
                filtered.append(claim)
        return filtered
    
    def is_factual(self, claim):
        """정보 밀도가 높은 주장만 통과"""
        # "안녕하세요" → False
        # "2024년 매출은 100억" → True
        return self.classifier.predict(claim) == "factual"
```

**필터링 예시:**
```python
claims = [
    "안녕하세요, 고객님!",           # → 제외
    "본 보고서는 다음과 같습니다.",   # → 제외
    "2024년 매출은 100억입니다.",    # → 통과
    "CEO는 김철수입니다.",           # → 통과
]
filtered = ["2024년 매출은 100억입니다.", "CEO는 김철수입니다."]
```

#### 3단계: Context Chunking (Dynamic Parameters)

```python
def chunk_context(context, claim_length):
    """Claim 길이에 따라 동적으로 청크 크기 조정"""
    
    # 512 토큰 윈도우 계산
    max_window = 512
    overhead = 20  # [CLS], [SEP], special tokens
    
    # Claim이 차지하는 공간
    claim_space = claim_length + overhead
    
    # Context에 사용 가능한 공간
    available = max_window - claim_space  # 예: 512 - 50 = 462
    
    # 청크 크기 결정
    chunk_size = min(available // 4, 150)  # 4개 청크 기준
    
    chunks = recursive_chunk(context, chunk_size)
    return chunks
```

**동적 청킹 전략:**
```
Claim 10 토큰 → Available 482 토큰 → Chunk size ~120 → k=4
Claim 30 토큰 → Available 462 토큰 → Chunk size ~115 → k=4
Claim 60 토큰 → Available 432 토큰 → Chunk size ~108 → k=4
```

#### 4단계: Per-Claim Retrieval (핵심!)

```python
class DynamicRetriever:
    def __init__(self, embedding_model="AngleEmbeddings"):
        self.embedder = AngleEmbeddings()  # Li & Li 2024
    
    def retrieve_for_claim(self, claim, context_chunks, claim_length):
        """각 주장마다 최적의 k 계산 후 검색"""
        
        # 동적 k 계산
        k = self.calculate_k(claim_length)
        
        # Claim 임베딩
        claim_emb = self.embedder.encode(claim)
        
        # 모든 청크 임베딩
        chunk_embs = self.embedder.encode(context_chunks)
        
        # 코사인 유사도로 Top-k 검색
        similarities = cosine_similarity(claim_emb, chunk_embs)
        top_k_indices = np.argsort(similarities)[-k:]
        
        return [context_chunks[i] for i in top_k_indices]
    
    def calculate_k(self, claim_length):
        """512 토큰 제약 내에서 최대 k 계산"""
        max_window = 512
        overhead = 20
        avg_chunk_size = 100  # 청킹 단계에서 설정
        
        available = max_window - claim_length - overhead
        k = available // avg_chunk_size
        
        return max(2, min(k, 8))  # 2~8 사이
```

**동적 k의 실제 동작:**
```python
# 예시 1: 짧은 주장
claim = "CEO는 김철수다."  # 10 토큰
k = (512 - 10 - 20) // 100 = 4.82 → k=4
retrieved = 4 chunks × 100 tokens = 400 tokens
total = 10 + 400 + 20 = 430 tokens ✓

# 예시 2: 긴 주장
claim = "2024년 회사 실적은 전년 대비 20% 증가했으며..."  # 50 토큰
k = (512 - 50 - 20) // 100 = 4.42 → k=4
retrieved = 4 chunks × 100 tokens = 400 tokens
total = 50 + 400 + 20 = 470 tokens ✓

# 예시 3: 매우 긴 주장 (60 토큰 상한)
claim = "복잡한 문장..."  # 60 토큰
k = (512 - 60 - 20) // 100 = 4.32 → k=4
retrieved = 4 chunks × 100 tokens = 400 tokens
total = 60 + 400 + 20 = 480 tokens ✓
```

**왜 Retrieval이 중요한가?**
```
Luna (Windowing):
전체 컨텍스트를 512 윈도우로 슬라이딩
→ 관련 없는 정보도 포함
→ 노이즈 많음

LettuceDetect (Long Context):
8K 토큰 전부 처리
→ 모델 크고 느림
→ 노이즈 많음

ORION (Retrieval):
각 주장마다 관련 청크만 검색
→ 노이즈 적음 ← F1 0.83 달성의 핵심!
→ 빠르고 정확함
```

#### 5단계: NLI Scoring

```python
class NLIScorer:
    def __init__(self):
        # WeCheck 또는 DeBERTA-NLI
        self.nli_model = WeCheck()  # Wu et al. 2023
    
    def score_pair(self, claim, chunk):
        """(주장, 청크) 쌍의 entailment 확률 계산"""
        
        # Input 구성
        input_text = f"[CLS] {claim} [SEP] {chunk} [SEP]"
        
        # NLI 예측
        logits = self.nli_model(input_text)
        probs = softmax(logits)  # [entailment, neutral, contradiction]
        
        # Entailment 확률만 사용
        return probs[0]
    
    def score_claim(self, claim, retrieved_chunks):
        """하나의 주장에 대해 여러 청크 점수화"""
        scores = []
        for chunk in retrieved_chunks:
            score = self.score_pair(claim, chunk)
            scores.append(score)
        return scores
```

**NLI의 3-way 분류:**
```
Entailment (수반됨):
Claim: "CEO는 김철수다"
Chunk: "회사의 대표이사는 김철수이며..." → 0.95

Neutral (중립):
Claim: "CEO는 김철수다"
Chunk: "회사는 1990년 설립되었다" → 0.05

Contradiction (모순):
Claim: "CEO는 김철수다"
Chunk: "대표이사는 이영희입니다" → 0.02
```

#### 6단계: Aggregation (Negative Weighting)

```python
class ScoreAggregator:
    def __init__(self, negative_weight=2.0):
        self.negative_weight = negative_weight
    
    def aggregate(self, scores):
        """환각에 더 큰 페널티 부여"""
        weighted_scores = []
        
        for score in scores:
            if score < 0.5:  # Contradiction or Neutral
                # 부정적 점수는 가중치 2배
                weighted = score * self.negative_weight
            else:  # Entailment
                weighted = score
            weighted_scores.append(weighted)
        
        # 가중 평균
        return sum(weighted_scores) / len(weighted_scores)
    
    def aggregate_to_response_level(self, claim_scores):
        """전체 응답 레벨 점수"""
        # 최소값 기준 (가장 약한 고리)
        return min(claim_scores)
```

**집계 전략의 의미:**
```python
# 예시: 3개 청크 검색
scores = [0.9, 0.8, 0.2]  # 2개 지지, 1개 모순

# 단순 평균 (안 좋음)
simple_avg = (0.9 + 0.8 + 0.2) / 3 = 0.63  # 괜찮아 보임 ✗

# Negative weighting (ORION)
weighted = [0.9, 0.8, 0.2 * 2.0] / 3 = 0.73  # 하지만 패널티 적용
# 또는 min 기준: 0.2 → 환각 탐지! ✓
```

**실전 예시:**
```python
claim = "CEO는 김철수다"
retrieved_chunks = [
    "대표이사는 이영희입니다",      # → 0.05 (모순!)
    "회사는 서울에 위치합니다",     # → 0.1 (중립)
    "임직원은 500명입니다",        # → 0.1 (중립)
]

# Negative weighting
weighted = (0.05*2 + 0.1*2 + 0.1*2) / 3 = 0.167
# 낮은 점수 → 환각 탐지!

# Min 기준
min_score = 0.05 → 환각!
```

### 완전한 파이프라인 구현

```python
class GroundedInContext:
    def __init__(self):
        self.chunker = AdaptiveChunker(max_size=60)
        self.filter = FactualFilter()
        self.retriever = DynamicRetriever()
        self.nli = NLIScorer()
        self.aggregator = ScoreAggregator(negative_weight=2.0)
    
    def evaluate(self, output, context):
        """전체 파이프라인"""
        
        # 1. Output을 claim으로 분할
        claims = self.chunker.chunk(output)
        
        # 2. Factual claims만 필터링
        factual_claims = self.filter.filter(claims)
        
        # 3. Context 청킹
        context_chunks = self.chunker.chunk(context)
        
        # 4-6. 각 claim 평가
        claim_scores = []
        for claim in factual_claims:
            # 4. Retrieval
            retrieved = self.retriever.retrieve_for_claim(
                claim, context_chunks, len(claim.split())
            )
            
            # 5. NLI Scoring
            scores = self.nli.score_claim(claim, retrieved)
            
            # 6. Aggregation
            claim_score = self.aggregator.aggregate(scores)
            claim_scores.append(claim_score)
        
        # Response-level 점수
        final_score = self.aggregator.aggregate_to_response_level(
            claim_scores
        )
        
        return {
            "score": final_score,
            "claim_scores": claim_scores,
            "hallucinated_claims": [
                c for c, s in zip(factual_claims, claim_scores) 
                if s < 0.5
            ]
        }
```

### 긴 컨텍스트 처리: 실전 시나리오

#### 시나리오 1: 10,000 토큰 RAG 컨텍스트

```python
# RAG 시스템이 생성한 데이터
context = """
[Document 1 - 3000 tokens]: 회사 연혁...
[Document 2 - 2500 tokens]: 재무제표...
[Document 3 - 2000 tokens]: 임원진 정보...
[Document 4 - 2500 tokens]: 사업 계획...
"""  # 총 10,000 토큰

output = """
2024년 회사 매출은 전년 대비 20% 증가한 1000억원을 기록했습니다.
CEO 김철수는 신사업 진출을 발표했으며, 
직원 수는 500명으로 증가했습니다.
"""  # 약 50 토큰

# ORION 평가
evaluator = GroundedInContext()

# 1. Chunking
claims = [
    "2024년 회사 매출은 전년 대비 20% 증가한 1000억원을 기록했습니다",  # 25 토큰
    "CEO 김철수는 신사업 진출을 발표했습니다",  # 15 토큰
    "직원 수는 500명으로 증가했습니다",  # 10 토큰
]

# 2. Per-claim Processing
for claim in claims:
    # Context 청킹: 10,000 토큰 → 100개 청크 (각 100 토큰)
    context_chunks = chunker.chunk(context)  # [c1, c2, ..., c100]
    
    # Retrieval: 100개 중 top-4만 가져오기
    k = calculate_k(len(claim.split()))  # k=4
    retrieved = retrieve_top_k(claim, context_chunks, k=4)
    # retrieved: 4 chunks × 100 tokens = 400 tokens
    
    # NLI: 512 윈도우에 딱 맞음!
    # claim (25) + retrieved (400) + overhead (20) = 445 ✓
    score = nli_model(claim, retrieved)
```

**처리 효율성:**
```
Luna (Windowing):
10,000 토큰 → 20번 윈도우 슬라이딩 (512씩)
각 claim마다 20번 NLI 호출
총 NLI 호출: 3 claims × 20 = 60번

ORION (Retrieval):
10,000 토큰 → 100 청크
각 claim마다 4개만 검색
총 NLI 호출: 3 claims × 4 = 12번 ← 5배 빠름!
```

### 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Generated Output O                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ Chunker T   │
                    │ max_size=60 │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Claims C  │
                    │ [c1,c2,...] │
                    └──────┬──────┘
                           │
                    ┌──────▼──────────┐
                    │ Factual Filter F│
                    │ (Encoder-based) │
                    └──────┬──────────┘
                           │
                    ┌──────▼──────────┐
                    │ Factual Claims  │
                    │ C' ⊆ C          │
                    └──────┬──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
│   Claim c1     │  │  Claim c2   │  │   Claim cn     │
└───────┬────────┘  └──────┬──────┘  └───────┬────────┘
        │                  │                  │
        │         ┌────────▼────────┐         │
        │         │  Context D      │         │
        │         │  Chunker T      │         │
        │         │ [d1,d2,...,dm]  │         │
        │         └────────┬────────┘         │
        │                  │                  │
┌───────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
│ Retrieval (k)  │  │Retrieval(k) │  │ Retrieval (k)  │
│ R1=[d11,..]    │  │R2=[d21,..]  │  │ Rn=[dn1,..]    │
└───────┬────────┘  └──────┬──────┘  └───────┬────────┘
        │                  │                  │
┌───────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
│ NLI Scoring M  │  │NLI Scoring M│  │ NLI Scoring M  │
│ p_ent(c1,d11)  │  │p_ent(c2,..) │  │ p_ent(cn,..)   │
└───────┬────────┘  └──────┬──────┘  └───────┬────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                    ┌──────▼──────────┐
                    │ Aggregation A   │
                    │(Negative-weight)│
                    └──────┬──────────┘
                           │
                    ┌──────▼──────────┐
                    │  Final Score    │
                    │ (0=환각, 1=정상) │
                    └─────────────────┘
```

### 3가지 핵심 과제와 해결책

#### 과제 1: 비사실적 문장 (Non-factual Statements)
**문제:**
```
"안녕하세요!"           ← 환각 아님, 하지만 컨텍스트와 일치 안 함
"본 보고서는..."       ← 제목, 환각 아님
"2024년 매출은 100억"  ← 사실적 주장, 검증 필요!
```

**해결:** 
- 경량 factual claims classifier로 필터링
- 정보 밀도(information density) 낮은 문장 제외

#### 과제 2: 긴 컨텍스트 (Long Context)
**문제:**
```
RAG 검색 컨텍스트: 10,000 토큰
Encoder NLI 모델: 512 토큰 윈도우 ← 불가능!
```

**해결:**
- **RAG-inspired retrieval**: 각 주장마다 전용 컨텍스트 검색
- ModernBERT (8K 토큰) 같은 최신 모델 사용 계획

#### 과제 3: 예측 해상도 (Prediction Resolution)
**옵션들:**
- Token-level: 가장 세밀, 설명력 최고, 하지만 학습 어려움
- Proposition-level: 균형잡힌 선택 ← **ORION이 선택**
- Sequence-level: 너무 거칠음

**ORION의 선택 이유:**
```python
# Proposition-level
"2024년 매출은 100억이고, CEO는 김철수다."
  ↓ 분해
["2024년 매출은 100억이다", "CEO는 김철수다"]
  ↓ 각각 검증
[True, False]  # 명확한 원인 분석 가능

# vs Token-level
["2024", "년", "매출", "은", ...]  # 너무 세밀, 오버헤드
```

### RAGTruth 벤치마크 결과

**전체 F1 점수 비교:**

| 방법 | 모델 크기 | 훈련 여부 | F1 Score |
|-----|----------|---------|----------|
| **RAG-HAT** | Large | ✅ RAGTruth | **0.84** |
| **ORION** | Small | ❌ OOD | **0.83** |
| LettuceDetect-large | Medium | ✅ RAGTruth | 0.79 |
| Finetuned Llama-2-13B | 13B | ✅ RAGTruth | 0.79 |
| Luna | Medium | ❌ OOD | 0.65 |
| Prompt GPT-4-turbo | Very Large | ❌ OOD | 0.63 |

**ORION의 놀라운 점:**
1. RAGTruth로 훈련 안 했는데 0.83 달성
2. 훈련한 모델들과 거의 동등
3. 훈련한 RAG-HAT(0.84)와 0.01 차이만

**태스크별 성능 (ORION):**

| Task | Precision | Recall | F1 |
|------|-----------|--------|-----|
| Question Answering | 88.4 | 91.9 | **90.1** |
| Summarization | 85.4 | 87.1 | **86.2** |
| Data-to-Text | 64.4 | 82.2 | 72.2 |

**Data-to-Text에서 낮은 이유:**
```json
// 구조화된 데이터 예시
{
  "name": "John",
  "age": 30,
  "city": "NYC"
}
```
- 청킹이 어려움 (테이블, JSON 구조)
- 훈련 데이터에 구조화 데이터 부족
- Feature extraction use-case 위주 훈련 → 낮은 precision, 높은 recall

### 경쟁 모델 비교

#### Luna (이전 분석한 모델)
```
Luna: Token-level, DeBERTA-large (440M)
- Window aggregation으로 긴 컨텍스트 처리
- F1: 0.65

ORION: Proposition-level, Encoder-based (smaller)
- Retrieval로 긴 컨텍스트 처리
- F1: 0.83
```

**ORION이 Luna보다 나은 이유:**
1. **Retrieval > Windowing**: 관련 컨텍스트만 가져옴
2. **Proposition > Token**: 학습하기 쉬운 태스크
3. **경량 모델**: 프로덕션 배포 용이

#### LettuceDetect
```
LettuceDetect: ModernBERT (8K context, 396M)
- Native long context
- F1: 0.79 (훈련함)

ORION: 512 token context
- Retrieval로 극복
- F1: 0.83 (훈련 안 함)
```

**시사점:** 긴 컨텍스트 윈도우 < 똑똑한 검색 전략

### 핵심 기술 차별점

#### 1. 동적 k 선택의 중요성
```python
# 1. Chunker
from recursive_text_splitter import RecursiveTextSplitter
chunker = RecursiveTextSplitter(
    max_chunk_size=60,  # 토큰
    max_overlap=o_max
)

# 2. Factual Classifier
factual_filter = EncoderModel(
    task="binary_classification",
    classes=["factual", "non_factual"]
)

# 3. Retrieval
from angle_embeddings import AngleEmbeddings
retriever = AngleEmbeddings()  # Li & Li, 2024

# 4. NLI Model
from wecheck import WeCheck
nli_model = WeCheck()  # Wu et al., 2023
# or 자체 proprietary NLI (Deepchecks)

# 5. Aggregator
def aggregate(scores, negative_weight=2.0):
    weighted = []
    for score in scores:
        if score < 0.5:  # contradiction/neutral
            weighted.append(score * negative_weight)
        else:
            weighted.append(score)
    return sum(weighted) / len(weighted)
```

#### 동적 k 선택 알고리즘
```python
def choose_k(claim_length, max_context=512):
    """
    claim_length: 토큰 수
    max_context: NLI 모델의 최대 윈도우
    """
    # Special tokens, separator 등 오버헤드
    overhead = 20
    
    # 사용 가능한 공간
    available = max_context - claim_length - overhead
    
    # 청크 평균 크기 (동적 청킹 파라미터에서)
    avg_chunk_size = 100  # 예시
    
    # 최대로 넣을 수 있는 청크 수
    k = available // avg_chunk_size
    
    # 최소 2개, 최대 10개
    return max(2, min(k, 10))
```

### 향후 개선: ModernBERT 통합의 임팩트
**현재:**
```
512 토큰 윈도우 → 낮은 k → 관련 청크 놓칠 가능성
```

**향후:**
```python
# ModernBERT: 8,192 토큰 윈도우
nli_model = ModernBERT(context_window=8192)

# 더 많은 청크 검색 가능
k = choose_k(claim_length, max_context=8192)
# k가 2~10 → 10~50으로 증가 가능

# 더 나은 contextualization
# 더 높은 정확도 예상
```

#### 2. 구조화 데이터 처리 개선
```python
# 특화된 청커
class StructuredDataChunker:
    def chunk_table(self, table):
        # 행 단위, 열 단위 청킹
        pass
    
    def chunk_json(self, json_obj):
        # 키-값 쌍 단위 청킹
        pass
```

#### 3. 실시간 프로덕션 최적화
```python
# 배치 처리
results = evaluator.evaluate_batch([
    (output1, context1),
    (output2, context2),
    # ...
])

# 비동기 처리
async_results = await evaluator.evaluate_async(
    output, context
)
```

### 기술적 차별점

#### 1. Zero-Shot 성능
- RAGTruth로 훈련 안 했는데 0.83
- Out-of-distribution에서 강건함
- **실전 데이터에 바로 적용 가능**

#### 2. 경량 모델
```
RAG-HAT: Large model
ORION: Small encoder (< 500M parameters)

→ 추론 속도 빠름
→ 메모리 효율적
→ 비용 절감
```

#### 3. 설명 가능성
```python
result.hallucinated_claims[0]
# {
#   "text": "CEO는 김철수다",
#   "confidence": 0.95,
#   "context_matches": [
#     {"chunk": "...", "score": 0.2},  # 모순
#     {"chunk": "...", "score": 0.3}   # 모순
#   ],
#   "reason": "모든 관련 청크가 모순됨"
# }
```

#### 4. 프로덕션 친화적
- 512 토큰 윈도우 → 빠른 추론
- 모듈형 설계 (청커, 필터, 검색, NLI 분리)
- 각 컴포넌트 교체 가능

### ORION vs Luna vs LettuceDetect 비교

| | ORION | Luna | LettuceDetect |
|---|-------|------|---------------|
| **레벨** | Proposition | Token | Token |
| **컨텍스트 처리** | Retrieval | Windowing | Native 8K |
| **모델 크기** | Small | Medium (440M) | Large (396M) |
| **훈련 데이터** | ❌ RAGTruth | ❌ RAGTruth | ✅ RAGTruth |
| **F1 (RAGTruth)** | **0.83** | 0.65 | 0.79 |
| **강점** | Zero-shot, 경량 | 토큰 정밀도 | Long context |
| **약점** | Data-to-text | 낮은 F1 | 훈련 필요 |

### ORION Family의 다른 멤버들

**Grounded in Context** 외에 ORION은 다차원 평가 수행:

1. **Factual Consistency** ← Grounded in Context
2. **Information Density**: 정보 밀도 평가
3. **Task Relevance**: 태스크 관련성
4. **Avoidance**: 회피성 답변 탐지

```python
# ORION 전체 평가
from orion import ORIONEvaluator

evaluator = ORIONEvaluator()
results = evaluator.evaluate(
    output=llm_output,
    context=context,
    query=query,
    dimensions=[
        "factual_consistency",  # Grounded in Context
        "information_density",
        "task_relevance",
        "avoidance"
    ]
)
```

## 내가 얻은 인사이트

### 1. Per-Claim Retrieval의 핵심 통찰
단순하게 토큰이나 길이 단위 청크로 모두 검사하지 말고 “주장을 포함한 문장” 단위 중 질문과 관련이 있는 top k 개 문장만 동적으로 청킹하여 검증을 하면 모델 컨텍스트 크기를 늘리지 않아도 수백 토큰(60 * k) 수준으로 95% 이상의 대화를 커버할 수 있다는 컨셉임


### 2. 동적 k 선택의 엔지니어링
고정된 k가 아니라 claim 길이에 따라 k를 조정한 게 실용적이다:
```python
k = (512 - claim_length - 20) // avg_chunk_size
```
이는 **제약 조건(512 토큰)을 변수로 바꾼** 좋은 예시. 파라미터를 하드코딩하지 않고 런타임에 계산.

### 3. Negative Weighting의 안전 우선 설계
환각(모순)에 2배 가중치를 준 건 프로덕션의 현실을 반영한다:
- False Negative (놓친 환각): 치명적 → 사용자에게 잘못된 정보
- False Positive (오탐): 덜 치명적 → 보수적 판단

```python
if score < 0.5:
    weighted = score * 2.0  # 환각 페널티
```
이는 **안전 시스템 설계의 원칙**을 보여준다.

### 4. 60 토큰 청킹의 Empirical Justification
Figure 1의 데이터 분석으로 60 토큰을 선택한 건 좋은 엔지니어링:
- 임의 선택 아님
- 실제 데이터 분포 기반
- 95%의 문장을 자연스럽게 캡처

**데이터가 하이퍼파라미터를 결정**하게 한 사례.

### 5. Retrieval > Long Context의 증명
```
LettuceDetect: 8K 네이티브 → F1 0.79
ORION: 512 + retrieval → F1 0.83
```
이는 **"노이즈 섞인 긴 컨텍스트 < 정확한 짧은 컨텍스트"**를 입증한다. 정보 검색의 precision이 모델 윈도우보다 중요.

## 내가 얻은 인사이트

### 1. Per-Claim Retrieval: 전처리의 빈공간
"주장을 포함한 문장" 단위(60 토큰)로 검증하면 모델 컨텍스트를 늘리지 않아도 95% 대화를 커버할 수 있다. 이는:
- 의미적 컨텍스트를 끊지 않음
- 노이즈 제거
- Luna/LettuceDetect가 집중하지 않던 **데이터 전처리 관점**의 접근

### 2. 동적 k 선택: 제약을 변수로
```python
k = (512 - claim_length - 20) // avg_chunk_size
```
제약 조건(512 토큰)을 하드코딩하지 않고 런타임 계산. 실용적 엔지니어링.

### 3. Negative Weighting: 안전 우선
환각(모순)에 2배 가중치 → False Negative(놓친 환각)가 False Positive(오탐)보다 치명적이라는 프로덕션 현실 반영.

### 4. 60 토큰 청킹: 데이터 기반 선택
Figure 1 분석으로 95% 문장을 자연스럽게 캡처하는 60 토큰 선택. 임의 선택이 아닌 **데이터가 하이퍼파라미터를 결정**.

### 5. Retrieval > Long Context
```
LettuceDetect: 8K 네이티브 → F1 0.79
ORION: 512 + retrieval → F1 0.83
```
노이즈 섞인 긴 컨텍스트보다 정확한 짧은 컨텍스트가 낫다. 정보 검색의 precision이 모델 윈도우보다 중요.

### 6. Zero-Shot 0.83의 의미
RAGTruth로 훈련 안 했는데 훈련한 모델들과 동등. **"좋은 설계 > 많은 데이터"** 입증.

### 7. 데이터 전처리를 통한 고도화의 힌트
컨셉은 탁월하지만 작은 모델(~500M)로 구현한 실제 실행은 어중간. 파이프라인 성격이 강한데 고도화 여지가 많음. 하지만 **이런 컨셉이 있다는 인지** 자체가 향후 고도화 시 힌트.
