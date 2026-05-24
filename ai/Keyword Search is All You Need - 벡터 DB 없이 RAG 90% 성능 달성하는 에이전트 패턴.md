# Keyword Search is All You Need - 벡터 DB 없이 RAG 90% 성능 달성하는 에이전트 패턴

## 출처
- **논문**: Keyword search is all you need: Achieving RAG-Level Performance without vector databases using agentic tool use
- **저자**: Shreyas Subramanian, Adewale Akinfaderin, Yanyan Zhang, Ishan Singh, Mani Khanuja, Sandeep Singh, Maira Ladeira Tanke (Amazon Science)
- **링크**: https://arxiv.org/abs/2602.23368
- **참고**: [arXiv HTML 버전](https://arxiv.org/html/2602.23368v1), [Amazon Science 발표 페이지](https://www.amazon.science/publications/keyword-search-is-all-you-need-achieving-rag-level-performance-without-vector-databases-using-agentic-tool-use)
- **분야**: cs.IR / cs.AI

---

## AI 요약

### 1. 핵심 질문

> "Do vector databases and semantic search provide enough additional value over simple keyword-search agents for document QA?"

저자들은 "벡터 DB + 시맨틱 검색"이 RAG의 필수 인프라처럼 자리잡았지만, 실제로 **단순 키워드 검색 + 에이전트 추론** 조합이 얼마나 비슷한 성능을 낼 수 있는지 정면으로 측정한다.

| 차원 | 전통 RAG | 본 논문의 Agentic Approach |
|------|---------|---------------------------|
| **검색 메커니즘** | 임베딩 + 벡터 유사도 | `rga`, `pdfgrep` 등 키워드 검색 |
| **인덱싱** | 오프라인 청킹 + 임베딩 + Vector DB | 없음 (파일 직접 검색) |
| **검색 횟수** | 1회 top-k | 다회 반복(ReAct 루프) |
| **응답 결정 시점** | 사전 (정적) | 런타임 (동적) |
| **업데이트 비용** | 재청킹 + 재임베딩 + 재인덱싱 | 0 (파일만 바뀌면 끝) |

---

### 2. 왜 키워드 검색 + 에이전트인가

기존 RAG의 비용 구조:
- **인프라**: 벡터 DB 호스팅, 임베딩 모델 호출 비용
- **운영**: 재인덱싱, 청킹 전략 튜닝, 임베딩 모델 업그레이드 시 전면 재구축
- **취약점**: top-k에 떨어진 evidence는 복구 불가, 어휘 미스매치에 약함

저자 주장:
> "Agents using simple keyword search tools can attain over 90% of the performance metrics of vector-based RAG implementations."

→ 인프라 부담 0에 가까운 대안이 실재한다.

---

### 3. 아키텍처 - 에이전트가 쓰는 도구들

```
┌───────────────────────────────────────────────────┐
│         Claude 3 Sonnet (200K, temp=0.001)        │
│  ┌──────────────────────────────────────────────┐ │
│  │   ReAct Loop                                  │ │
│  │   Reason → Act (tool) → Observe → Reason ...  │ │
│  └──────────────────────────────────────────────┘ │
└─────────────────────┬─────────────────────────────┘
                      │ tool calls (LangChain shell tool)
                      ▼
       ┌──────────────────────────────────┐
       │   Tool Inventory                  │
       │  ┌───────────────────────────┐    │
       │  │ pdfmetadata.sh            │    │
       │  │  → 폴더 내 PDF 메타데이터 │    │
       │  │  → "어디부터 찾을지" 정찰 │    │
       │  └───────────────────────────┘    │
       │  ┌───────────────────────────┐    │
       │  │ rga (ripgrep-all)         │    │
       │  │  → 정규식 다중 키워드     │    │
       │  │  → 'kw1|kw2|kw3' OR 검색  │    │
       │  └───────────────────────────┘    │
       │  ┌───────────────────────────┐    │
       │  │ pdfgrep                   │    │
       │  │  → PDF 특화 페이지 범위   │    │
       │  │  → --page-range 1-4 -P -r │    │
       │  └───────────────────────────┘    │
       └──────────────────┬───────────────┘
                          ▼
       ┌──────────────────────────────────┐
       │   Raw PDFs (no index, no embed)  │
       └──────────────────────────────────┘
```

### 3.1 ReAct 알고리즘 (단순화)

```
1. pdfmetadata.sh 실행 → 어떤 파일들이 있는지 정찰
2. while t < t_max:
     - 직전 관찰 보기
     - rga / pdfgrep 명령 작성
     - 셸에서 실행
     - 결과 보고 분기:
         · 더 좁힐 필요 → 새 명령
         · 답 발견 → 종료
         · 헛탕 → 패턴 수정 재시도
3. 최종 답변 반환
```

핵심은 **"점진적 맥락 확장(successive context expansion)"** — 한 번에 정답을 안 찾고, 검색 → 부분 정보 → 검색어 정제 → 다음 검색을 반복한다.

---

### 4. 실험 셋업

#### 4.1 데이터셋 (6개 도메인)

| 데이터셋 | 특징 |
|---------|------|
| PaulGrahamEssay | 에세이, 비선형적 논증 |
| Llama2Paper | LLM 기술 논문 |
| HistoryOfAlexnet | CNN 발전사 (학술) |
| BlockchainSolana | 화이트페이퍼 |
| LLM Survey | 종합 서베이 논문 |
| FinanceBench | 10-K, 10-Q, 8-K 공시 (2015-2023, 복수 기업) |

#### 4.2 Baseline RAG 구성

- **플랫폼**: Amazon Bedrock
- **임베딩**: Titan Text Embedding V2 (1024차원)
- **청킹**: 300 토큰, 20% 오버랩
- **Vector DB**: OpenSearch Serverless
- **top-k**: 5
- **생성**: Claude 3 Sonnet (양쪽 동일)

#### 4.3 평가 메트릭 (RAGAS)

1. **Faithfulness** — 답변이 검색된 근거에 충실한가
2. **Context Recall** — 답에 필요한 모든 관련 청크를 회수했는가
3. **Answer Correctness** — 정답 대비 정확도

---

### 5. 핵심 결과

#### 5.1 종합 성과 (vs RAG 기준선 대비 달성률)

| 메트릭 | 에이전트 달성률 |
|--------|----------------|
| **Faithfulness 평균** | **94.52%** |
| **Context Recall 평균** | **88.05%** |
| **Answer Correctness 평균** | **91.48%** |

> 즉, "벡터 DB 없이도 RAG의 ~90% 성능을 거의 모든 지표에서 달성".

#### 5.2 데이터셋별 빛과 그림자

| 데이터셋 | Context Recall | Answer Correctness | 평가 |
|---------|---------------|---------------------|------|
| BlockchainSolana | **99.62%** | **99.97%** | 키워드 매칭이 완벽히 들어맞는 구조 |
| LLM Survey | 98.71% | 99.51% | 명확한 용어/정의 중심 |
| Llama2Paper | **70.56%** | — | 기술 논문의 밀집·상호참조 구조에 약함 |
| PaulGrahamEssay | — | **79.91%** | 논증적·함축적 의미에 약함 |

#### 5.3 FinanceBench — 에이전트가 RAG를 **이기는** 사례

| 시스템 | Answer Correctness |
|--------|---------------------|
| 전통 RAG | 24.24% |
| 에이전트 (평균 3회) | 32.71% |
| 에이전트 (4회차) | **39.64%** |

> 복잡한 표·섹션 상호참조가 많은 재무 공시에선 **에이전트가 +8~15pp 우위**. 정적 청크 기반 검색이 표 구조에 약하기 때문.

---

### 6. 분석 — 언제 에이전트가 이기고 언제 지는가

#### 에이전트 우위
- **구조화된/기술 문서**: 명확한 용어, 선형 논리
- **표·이미지 다수**: 정적 청킹이 표를 끊어버림
- **재무 공시, 코드 문서**: 정확한 lexical 매칭이 중요

#### RAG 우위
- **에세이, 의견 글**: 키워드보다 의미적 유사도가 강함
- **밀집된 기술 논문**: 한 번에 여러 섹션 묶어 가져와야 할 때
- **paraphrase 많은 코퍼스**: 어휘 다양성에 임베딩이 강함

#### 패턴 한 줄 요약
> "관계적 검색이 필요한 콘텐츠는 RAG가 유리, 구조적/lexical 검색이 필요한 콘텐츠는 에이전트가 유리."

---

### 7. 한계점

| 한계 | 설명 |
|------|------|
| Context Recall 88% | RAG에 비해 회수율이 다소 낮음 |
| 대용량 문서 | 200K 컨텍스트도 한계에 도달 가능 |
| 멀티미디어 | 이미지/표 복잡 구조 처리 미흡 |
| 모호한 쿼리 | 명확한 키워드가 없는 질문에 약함 |
| API 신뢰성 | 호출 간 간헐적 실패 |
| 누적 학습 부재 | 쿼리 간 지식 보유 불가 |

---

### 8. 핵심 인용

> "Tool-augmented LLM agents using simple keyword search tools can attain over 90% of the performance metrics of vector-based RAG implementations."

> "Agent demonstrated strong performance, achieving an average attainment score of 94.52% across all datasets [for Faithfulness]."

> "This approach is simple to implement, cost effective, and is particularly useful in scenarios requiring frequent updates to knowledge bases."

---

## 내가 얻은 인사이트

### RAG 인프라 관점

1. **벡터 DB는 "필수"가 아니라 "선택"으로 격하**
   - 기업이 RAG를 도입할 때 가장 먼저 사는 게 벡터 DB지만, 이 논문은 그 결정을 처음부터 다시 묻게 만든다. 90% 성능을 0% 인프라 비용으로 얻을 수 있다면, 벡터 DB는 *남은 10%를 위해 정말 필요한가*를 검증한 뒤에 사야 한다.

2. **재인덱싱 비용은 숨어있던 거대한 운영 부담**
   - 임베딩 모델이 업그레이드되거나, 청킹 전략을 바꾸거나, 문서가 갱신될 때마다 전면 재구축이 필요하다. 키워드 + grep은 이 비용 자체가 존재하지 않는다 — 사내 문서·코드처럼 매일 변하는 코퍼스에서 결정적인 이점.

### 검색 시스템 설계 관점

1. **"단일 호출 retriever"라는 가정의 붕괴**
   - 기존 RAG는 "한 번 검색 → 끝"이지만, 에이전트는 **검색을 reasoning loop의 일부로 통합**한다. 결국 retriever 자체가 LLM의 일부가 되는 셈이며, retriever 품질은 LLM의 도구 사용 능력과 강결합된다.

2. **결과 분포는 "코퍼스의 성격"이 결정**
   - 같은 에이전트가 BlockchainSolana에서 99.97%, PaulGrahamEssay에서 79.91%. 즉, "에이전트 vs RAG"는 도메인 특이적 결정이며, 단일 정답이 없다. 실무 함의: **도메인별 A/B 테스트가 필수**.

3. **FinanceBench의 +8pp 우위는 의미가 크다**
   - 재무 공시는 RAG가 가장 어려워하는 영역 중 하나 — 표, 부록 참조, 섹션 cross-link. 여기서 에이전트가 이긴다는 건 *정적 청킹의 근본 한계*를 보여준다. "에이전트가 표를 동적으로 다시 본다"는 능력은 정적 검색으론 불가능.

### 실무 적용 관점

1. **하이브리드의 자연스러운 출발점**
   - 작은~중간 코퍼스: 키워드 + 에이전트만으로 시작 → 부족함이 측정되면 그때 벡터 DB 추가. 반대 순서로 하면 매몰 비용 때문에 절대 되돌아오지 못한다.

2. **도구 설계가 진짜 IP**
   - 이 논문의 비밀 소스는 LLM이 아니라 `pdfmetadata.sh + rga + pdfgrep` 조합이다. 도메인에 맞는 좋은 CLI 도구가 있으면 에이전트는 강해지고, 없으면 약해진다. 즉, **에이전트 시대의 retrieval 엔지니어링은 도구 설계로 이동**.

3. **Sonnet 4.5/Claude Code의 디자인이 학계로 역수렴**
   - Claude Code가 `grep`, `glob`, `read`로 거대 코드베이스를 다룬 패턴이, 일반 문서 QA에서도 똑같이 통한다는 실증. "코드 에이전트의 도구 사용 패턴 = 일반 RAG의 미래"라는 가설을 뒷받침.

### 학습된 직관

1. **"단순한 것이 일찍, 정교한 것이 늦게"**
   - 90%를 키워드로 얻고 남은 10%를 임베딩으로 메우는 게, 처음부터 100%를 임베딩으로 시도하는 것보다 거의 항상 싸고 안정적이다. 시스템 설계의 일반 원리.

2. **"Recall은 키워드가 약해도, Faithfulness는 강하다"**
   - 흥미로운 발견: Faithfulness(94.5%)가 Context Recall(88%)보다 높다. 즉, *찾아낸 정보엔 충실하지만, 찾아내야 할 걸 모두 회수하진 못한다*. 환각보다 누락이 위험인 시스템이라는 뜻 — 사용처에 따라 이게 더 안전할 수 있다.
