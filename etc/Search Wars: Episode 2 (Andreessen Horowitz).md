# Search Wars: Episode 2 (Andreessen Horowitz)

## 출처
- **링크**: https://a16z.com/search-wars-episode-2/
- **저자**: Jason Cui (Partner), Jennifer Li (GP), Sarah Wang (GP), Stephenie Zhang (Partner)
- **발표일**: 2025년 11월 13일
- **카테고리**: Infrastructure, AI

---

## AI 요약

### 핵심 메시지

**"We have a front row seat to a new search war"**

1996년 Yahoo vs Excite vs Inktomi 검색 전쟁이 다시 일어나고 있음. 하지만 이번엔 다르다:
- **인간이 아닌 에이전트**가 웹을 브라우징
- **제품이 아닌 API** 간 경쟁
- **30+ AI 검색 회사**가 난립

---

### Part 1: AI Search의 역사

**2023년 이전: ChatGPT의 한계**
```
문제:
- 인터넷 접근 불가
- 구식 정보 제공
- 환각(Hallucination) 빈번

재미있는 실수들:
- Matrix 캐릭터 이름 날조
- "통조림 정어리가 살아있나?" 잘못된 답변
- 프로그래밍 문서 접근 불가
```

**2023년: GPT Researcher의 등장**
```
혁신:
- 최초로 "Retrieval for Reasoning" 패러다임
- 웹 브라우징 + 검색 + 종합
- GitHub 20,000+ stars

→ Tavily 창업팀의 오픈소스 프로젝트
→ ChatGPT의 2024년 브라우징 기능 검증
```

**핵심 아키텍처 변화 2가지**:

1. **RAG (Retrieval-Augmented Generation)**
   - Static training weights 의존 탈피
   - Live, domain-specific, proprietary data 접근
   
2. **TTC (Test-Time Compute)**
   - Inference 시 추론 파워 할당
   - 반복적 검색, 검증, 계획 루프

→ **Static models → Dynamic reasoners**

**2025년: Microsoft Bing API 종료**
```
상징적 사건:
- Microsoft가 공개 Bing Search API 종료
- "Agent Builder"로 유도 (LLM + 검색 통합)

메시지:
"검색 API는 끝났다. 
 이제 에이전트 빌더 시대다."

결과:
→ 12개 AI 검색 스타트업 등장
```

---

### Part 2: AI-Native Search의 요구사항

**기존 웹 검색의 문제**:
```
Human-optimized (정확히는 Marketer-optimized):
- SEO 콘텐츠로 도배
- 광고 난무
- 불필요한 정보 과다

AI가 이걸 그대로 쓰면:
→ Garbage in, garbage out
→ LLM 잠재력의 "끔찍한 표현"
```

**AI-Native Search가 필요한 이유**:
```
목표:
- 정보가 가장 풍부한 텍스트 세그먼트 타겟팅
- Recency와 Length 명시적 제어
- LLM context window에 바로 삽입 가능
- 에이전틱 워크플로우에 즉시 활용

핵심:
"가장 유익한 텍스트 세그먼트를
 콘텐츠 길이와 실시간 신선도를 
 세밀하게 제어하며 제공"
```

---

### Part 3: 현재 플레이어 지형

**핵심 발견** (30+ 고객 인터뷰):
```
대부분의 조직은 Third-party 검색 제공자에 의존 예상

이유:
1. 웹 인덱스 유지 비용 너무 높음
2. 검색 인프라 기술적 복잡도
3. 엔지니어링 시간 = 핵심 제품 개선에 투자하는 게 나음

예외:
- Massive scale 운영하는 조직만 자체 구축
```

**플랫폼 vs 제품**:

**API 플랫폼 (대부분)**:
```
제공 기능:
- Ranked search (순위 검색)
- Web crawling (웹 크롤링)
- Page extraction (페이지 정보 추출)
- Deep research (심층 연구)

주요 플레이어:
1. Exa (https://exa.ai)
   - 144 H200 GPU 자체 운영
   - Neural database
   - Infrastructure-intensive 접근

2. Parallel (https://parallel.ai)
   - Large-scale index 유지
   - 매일 수백만 페이지 추가
   - Programmable search API
   - Token-efficient excerpts

3. Tavily (https://www.tavily.com)
   - Periodic crawling (compute 절약)
   - RL 모델로 재크롤링 시점 예측
   - 블로그: 재크롤링 불필요
   - e-Commerce: 시간당 업데이트

4. Valyu (https://www.valyu.ai)
   - Tavily와 유사 접근
   - 동적 사이트 우선 업데이트
```

**소비자 제품**:
```
1. ChatGPT Deep Research
   - 2025년 2월 공개
   
2. Seda (https://getseda.com)
   - Branching 기능
   - Result specification
   - 더 강력한 소비자 리서치

3. Exa Websets (https://websets.exa.ai)
   - End user가 API 통합 없이 사용
   - GTM 팀이 바로 Lead enrichment
   - Engineering loop-in 불필요
   - Trade-off: 유연성↓, 편의성↑
```

---

### Part 4: 고객 평가 방법 ⭐⭐⭐

**a16z의 핵심 발견**:

> **"Customers typically evaluate providers by benchmarking result quality, API performance, and cost. However, there's no standardized methodology."**

**평가 방법의 스펙트럼**:
```
Informal (비공식):
└─ 간단한 실험
└─ 몇 개 쿼리 테스트

Formal (공식):
└─ 내부 "시험 스타일" 벤치마크
└─ 특정 use case에 맞춘 평가
└─ Side-by-side 비교

공통점:
→ 표준화된 방법론 없음
→ 각 기업이 자체 평가 기준 개발
```

