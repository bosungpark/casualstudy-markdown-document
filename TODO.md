### I. 백엔드 / 인프라

| 우선순위 | # | 제목 | 링크 | 핵심 주제 |
| :--- | :--- | :--- | :--- | :--- |
| **P1** | 2 | Dapper, a Large-Scale Distributed Systems Tracing Infrastructure | *New Addition* | **분산 시스템 추적 (Observability)** |
| **P2** | 3 | Paxos Made Simple | `https://lamport.azurewebsites.net/pubs/paxos-simple.pdf` | **분산 합의 (Paxos)** |
| **P2** | 4 | ZooKeeper: Wait-Free Coordination for Internet-Scale Systems | *New Addition* | **분산 코디네이션 서비스** |
| **P2** | 5 | Chubby: The Lock Service for Loosely-Coupled Distributed Systems | `https://static.googleusercontent.com/media/research.google.com/en//archive/chubby-osdi06.pdf` | **분산 락 서비스** |
| **P1** | 6 | The Tail at Scale | `https://www.usenix.org/legacy/event/hotpar09/tech/full_papers/Dean.pdf` | **대규모 분산 시스템의 지연 시간(Latency)** |
| **P2** | 7 | Consistent Hashing and Random Trees: Distributed Caching Protocols... | `https://people.csail.mit.edu/karger/Papers/web.pdf?utm_source=chatgpt.com` | **캐싱, 일관 해싱** |
| **P3** | 8 | Web Caching with Consistent Hashing | `https://www.cs.cmu.edu/~srini/15-744/S02/readings/K%2B99.html?utm_source=chatgpt.com` | **캐싱, 일관 해싱** (추가 분석) |
| **P1** | 9 | Effective Concurrency Testing for Go via Directional Primitive-constrained Interleaving Exploration | `https://chao-peng.github.io/publication/ase23/?utm_source=chatgpt.com` | **Golang 동시성 테스트** |
| **P2** | 10 | A Study of Real-World Data Races in Golang | `https://arxiv.org/abs/2204.00764?utm_source=chatgpt.com` | **Golang 데이터 경쟁(Data Race)** |
| **P3** | 11 | An Empirical Study of Messaging Passing Concurrency in Go Projects | `https://kar.kent.ac.uk/71491/?utm_source=chatgpt.com` | **Golang 메시지 전달 동시성** |
| **P3** | 12 | Hero: On the Chaos When PATH Meets Modules | `https://arxiv.org/abs/2102.12105?utm_source=chatgpt.com` | **Golang 모듈/의존성 관리 문제** |
| **P3** | 13 | Breaking Type Safety in Go: An Empirical Study on the Usage of the unsafe Package | `https://arxiv.org/abs/2006.09973?utm_source=chatgpt.com` | **Golang `unsafe` 패키지 분석** |
| **P3** | 14 | A Dictionary-Passing Translation of Featherweight Go | `https://arxiv.org/abs/2106.14586?utm_source=chatgpt.com` | **Golang 언어 설계 심층 분석** |
| **P3** | 15 | Consistent, highly throughput and space scalable distributed architecture for layered NoSQL data store | `https://www.nature.com/articles/s41598-025-03755-5?utm_source=chatgpt.com` | **NoSQL 분산 아키텍처** |

---

### II. 데이터

| 우선순위 | # | 제목 | 링크 | 핵심 주제 |
| :--- | :--- | :--- | :--- | :--- |
| **P1** | 16 | The Google File System (GFS) | `https://static.googleusercontent.com/media/research.google.com/ko//archive/gfs-sosp2003.pdf` | **분산 파일 시스템** |
| **P1** | 17 | Bigtable: A Distributed Storage System for Structured Data | `https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf` | **분산 키-값 저장소** |
| **P1** | 18 | Dynamo: Amazon's Highly Available Key-value Store | `https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf` | **고가용성 분산 키-값 저장소** |
| **P1** | 19 | Spanner: Google's Globally-Distributed Database | `https://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi14.pdf` | **글로벌 분산 데이터베이스** |
| **P1** | 20 | The Log: What Every Software Engineer Should Know About Real-time Data's Unifying Abstraction | `https://engineering.linkedin.com/sites/default/files/papers/the-log-what-every-software-engineer-should-know-about-real-time-data-unifying-abstraction-2011.pdf` | **로그 기반 데이터 스트리밍** |
| **P2** | 21 | Dataflow: A Unified Model for Stream and Batch Processing | *New Addition* | **통합 스트림/배치 처리 모델** |
| **P2** | 22 | Consistency models in distributed systems: A survey on definitions, disciplines, challenges and applications | `https://arxiv.org/abs/1902.03305?utm_source=chatgpt.com` | **분산 시스템 일관성 모델 (Survey)** |
| **P3** | 23 | MapReduce: Simplified Data Processing on Large Clusters | `https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf` | **데이터 처리 (MapReduce)** |
| **P3** | 24 | DHT-based Communications Survey: Architectures and Use Cases | `https://arxiv.org/abs/2109.10787?utm_source=chatgpt.com` | **DHT(분산 해시 테이블) 아키텍처** |
| **P3** | 25 | Odysseus/DFS: Integration of DBMS and Distributed File System for Transaction Processing of Big Data | `https://arxiv.org/abs/1406.0435?utm_source=chatgpt.com` | **DBMS와 분산 파일 시스템 통합** |

