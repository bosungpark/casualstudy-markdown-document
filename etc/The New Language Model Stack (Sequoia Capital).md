# The New Language Model Stack (Sequoia Capital)

## 출처
- **링크**: https://sequoiacap.com/article/llm-stack-perspective/
- **저자**: Michelle Fradin, Lauren Reeder
- **발표일**: 2023년 6월 14일
- **조사 대상**: Sequoia 네트워크 33개 기업 (seed → 대기업)
- **조사 방법**: 2개월 전 + 1주일 전 인터뷰 (변화 속도 측정)

---

## AI 요약

### 연구 배경

**"ChatGPT unleashed a tidal wave of innovation with large language models (LLMs)"**

Sequoia가 자사 포트폴리오 33개사를 대상으로 실시한 **실증 연구**:
- AI 전략 수립 중인 기업들에게 인사이트 공유 목적
- 급변하는 시장에서 스냅샷 제공
- 2개월 간격 2차 조사로 변화 속도 측정

---

### 핵심 발견 8가지

### **Finding 1: 거의 모든 기업이 LLM 도입 중**

**적용 분야** (Sequoia 포트폴리오):
```
Code:
- Sourcegraph, Warp, Github

Data Science:
- Hex

Customer/Employee Support:
- Chatbots

전체 워크플로우 재설계:
- Visual Art: Midjourney
- Marketing: Hubspot, Attentive, Drift, Jasper, Copy, Writer
- Sales: Gong
- Contact Centers: Cresta
- Legal: Ironclad, Harvey
- Accounting: Pilot
- Productivity: Notion
- Data Engineering: dbt
- Search: Glean, Neeva
- Grocery: Instacart
- Payments: Klarna
- Travel: Airbnb

→ "These are just a few examples and they're only the beginning"
```

---

### **Finding 2: 새로운 스택의 핵심 레이어** ⭐⭐⭐

**채택률 통계** (33개사 대상):

| 레이어 | 채택률 | 세부 내용 |
|--------|--------|-----------|
| **Production 배포** | 65% (2개월 전 50%) | 나머지 35%는 실험 중 |
| **Foundation Model API** | 94% | OpenAI GPT 91%, Anthropic 15% (증가 추세) |
| **Retrieval (Vector DB)** | 88% | 핵심 스택으로 남을 것으로 전망 |
| **Orchestration (LangChain)** | 38% | 프로토타입 or 프로덕션, 지난 몇 달간 증가 |
| **Output Monitoring/Eval** | <10% ⚠️ | A/B test, cost, performance 모니터링 |
| **Custom Model Training** | 15% | 2개월 전 대비 "meaningful increase" |

**Sequoia의 핵심 Stack 다이어그램**:

![LLM Stack](첨부 이미지 참조)

```
계층 구조 (위→아래):

┌─────────────────────────────────────┐
│   Applications                      │
│   (Notion, Jasper, Harvey, etc.)    │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   Output Monitoring/Eval  ← 여기!   │
│   (Sub-10% adoption)                │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   Orchestration                     │
│   (LangChain - 38%)                 │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   Retrieval                         │
│   (Vector DB - 88%)                 │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│   Foundation Models                 │
│   (OpenAI, Anthropic - 94%)         │
└─────────────────────────────────────┘
```

**Sequoia의 예측**:
> "Sub-10% were looking for tools to monitor LLM outputs, cost, or performance and A/B test prompts. **We think interest in these areas may increase as more large companies and regulated industries adopt language models.**"

---

### **Finding 3: 커스터마이제이션 니즈**

**3가지 커스터마이제이션 방법**:

**1. Train from Scratch (최고 난이도)**
```
요구사항:
- Highly skilled ML scientists
- Lots of relevant data
- Training infrastructure
- Compute

예시:
- BloombergGPT (Hugging Face 사용)

전망:
- 오픈소스 개선으로 증가 예상
```

**2. Fine-tune (중간 난이도)**
```
방법:
- Pre-trained model weights 업데이트
- Proprietary/domain-specific data 추가 학습

문제:
- "Much harder than it sounds"
- Model drift
- "Breaking" other skills without warning

현재:
- Most companies에게 여전히 out of reach
- But changing quickly
```