**Multi-provider 전략**:
```
패턴:
- 여러 제공자 동시 사용
- 속도용 제공자 A
- 복잡한 쿼리용 제공자 B
- Proprietary 쿼리용 제공자 C

목적:
- 데이터 완전성↑
- 도메인 커버리지↑
```

**평가 기준 3가지**:
```
1. Result Quality (결과 품질)
   - 정확도
   - 관련성
   - 신선도

2. API Performance (API 성능)
   - Latency
   - Throughput
   - Reliability

3. Cost (비용)
   - Per-query pricing
   - Volume discounts
   - Infrastructure overhead
```

---

### Part 5: 주요 Use Cases

**1. Deep Research (가장 중요)**

**정의**:
> "Agent's ability to conduct multi-step, open-ended research with both breadth and depth across the internet"

**가치**:
- 수시간 걸리는 작업을 수분 안에
- 인간이 발견 못했을 정보 발굴
- Multi-hop reasoning 필요

**OpenAI BrowseComp 벤치마크**:
```
난이도:
- 1,266 questions
- Multi-hop reasoning across scattered sources
- Creative query reformulation
- Time period별 맥락 종합

인간 전문가:
- 2시간 내 25%만 해결

실제 응용:
- 규제 서류 추적 (시간대별)
- 경쟁 인텔리전스 종합
- Multi-layer 기업 소유권 매핑
- Due diligence (놓친 디테일 하나가 결과 바꿈)

예시 제공자:
- Parallel Deep Research API
  → 리서치 리포트 생성
  → 시장 조사
```

**a16z 예측**:
> **"Deep research will become the dominant and most monetizable form of agentic search. Customers already demonstrate willingness to pay for high-quality research results."**

---

**2. CRM Enrichment (초기 킬러 유스케이스)**

```
기존 문제:
- Lead enrichment = 시간 소모적, 수동 작업
- 여러 소스에서 데이터 수집
- 정보 일관성 유지 어려움

AI 검색 솔루션:
- 관련 정보 자동 검색/수집
- 정기 업데이트로 신선도 유지
- Stitching across disparate sources
```

---

**3. Technical Documentation / Code Search**

```
필요성:
- 코딩 에이전트는 Live, 최신 문서 필요
- Framework/API/Syntax 빠르게 진화
- Static datasets → 빠르게 구식

해결책:
- Search API가 Live web sources 연결
- 항상 최신 정보 참조
- 커뮤니티 포럼에서 학습
- 새 라이브러리/프레임워크에 지속 적응
```

---

**4. Proactive, Personalized Recommendations**

```
활용:
- 실시간 맞춤 추천
- 지역 이벤트 제안
- 트렌딩 활동 추천
- User context + preferences 기반

특징:
- Continuously updated web data
- Proactive suggestions
- Personalized
```

---

### Part 6: 시장 현황 및 전망

**현재 상황 (30+ 고객 인터뷰 결과)**:

**제한적인 초기 차별화**:
```
대부분의 Top AI 검색 제공자들:
- 경쟁 요소: Speed, Pricing, Ease of integration
- 유사한 기능: Ranked search, Crawling, Extraction, Deep research

→ "Bounded early product differentiation"
```

**변화 조짐**:
```
일부 팀들이 차별화 시작:
- Especially in deep research
- "Stack rank" of providers constantly shifting

한 Enterprise 고객 언급:
"The space is one of the most exciting ones 
 that we're tracking closely as trade-offs 
 that various players have taken in their 
 approaches evolve into bigger differences over time."
```

**LLM-as-Search-API 경계 흐려짐**:
```
선택지 1: Raw search results → LLM filter
선택지 2: LLM이 이미 필터링한 결과 제공

→ 둘의 경계가 불분명해짐
```

**인덱싱 접근법 차이**:
```
Infrastructure-intensive (Exa):
└─ 144 H200 GPUs
└─ 전체 웹 고품질 재크롤링
└─ 비용↑, 품질↑

Compute-saving (Tavily, Valyu):
└─ Periodic crawling
└─ RL 모델로 재크롤링 최적화
└─ 비용↓, 선택적 업데이트

Trade-off:
Cost vs Accuracy vs Performance
```

---

### Part 7: a16z의 핵심 통찰

**검색의 재발명**:
```
30년간의 문제:
- Google 검색 = 광고와 SEO로 오염
- 관련 결과가 Sponsored links 아래 묻힘
- 팝업과 광고로 뒤덮인 웹사이트

AI 시대:
"Making search more accessible for agents 
 is another way of saying it's also getting 
 more accessible for humans."

→ 에이전트를 위한 검색 개선
  = 인간을 위한 검색 개선
```

**1996 vs 2025**:
```
1996년:
- 각 경쟁자 = 검색 제품 (Yahoo, Excite, AltaVista)
- 완전히 다른 접근 방식
- 느린 Best practices 확산

2025년:
- 경쟁자 = API 제공자
- 매우 빠른 반복
- SOTA AI search 빠르게 통합
- 엔지니어링 결정 훨씬 빠르게 수렴

이유:
- GitHub/X에서 오픈소스로 시작
- Research spread faster
- 무엇이 작동하는지 더 빨리 발견
```

**다수 제공자 생존 가능성**:
```
과거 웹 검색: 
- 단일 거인 (Google)

AI 검색:
- 여러 제공자 공존 가능
- 서로 다른 차원과 도메인에서 경쟁
- User-facing products에 embedded
```

---

## 내가 얻은 인사이트
