# The Illustrated Transformer

## 출처
- **문서**: The Illustrated Transformer
- **저자**: Jay Alammar
- **게재**: jalammar.github.io, 2018
- **원문**: https://jalammar.github.io/illustrated-transformer/
- **원 논문**: Attention is All You Need (Vaswani et al., 2017)

---

## AI 요약

### Transformer란?
- **2017년 Google이 발표한 혁명적인 신경망 아키텍처**
- RNN/LSTM 없이 오직 **Attention 메커니즘**만으로 시퀀스 데이터 처리
- 병렬 처리 가능 → 학습 속도 극적 향상
- 현대 LLM(GPT, BERT, T5 등)의 기반 기술

### 전체 구조: 인코더-디코더

```
입력 문장 (영어)
    ↓
[인코더 스택] (6층)
    ↓
[디코더 스택] (6층)
    ↓
출력 문장 (프랑스어)
```

**인코더**:
- Self-Attention 레이어: 입력 문장의 모든 단어를 동시에 참조
- Feed-Forward 신경망: 각 위치별로 독립적 처리

**디코더**:
- Self-Attention 레이어 (마스킹됨: 미래 단어 참조 불가)
- Encoder-Decoder Attention: 인코더 출력 참조
- Feed-Forward 신경망

### Self-Attention: 핵심 메커니즘

**문제 상황**:
```
"The animal didn't cross the street because it was too tired"
```
여기서 "it"이 무엇을 가리키는가? → "animal"

**Self-Attention 동작**:
1. 각 단어를 3개 벡터로 변환: **Query(Q), Key(K), Value(V)**
2. Query와 모든 Key의 유사도 계산 (내적)
3. 유사도를 정규화 (Softmax) → 가중치
4. 가중치를 Value에 곱해서 합산 → 최종 출력

**수식**:
```
Attention(Q, K, V) = softmax(QK^T / √d_k) × V
```

**직관적 이해**:
- Q (질문): "나는 누구를 봐야 하나?"
- K (열쇠): "나는 이런 의미를 가져!"
- V (값): "나의 실제 정보는 이거야"

### Self-Attention 계산 예시

```python
# 예: "Thinking Machines" 문장 처리

# 1단계: Q, K, V 벡터 생성
x1 = embedding("Thinking")
q1 = x1 @ W_Q  # Query
k1 = x1 @ W_K  # Key
v1 = x1 @ W_V  # Value

# 2단계: 점수 계산 (Thinking과 모든 단어 비교)
score_11 = q1 · k1  # Thinking vs Thinking
score_12 = q1 · k2  # Thinking vs Machines

# 3단계: 정규화
scores = [score_11, score_12] / √64  # √d_k로 나눔
weights = softmax(scores)  # [0.88, 0.12]

# 4단계: 가중 합
output = 0.88 × v1 + 0.12 × v2
```

### Multi-Head Attention: 다중 관점

**왜 필요한가?**
- 단일 Attention은 한 가지 관점만 제공
- 8개 헤드 → 8가지 다른 관점에서 문장 이해

**동작 방식**:
```
입력
 ↓
[Head 1] [Head 2] ... [Head 8]  ← 각각 독립적인 Q,K,V
 ↓        ↓            ↓
 z1       z2    ...    z8
 ↓________________________↓
         Concat + W_O
              ↓
          최종 출력
```

**예시**:
```
"The animal didn't cross the street because it was too tired"

Head 1: "it" → "animal" (88% 가중치)
Head 2: "it" → "tired" (76% 가중치)
```

### Positional Encoding: 단어 순서 표현

**문제**: Self-Attention은 단어 순서를 모름 (병렬 처리라서)

**해결**: 각 단어 임베딩에 위치 정보 추가
```python
# Sin/Cos 함수로 위치 인코딩 생성
PE(pos, 2i) = sin(pos / 10000^(2i/d))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d))

# 최종 입력
input = word_embedding + positional_encoding
```

**특징**:
- 상대적 거리 학습 가능
- 학습 중 본 적 없는 긴 문장도 처리 가능

### Residual Connection & Layer Normalization

**모든 서브레이어에 적용**:
```python
output = LayerNorm(x + SubLayer(x))
```

**효과**:
- Gradient Vanishing 방지
- 깊은 네트워크 학습 안정화
- 원본 정보 보존

### 디코더의 특수성

