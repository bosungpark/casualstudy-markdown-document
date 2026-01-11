# The State of AI 2025 (Bessemer Venture Partners)

## 출처
- **링크**: https://www.bvp.com/atlas/the-state-of-ai-2025
- **저자**: BVP 파트너 13명 (Kent Bennett, Talia Goldberg, Janelle Teng 등)
- **발표일**: 2025년 8월 13일
- **형식**: AI 산업 종합 보고서 (Roadmap + Prediction)

---

## AI 요약

### 보고서 핵심 메시지

**"There is no cloud without AI anymore."**

2023년이 AI Big Bang이었다면, 2025년은 "First Light" - 초기 은하계가 형성되는 시점. BVP는 이미 $1B 이상을 AI 스타트업에 투자했으며, 레거시 SaaS 기업들도 모두 AI를 제품에 통합 중.

---

### Part 1: AI 벤치마크 - 두 가지 유형의 성공

**1. AI Supernovas (폭발적 성장)**
```
Year 1 ARR: $40M
Year 2 ARR: $125M

특징:
- Gross Margin: ~25% (심지어 마이너스)
- ARR/FTE: $1.13M (SaaS 대비 4-5배)
- 대표 기업: Perplexity, Cursor

리스크:
- "Thin wrapper" 우려
- 낮은 Switching cost
- 경쟁 과열
```

**2. AI Shooting Stars (건강한 성장)**
```
Year 1: $3M ARR
Year 2: $12M ARR → 4배 성장
Year 3: $40M ARR → 3.3배 성장
Year 4: $103M ARR → 2.6배 성장

특징:
- Gross Margin: 60%
- ARR/FTE: $164K
- 대표 기업: Abridge, EvenUp

새로운 벤치마크: Q2T3 (Quadruple, Quadruple, Triple, Triple, Triple)
→ SaaS의 T2D3보다 빠름
```

**BVP의 결론**:
> "While we love Supernovas, we believe this era will be defined not by a few outliers—but by hundreds of Shooting Stars."

---

### Part 2: 산업별 Roadmap

**I. AI Infrastructure**

**형성된 은하계**:
- Model layer: OpenAI, Anthropic, Gemini, Llama, xAI 주도
- Open-source 약진: DeepSeek, Qwen, Mixtral
- 연구 혁신: Mixture-of-Recursion, Test-time RL

**AI Infrastructure's Second Act**:
> "The second half of AI will shift focus from solving problems to **defining them**."

새로운 인프라 레이어:
1. **RL Environments**: Fleet, Matrices, Mechanize (라벨링 데이터 한계 극복)
2. **Novel Evaluation**: Bigspin.ai, Kiln AI, Judgment Labs
3. **Compound AI Systems**: 단순 모델 성능 넘어 지식 검색, 메모리, 추론 최적화

**Dark Matter (미해결 영역)**:
- "Bitter Lesson" 재현 가능성
- 어떤 기술이 실제 확장 가능할지 불명확

---

**II. Developer Platforms**

**형성된 은하계**:
- **Software 3.0**: "Prompts are programs, LLMs are computers"
- **Model Context Protocol (MCP)**: AI의 USB-C
  - Anthropic 주도, OpenAI/Google/MS 채택
  - 에이전트가 외부 API, 도구, 실시간 데이터 접근
  - 생태계: FastMCP (Prefect), Arcade, Keycard

**Dark Matter**:
- **Memory & Context**: 가장 중요한 미해결 과제

```
Memory 스택 구조 (예상):
├─ Short-term: 128k - 1M+ token context window
├─ Long-term: Vector DB, MemOS, MCP orchestration
└─ Semantic: Hybrid RAG, Episodic modules

문제:
- Long context → Latency ↑, Cost ↑
- Persistent memory → Brittle without context engineering
```

**Memory = 새로운 해자(Moat)**:
> "When your product understands a user's world better than anything else, replacing it feels like starting over."

예시:
- 팀 코드베이스에 능통한 코딩 어시스턴트
- CRM/커뮤니케이션에 내장된 세일즈 에이전트

→ **축적된 인텔리전스가 가장 강력한 Lock-in**

---

**III. Horizontal and Enterprise AI**

**형성된 은하계**: 
**Systems of Record → Systems of Action**

기존 SoR (Salesforce, SAP, Oracle, ServiceNow)의 해자 약화:
```
AI 이전:
- 마이그레이션 비용: 수백만 달러, 수년 소요
- 전환 비용(Switching cost) 극도로 높음

AI 이후:
- 구현 속도: 90% 더 빠름 (Codegen)
- 데이터 마이그레이션: 1일 (Schema 자동 번역)
- ROI: Legacy 대비 10배
```