---

### III. AI / MLOps

| 우선순위 | # | 제목 | 링크 | 핵심 주제 |
| :--- | :--- | :--- | :--- | :--- |
| **P1** | 26 | Hidden Technical Debt in Machine Learning Systems | *New Addition* | **MLOps 아키텍처의 기술 부채 (Classic)** |
| **P1** | 27 | TFX: A TensorFlow-Based Production Machine Learning Platform | *New Addition* | **MLOps 파이프라인 시스템 설계** |
| **P2** | 28 | Evaluation-Driven Development and Operations of LLM Agents (EDDOps) | `https://arxiv.org/html/2411.13768v3` | **LLM 에이전트 개발 및 운영 (EDDOps)** |
| **P1** | 29 | Safeguarding Large Language Models: A Survey | `https://arxiv.org/abs/2406.02622` | **LLM 보호 (Safeguard) 종합 연구** |
| **P2** | 30 | Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations | `https://arxiv.org/pdf/2312.06674` | **LLM 기반의 입출력 보호 (Llama Guard)** |
| **P2** | 31 | SoK: Evaluating Jailbreak Guardrails for Large Language Models | `https://arxiv.org/abs/2506.10597` | **LLM 탈옥(Jailbreak) 방어 전략 평가** |
| **P3** | 32 | The need for guardrails with large language models in high-risk contexts | `https://www.nature.com/articles/s41598-025-09138-0` | **고위험 환경 LLM 가드레일 필요성** |
| **P3** | 33 | Beyond Linear Probes: Dynamic Safety Monitoring for Language Models | `https://arxiv.org/abs/2509.26238` | **LLM 동적 안전 모니터링** |
| **P3** | 34 | Architecting software monitors for control-flow anomaly detection through LLMs and conformance checking | `https://arxiv.org/abs/2511.10876` | **LLM을 통한 소프트웨어 모니터링 아키텍처** |
| **P3** | 35 | GuardReasoner: Towards Reasoning-based LLM Safeguards | `https://arxiv.org/abs/2501.18492` | **추론 기반 LLM 안전장치** |
| **P3** | 36 | MoJE: Mixture of Jailbreak Experts, Naive Tabular Classifiers as Guard for Prompt Attacks | `https://arxiv.org/abs/2409.17699` | **프롬프트 공격 방어를 위한 전문가 혼합 모델** |
| **P2** | 37 | Small Agent Can Also Rock! Empowering Small Language Models as Hallucination Detector (HaluAgent) | `https://arxiv.org/abs/2406.11277?utm_source=chatgpt.com` | **소형 LLM 기반 환각 탐지** |
| **P3** | 38 | Light-Weight Hallucination Detection using Contrastive Learning | `https://aclanthology.org/2025.acl-srw.44.pdf?utm_source=chatgpt.com` | **대조 학습을 이용한 경량 환각 탐지** |
| **P3** | 39 | Can a Small Model Learn to Look Before It Leaps? Dynamic Learning and Proactive Correction for Hallucination Detection | `https://arxiv.org/abs/2511.05854?utm_source=chatgpt.com` | **소형 모델을 이용한 동적 환각 탐지 및 교정** |
| **P3** | 40 | LLM-Check / Studies on Using Multiple Evaluators (LLMs) as Judges | `https://openreview.net/pdf?id=LYx4w3CAgy&utm_source=chatgpt.com` | **다중 LLM 평가자 사용 연구** |