**1. Masked Self-Attention**:
```
"I am a student"를 생성할 때

위치 1 (I): 자기 자신만 참조
위치 2 (am): I, am만 참조
위치 3 (a): I, am, a만 참조
위치 4 (student): I, am, a, student 참조
```
→ 미래 단어 참조 방지 (학습 시 치팅 방지)

**2. Encoder-Decoder Attention**:
- Query: 디코더 출력
- Key, Value: 인코더 최종 출력
- 번역 시 원문 참조

### 학습 과정

**1. 순전파 (Forward)**:
```
입력: "merci"
출력 예측: [0.1, 0.7, 0.05, 0.15, 0.0, 0.0]
실제 정답: [0, 1, 0, 0, 0, 0]  ← "thanks"
```

**2. 손실 계산**:
- Cross-Entropy Loss 사용
- 예측 확률 분포 vs 정답 분포

**3. 역전파 (Backprop)**:
- 모든 가중치(W_Q, W_K, W_V, W_O 등) 업데이트

**4. 추론 (Inference)**:
- Greedy Decoding: 매 단계 가장 높은 확률 단어 선택
- Beam Search: 상위 k개 후보 유지, 전체 확률 최대화

### Transformer vs RNN/LSTM

| 특성 | RNN/LSTM | Transformer |
|------|----------|-------------|
| 처리 방식 | 순차적 (단어 하나씩) | 병렬 (모든 단어 동시) |
| 학습 속도 | 느림 | 매우 빠름 |
| 장거리 의존성 | 어려움 (vanishing gradient) | 쉬움 (direct connection) |
| 메모리 | O(n) | O(n²) (attention) |
| GPU 활용 | 제한적 | 최대 활용 |

### 실전 활용

**1. 기계 번역**:
```
입력: "I love you"
출력: "Je t'aime"
```

**2. 텍스트 요약**:
```
입력: 긴 뉴스 기사
출력: 3줄 요약
```

**3. 질의응답**:
```
문맥: "트랜스포머는 2017년 발표되었다"
질문: "트랜스포머는 언제 나왔나?"
답변: "2017년"
```

**4. 현대 LLM의 기반**:
- GPT: 디코더만 사용 (생성)
- BERT: 인코더만 사용 (이해)
- T5: 전체 Encoder-Decoder (범용)

### 주요 하이퍼파라미터 (원 논문)

```
d_model = 512        # 모델 차원
h = 8                # Attention 헤드 수
d_k = d_v = 64       # 헤드당 차원 (512/8)
d_ff = 2048          # Feed-Forward 은닉층
N = 6                # 인코더/디코더 층 수
dropout = 0.1
```

### Transformer의 한계

**1. 메모리/연산 복잡도**:
- Self-Attention: O(n²) → 긴 시퀀스에 불리
- 해결: Sparse Attention, Linformer 등 변형

**2. 위치 정보 제약**:
- Sinusoidal Encoding의 한계
- 해결: Learned Positional Encoding, RoPE 등

**3. 작은 데이터셋에서 과적합**:
- 파라미터가 많아 데이터 요구량 큼
- 해결: Pre-training + Fine-tuning

---

## 내가 얻은 인사이트

**1. "Attention is All You Need"의 진짜 의미**
RNN/LSTM 같은 순차 처리가 필수라는 고정관념을 깼다. Attention 메커니즘만으로도 문맥을 완벽히 이해할 수 있다는 증명이다. 이는 단순히 기술적 개선이 아니라, "어떻게 문장을 이해하는가"에 대한 패러다임 전환이었다.

**2. 병렬화가 가져온 혁명**
RNN은 "I → love → you"를 순차적으로 처리해야 했지만, Transformer는 세 단어를 동시에 본다. 이 차이가 학습 속도를 수십 배 향상시켰고, GPT-3 같은 초대형 모델 학습을 가능하게 했다. 알고리즘 혁신이 하드웨어(GPU) 활용을 극대화한 사례다.

**3. Self-Attention은 "문맥 이해"의 수학적 구현**
"it"이 "animal"을 가리킨다는 걸 인간은 직관적으로 안다. Self-Attention은 이를 Query-Key 내적으로 수치화했다. 모든 단어 쌍의 관계를 명시적으로 계산함으로써, 암묵적이었던 언어 이해를 명시적 연산으로 바꿨다. 이것이 현대 AI의 "이해"가 작동하는 방식이다.