**AI-native CRM/HR/ERP 사례**:
- CRM: Day.ai, Attio (이메일/전화/Slack 자동 로깅)
- ERP: Everest, Doss, Rillet (재무 예측, 조달 자동화)
- HR/Recruiting: AI 후보자 스크리닝
- Enterprise Search: SharePoint/Notion 대체

**전략**: "AI Trojan Horse"
```
1단계: AI 기능으로 침투 (Wedge)
2단계: 데이터 축적
3단계: Legacy SoR과 공존하면서 확장
4단계: 완전한 SoR 교체

예시:
- Tradespace (IP management)
- Serval (ITSM)
```

**Dark Matter**:
- Enterprise급 ERP 교체는 여전히 수년 소요
- Long tail SoR (IAM, CAD, CMS 등) 교체는 10년 프로젝트

---

**IV. Vertical AI**

**BVP 핵심 논제** (2024년부터 유지):
> "Vertical AI has the potential to eclipse even the most successful legacy vertical SaaS markets."

**형성된 은하계**: Vertical Workflow Automation

성공 사례:
```
Healthcare:
- Abridge: 임상 기록 자동화 ($125M ARR 예상)
- SmarterDx: 병원 수익 복구 자동화
- OpenEvidence: 의학 문헌 검토 자동화

Legal:
- EvenUp: 법적 요구 패키지 생성 (수일 → 수분)
- Ivo: 계약 검토 자동화
- Legora: 법률 리서치, 검토, 초안 작성

Education:
- Brisk Teaching, MagicSchool: 채점, 과외, 콘텐츠 생성

Real Estate:
- EliseAI: 부동산 관리 자동화

Home Services:
- Hatch: AI CSR 팀
- Rilla: 대면 세일즈 대화 분석 (음성)
```

**성공 패턴**:
1. **Compelling Wedge**: Language-heavy/Multi-modal 문제 해결
   - 음성/오디오가 자주 등장 (Miraculous wedge)
2. **Context is Key**: 도메인 전문성, 통합, 데이터 해자
3. **Built for Value**: ROI가 Day 1부터 명확
   - 10배 생산성 향상 or 비용 절감

**Dark Matter**:
- Legacy SoR과의 관계 (통합 vs 경쟁)
- Incumbent 반격 가능성
- 지속 가능한 데이터 해자 구축 가능성

---

**V. Consumer AI**

**형성된 은하계**:

**1. General-purpose AI Assistants**
- ChatGPT: 600M WAU (Weekly Active Users)
- Gemini: 400M WAU
- 음성이 핵심 모달리티로 부상
- **Perplexity**: AI-native 검색의 Breakout
  - Comet (Agentic browser) 출시

**2. AI Creation Tools**
- App 개발: Create.xyz, Bolt, Lovable
- 음악: Suno, Udio
- 멀티미디어: Moonvalley, Runway, Black Forest Labs
- 이미지: FLORA, Visual Electric, ComfyUI, Krea

**3. Purpose-built Assistants**
- Mental Health: Rosebud (AI 저널), Finch (게임화된 자기관리)
- Character.AI: 감정적 AI의 메인스트림화
- Email/Calendar: 신뢰 문제로 채택 어려움

**Dark Matter**:
- **Travel**: 종합 여행 비서 (에이전트 인프라 부족)
- **Shopping**: 에이전트 기반 e-commerce (브라우징, 가격 비교, 체크아웃)

→ 누가 소유할 것인가? Browser? LLM? 새로운 Consumer Agent?

---

### Part 3: 2025년 Top 5 예측

**Prediction 1: 브라우저가 Agentic AI의 주요 인터페이스로 부상**

```
왜 브라우저인가?
- 음성보다 강력: Ambient, Contextual
- 기업/소비자 시스템에 깊게 통합
- Multi-step automation 가능
- 실시간 의사결정

차세대 AI 브라우저:
- Comet (Perplexity)
- Dia
- OpenAI, Google도 곧 출시 예정

→ "New browser wars begin!"
```

---

**Prediction 2: 2026년은 Generative Video의 해**

```
진화 과정:
2024: 이미지 생성 메인스트림
2025: 음성 AI 폭발 (Latency↓, Cost↓)
2026: 비디오 Breakout 예상

주요 모델:
- Google Veo 3
- Kling
- OpenAI Sora
- Moonvalley Marey
- Open-source 스택

미해결 질문:
- 대형 랩이 독점할 것인가?
- Open-source가 따라잡을 것인가?
- Real-time/Low-latency가 차별화 포인트인가?

IP 복잡성:
- 저작권, 규제 이슈 증가
- 메이저 스튜디오들의 소송 시작
- 책임감 있는 데이터 소싱, 로열티 구조 필요
```

---

**Prediction 3: Evals와 Data Lineage가 AI 제품 개발의 핵심 촉매제로 부상** ⭐