**3. Retrieval (최저 난이도)** ⭐
```
방법:
1. Data → Embeddings
2. Store in Vector DB
3. Query → Search embeddings
4. Provide context to model

장점:
- Limited context window 해킹
- Less expensive
- Data freshness 해결 (ChatGPT는 2021년 9월까지만)
- Solo developer도 가능 (ML 학위 불필요)

채택 패턴:
- 대기업: Enterprise cloud provider
- 스타트업: Purpose-built vector DB
  (Pinecone, Weaviate, Chroma, Qdrant, Milvus)
```

**Context Window 진화**:
```
발표 당시 (2023년 6월):
- OpenAI: 16K로 확장
- Anthropic: 100K token 출시

함의:
"Foundational models and cloud databases 
 may embed retrieval directly into their services"
```

---

### **Finding 4: API Stack vs Custom Training Stack 융합**

**과거 인식**:
```
"LLM API 제공 = Custom training 감소"
```

**실제 관찰**:
```
"We're seeing the opposite"

- AI 관심 증가
- 오픈소스 가속화
→ More companies train/fine-tune own models

예시:
- Custom model 훈련 + Vector DB retrieval 병행
  (Data freshness 해결)
```

**스택 융합 예측**:
> "We think the LLM API and custom model stacks will increasingly converge over time."

---

### **Finding 5: Developer-Friendly 진화**

**핵심 변화**:
```
Before:
- ML teams only

After:
- All developers (Average developer)

이유:
- Language model APIs = Ready-made models
- No ML expertise required
```

**LangChain 사례**:
```
역할:
- Abstract away common problems
- Combine models into higher-level systems
- Chain multiple model calls
- Connect models to tools/data
- Build agents
- Avoid vendor lock-in (Switch models easily)

채택:
- Prototyping
- Production
```

---

### **Finding 6: Trustworthiness가 완전 채택의 전제조건** ⭐⭐⭐

**기업들이 원하는 것**:

```
Full adoption 전에 필요:
1. Data Privacy
2. Segregation
3. Security
4. Copyright
5. Output Monitoring ← 핵심!

특히 규제 산업 (Fintech, Healthcare):
- Errors/Hallucinations 경고/방지
- Discriminatory content 차단
- Dangerous content 차단
- Security vulnerabilities 방지
```

**Sequoia의 예측**:
> "Before fully unleashing LLMs in their applications, many companies want **better tools for handling data privacy, segregation, security, copyright, and monitoring model outputs.**"

**언급된 솔루션**:
```
Robust Intelligence:
- 고객: Paypal, Expedia 등
- Tackling privacy, security, monitoring challenges
```

**Data Privacy 혼란**:
```
많은 기업이 모름:
- ChatGPT Consumer: 학습에 사용됨 (Default)
- ChatGPT Business/API: 학습에 사용 안 됨

→ 정책 명확화 필요
→ Guardrails 구축 필요
→ 그 후 Another step change in adoption
```

---

### **Finding 7: Multi-modal 진화**

**현재**:
```
조합 사례:
- Text + Speech → Conversational chatbots
- Text + Voice → Video overdubbing
```

**미래 비전**:
> "A future of rich consumer and enterprise AI applications that combine text, speech/audio, and image/video generation to create more engaging user experiences and accomplish more complex tasks."

---

### **Finding 8: It's Still Early** ⭐

**현재 상황**:
```
Production: 65%
- 많은 것이 "relatively simple applications"

앞으로:
- More companies launch LLM apps
- New hurdles arise
- More opportunities for founders
```

**Sequoia 예측**:
> "The infrastructure layer will continue to evolve rapidly for the next several years. If only half the demos we see make it to production, we're in for an exciting ride ahead."

---

## Stack 상세 분석

### **Consensus Stack (확정된 레이어)**

```
High Confidence:
1. LLM APIs (94% 채택)
   → "Will remain a key pillar"

2. Retrieval Mechanisms (88% 채택)
   → "Would remain a key part of their stack"

3. Development Frameworks (38% 채택)
   → LangChain 등, 증가 추세

Medium Confidence:
4. Custom Model Training (15% 채택)
   → "Meaningful increase" from 2개월 전

Low Confidence:
5. Output Monitoring/Eval (<10% 채택)
   → "May increase" with enterprise adoption
```

### **미성숙 레이어 (Immature but Important)**

```
현재 <10% 채택:
- Output quality monitoring
- Cost monitoring
- Performance monitoring
- A/B testing prompts

Sequoia 전망:
"Interest in these areas may increase"

촉매:
- Large companies 채택
- Regulated industries 진입
```

---

## 내가 얻은 인사이트