**현재 상황**:
```
문제:
- 공개 벤치마크(MMLU, GSM8K, HumanEval)로는 부족
- 실제 워크플로우, 컴플라이언스, 의사결정 맥락 반영 안 됨
- 기업들은 "성능"이 아니라 "신뢰"를 원함

해결책:
"AI evals will go private, grounded, and trusted"
```

**차세대 AI 측정 시대**:
```
특징:
1. Private, use-case-specific evals (자체 데이터 기반)
2. Business-grounded metrics:
   - Accuracy
   - Latency
   - Hallucination rates
   - Customer satisfaction
3. Continuous eval pipelines (프로덕션 통합)
4. Lineage & Interpretability (규제 산업 필수)
```

**핵심 인용구**:
> "Today's enterprises aren't just seeking performance; they're seeking **confidence**. And confidence requires trusted, reproducible evaluation frameworks tailored to their own data, users, and risk environments."

**기업 요구 변화**:
```
과거:
"이 모델 성능이 어때요?"

현재:
"우리 데이터에서 95% 정확도 증명 가능해요?"
"Hallucination rate가 2% 이하인가요?"
"HIPAA/금융 규제 준수 입증 가능해요?"
"배포 전에 Evidence 제공해주세요"

→ Evaluation이 Procurement 요건으로 변화
```

**주요 스타트업**:
```
Infrastructure:
- Braintrust: Eval harness, A/B testing
- LangChain: Eval 프레임워크
- Bigspin.ai: Agentic benchmarking
- Judgment Labs: Real-time feedback loops

Data Lineage:
- DataHub: 데이터 사용 추적, 컴플라이언스 검증

Product Development:
- Arklex: AI-native measurement
- Kiln AI: Feedback loops
- Pi Labs: 새로운 제품 개발 원칙
```

**LaunchDarkly 비유**:
> "Product development has always aspired to be data-driven and user-informed, with platforms like LaunchDarkly enabling experimentation and measurement. In the world of AI—where predictive versus deterministic user experience reign supreme, the very foundation of these product development principles has been rocked."

**창업자를 위한 조언**:
```
우선순위:
1. Multi-metric evals (정확도, Hallucination, 컴플라이언스)
2. Synthetic eval environments (에이전트 스트레스 테스트)
3. Logging, Retrieval, Feedback 시스템과 상호운용성
4. Model drift, Continuous update 지원

차별화 요소:
- Raw accuracy가 아니라
- "정확히 언제, 왜, 어떻게 작동하는지 아는 것"
```

**결론**:
> "As foundational model performance converges, **the real differentiator won't be raw accuracy—it'll be knowing exactly how, when, and why your model works in your environment.**"

---

**Prediction 4: AI-native Social Media Giant 등장 가능성**

```
역사적 패턴:
- PHP → Facebook
- Mobile Camera → Instagram
- Mobile Video → TikTok
- Generative AI → ???

가능성:
- AI 에이전트 기반 네트워크 (생일, 친구 업데이트 자동 관리)
- AI 인플루언서/클론 중심 세계
- Character.AI, Replika가 힌트

연료:
- 음성 상호작용
- Long-term memory
- 이미지/비디오 생성
```

---

**Prediction 5: Incumbent의 역습 - AI M&A 가속화**

```
현상:
- 2025-2026년 M&A 급증 예상
- Enterprise 거인들이 AI 능력 "구매"

대상:
1. Vertical AI 스타트업
   - 보험, 법률, 헬스케어, 물류, 금융
   - "Software vs Service" 경계 흐려짐

2. AI Infrastructure/Tooling
   - Model orchestration
   - Evaluation
   - Observability
   - Memory systems

창업자 조언:
- 전략적 관심 대비
- 강한 기술 해자, 고객 견인력 확보
- Acquirer의 로드맵 이해
```

---

### Part 4: 창업자를 위한 10가지 Takeaways

1. **두 가지 AI 스타트업 유형**: Supernova vs Shooting Star
2. **Memory와 Context가 새로운 해자**
3. **Systems of Action이 Systems of Record 대체**
4. **AI Wedge로 시작**: 좁은 고통 지점 해결 → 10배 가치 → 확장
5. **브라우저가 캔버스**: Agentic AI의 프로그래밍 가능 환경
6. **Private, Continuous Evaluation 필수**: 공개 벤치마크로는 부족
7. **구현 속도가 전략적 우위**: 온보딩 수개월 → 수시간
8. **Vertical AI가 새로운 SaaS**: "Technophobic" 산업도 빠르게 채택
9. **Incumbent가 깨어남**: 기술/데이터 해자 구축, M&A 대비
10. **Taste와 Judgment가 차별화**: 단순 속도 아닌 올바른 AI

---

## 내가 얻은 인사이트
