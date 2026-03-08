# I. AI Foundations (모델 구조 / 학습 원리 / 평가)

| 우선순위 | 제목                                                           | 링크                                                                                                       | 핵심 주제                    |
| ---- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ------------------------ |
| ★★★  | Attention Is All You Need                                    | [https://arxiv.org/abs/1706.03762](https://arxiv.org/abs/1706.03762)                                     | Transformer 아키텍처, Self-Attention |
| ★★★  | BERT: Pre-training of Deep Bidirectional Transformers        | [https://arxiv.org/abs/1810.04805](https://arxiv.org/abs/1810.04805)                                     | Bidirectional Pretraining, MLM |
| ★★★  | GPT-3: Language Models are Few-Shot Learners                 | [https://arxiv.org/abs/2005.14165](https://arxiv.org/abs/2005.14165)                                     | Few-Shot Learning, In-Context Learning |
| ★★☆  | Deep Residual Learning for Image Recognition (ResNet)        | [https://arxiv.org/abs/1512.03385](https://arxiv.org/abs/1512.03385)                                     | Residual Connection, Skip Connection |
| ★★☆  | Batch Normalization: Accelerating Deep Network Training      | [https://arxiv.org/abs/1502.03167](https://arxiv.org/abs/1502.03167)                                     | BatchNorm, Internal Covariate Shift |
| ★★☆  | Adam: A Method for Stochastic Optimization                   | [https://arxiv.org/abs/1412.6980](https://arxiv.org/abs/1412.6980)                                       | Adaptive Learning Rate, Momentum |
| ★★☆  | Dropout: A Simple Way to Prevent Neural Networks from Overfitting | [https://jmlr.org/papers/v15/srivastava14a.html](https://jmlr.org/papers/v15/srivastava14a.html)         | Regularization, Ensemble |
| ★★☆  | Model Cards for Model Reporting                              | [https://arxiv.org/pdf/1810.03993.pdf](https://arxiv.org/pdf/1810.03993.pdf)                             | 모델 문서화·투명성, 평가 표준화 |
| ★★☆  | On the Dangers of Stochastic Parrots                         | [https://dl.acm.org/doi/10.1145/3442188.3445922](https://dl.acm.org/doi/10.1145/3442188.3445922)         | LLM 윤리·데이터·환경비용 |

---

# II. MLOps / LLM Safety (운영 / 안전 / 가드레일)

| 우선순위 | 제목                                                           | 링크                                                                                                       | 핵심 주제                    |
| ---- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ------------------------ |
| ★★★  | Hidden Technical Debt in Machine Learning Systems            | [https://papers.neurips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf](https://papers.neurips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf) | ML 시스템 기술부채, 유지보수 |
| ★★★  | TFX: A TensorFlow-Based Production Machine Learning Platform | [https://www.tensorflow.org/tfx](https://www.tensorflow.org/tfx)                                         | MLOps 파이프라인              |
| ★★☆  | EDDOps: Evaluation-Driven Dev & Ops of LLM Agents            | [https://arxiv.org/html/2411.13768v3](https://arxiv.org/html/2411.13768v3)                               | LLM 에이전트 운영, 평가 기반 관측 |
| ★★☆  | Llama Guard                                                  | [https://arxiv.org/pdf/2312.06674](https://arxiv.org/pdf/2312.06674)                                     | LLM 입출력 안전 분류기 |
| ★★☆  | SoK: Evaluating Jailbreak Guardrails                         | [https://arxiv.org/abs/2506.10597](https://arxiv.org/abs/2506.10597)                                     | LLM Jailbreak 평가 체계 |
| ★☆☆  | Need for Guardrails in High-Risk Contexts                    | [https://www.nature.com/articles/s41598-025-09138-0](https://www.nature.com/articles/s41598-025-09138-0) | 고위험 LLM 가드레일 필요성 |
| ★☆☆  | Beyond Linear Probes                                         | [https://arxiv.org/abs/2509.26238](https://arxiv.org/abs/2509.26238)                                     | 동적 안전 모니터링 |
| ★☆☆  | Lightweight Hallucination Detection                          | [https://aclanthology.org/2025.acl-srw.44.pdf](https://aclanthology.org/2025.acl-srw.44.pdf)             | 경량 환각 탐지 |
| ★☆☆  | Small Model Dynamic Hallucination Detection                  | [https://arxiv.org/abs/2511.05854](https://arxiv.org/abs/2511.05854)                                     | 소형 모델 기반 환각 교정 |
| ★☆☆  | GuardReasoner                                                | [https://arxiv.org/abs/2501.18492](https://arxiv.org/abs/2501.18492)                                     | 추론 기반 가드레일 |
| ★☆☆  | MoJE                                                         | [https://arxiv.org/abs/2409.17699](https://arxiv.org/abs/2409.17699)                                     | Jailbreak Expert Mixture |

---

# III. System Design / Architecture

| 우선순위 | 제목                                   | 링크                                                                                                                                                       | 핵심 주제           |
| ---- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| ★★★  | The Tail at Scale                    | [https://research.google/pubs/the-tail-at-scale/](https://research.google/pubs/the-tail-at-scale/)                                                       | 대규모 시스템 Latency |
| ★★★  | Dapper: Distributed Systems Tracing  | [https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/) | Distributed Tracing, Observability |
| ★★★  | MapReduce: Simplified Data Processing | [https://research.google/pubs/pub62/](https://research.google/pubs/pub62/) | 분산 배치 처리 패턴 |
| ★★★  | Borg, Omega, and Kubernetes          | [https://queue.acm.org/detail.cfm?id=2898444](https://queue.acm.org/detail.cfm?id=2898444)                                                               | 컨테이너 오케스트레이션 |
| ★★☆  | Kafka: a Distributed Messaging System | [https://www.semanticscholar.org/paper/Kafka-%3A-a-Distributed-Messaging-System-for-Log-Kreps/ea97f112c165e4da1062c30812a41afca4dab628](https://www.semanticscholar.org/paper/Kafka-%3A-a-Distributed-Messaging-System-for-Log-Kreps/ea97f112c165e4da1062c30812a41afca4dab628) | 로그 기반 이벤트 스트리밍 |
| ★☆☆  | Google Cluster Management (Borg)      | [https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/](https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/) | 클러스터 스케줄링 |

---

# IV. Database (Storage / Consistency / Transactions)

| 우선순위 | 제목                                                                                       | 링크                                                                                                                                                                                                                                                                             | 핵심 주제                    |
| ---- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| ★★★  | Google File System (GFS)                                                                 | [https://static.googleusercontent.com/media/research.google.com/ko//archive/gfs-sosp2003.pdf](https://static.googleusercontent.com/media/research.google.com/ko//archive/gfs-sosp2003.pdf)                                                                                     | 분산 파일 시스템                |
| ★★★  | Bigtable: A Distributed Storage System                                                   | [https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf](https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf)                                                                               | 분산 저장소, SSTable          |
| ★★★  | Spanner: Google's Globally-Distributed Database                                          | [https://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi14.pdf](https://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi14.pdf)                                                                                 | 글로벌 분산 DB, TrueTime     |
| ★★★  | Dynamo: Amazon's Highly Available Key-value Store                                        | [https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)                                                                                                                                 | Eventually Consistent KV |
| ★★★  | The Log: What Every Engineer Should Know                                                 | [https://www.linkedin.com/pulse/log-what-every-software-engineer-should-know-unifying-abstraction-kreps/](https://www.linkedin.com/pulse/log-what-every-software-engineer-should-know-unifying-abstraction-kreps/)                                                             | 로그 기반 아키텍처               |
| ★★★  | The Log-Structured Merge-Tree (LSM-Tree)                                                 | [https://www.cs.umb.edu/~poneil/lsmtree.pdf](https://www.cs.umb.edu/~poneil/lsmtree.pdf)                                                                                                                                                                                       | LSM Tree, 쓰기 최적화         |
| ★★★  | ARIES: A Transaction Recovery Method                                                     | [https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf](https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf)                                                                                                                                                       | WAL, 복구 알고리즘             |
| ★★★  | Calvin: Deterministic Database Transactions                                              | [https://dl.acm.org/doi/10.1145/2387880.2387895](https://dl.acm.org/doi/10.1145/2387880.2387895)                                                                                                                                                                               | 결정적 분산 트랜잭션              |
| ★★☆  | The Design and Implementation of a Log-Structured File System                            | [https://people.eecs.berkeley.edu/~brewer/cs262/LFS.pdf](https://people.eecs.berkeley.edu/~brewer/cs262/LFS.pdf)                                                                                                                                                               | 로그 구조 스토리지               |
| ★★☆  | Dataflow: A Unified Model for Batch and Stream Processing                                | [https://research.google/pubs/dataflow-a-unified-model-for-batch-and-stream-processing/](https://research.google/pubs/dataflow-a-unified-model-for-batch-and-stream-processing/)                                                                                               | 스트림/배치 통합 처리            |
| ★★☆  | Consistency Models Survey                                                                | [https://arxiv.org/abs/1902.03305](https://arxiv.org/abs/1902.03305)                                                                                                                                                                                                           | 분산 일관성 모델                |
| ★★☆  | Online, Asynchronous Schema Change in F1                                                 | [https://research.google/pubs/pub41376/](https://research.google/pubs/pub41376/)                                                                                                                                                                                               | 온라인 스키마 변경               |
| ★★☆  | Frangipani: A Scalable Distributed File System                                           | [https://pdos.csail.mit.edu/6.824/papers/thekkath-frangipani.pdf](https://pdos.csail.mit.edu/6.824/papers/thekkath-frangipani.pdf)                                                                                                                                             | 분산 락 + FS                |
| ★★☆  | Granola: Low-Overhead Distributed Transaction Coordination                               | [https://www.usenix.org/conference/atc12/technical-sessions/presentation/cowling](https://www.usenix.org/conference/atc12/technical-sessions/presentation/cowling)                                                                                                             | 2PC 최적화                  |
| ★★☆  | Tango: Distributed Data Structures over a Shared Log                                     | [https://dl.acm.org/doi/10.1145/2517349.2522735](https://dl.acm.org/doi/10.1145/2517349.2522735)                                                                                                                                                                               | 로그 기반 트랜잭션               |
| ★★☆  | No Compromises: Distributed Transactions                                                 | [https://dl.acm.org/doi/10.1145/2815400.2815407](https://dl.acm.org/doi/10.1145/2815400.2815407)                                                                                                                                                                               | 트랜잭션 트레이드오프              |
| ★★☆  | Building Consistent Transactions with Inconsistent Replication                           | [https://dl.acm.org/doi/10.1145/2815400.2815417](https://dl.acm.org/doi/10.1145/2815400.2815417)                                                                                                                                                                               | 비일관 복제 트랜잭션              |
| ★☆☆  | Bitcask: A Log-Structured Hash Table                                                     | [https://riak.com/assets/bitcask-intro.pdf](https://riak.com/assets/bitcask-intro.pdf)                                                                                                                                                                                         | 로그 기반 KV                 |
| ★☆☆  | Odysseus/DFS                                                                             | [https://arxiv.org/abs/1406.0435](https://arxiv.org/abs/1406.0435)                                                                                                                                                                                                             | DB + DFS 통합              |
| ★☆☆  | Readings in Database Systems (Red Book)                                                  | [http://www.redbook.io](http://www.redbook.io)                                                                                                                                                                                                                                 | DB 고전 논문 모음              |

---

# V. Distributed Systems / Consensus

| 우선순위 | 제목                                  | 링크                                                                                                                                                       | 핵심 주제     |
| ---- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| ★★★  | Paxos Made Simple                   | [https://lamport.azurewebsites.net/pubs/paxos-simple.pdf](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf)                                       | 합의 알고리즘 |
| ★★★  | Raft: Understandable Consensus      | [https://raft.github.io/raft.pdf](https://raft.github.io/raft.pdf)                                                                                       | 합의 알고리즘 |
| ★★★  | Time, Clocks, and the Ordering of Events | [https://lamport.azurewebsites.net/pubs/time-clocks.pdf](https://lamport.azurewebsites.net/pubs/time-clocks.pdf) | Lamport Clock, 논리적 시간 |
| ★★☆  | Viewstamped Replication Revisited   | [https://pmg.csail.mit.edu/papers/vr-revisited.pdf](https://pmg.csail.mit.edu/papers/vr-revisited.pdf)                                                   | 합의·복제 알고리즘 |

---

# VI. Network / Protocol / Security

| 우선순위 | 제목                                                   | 링크                                                                                                                                       | 핵심 주제       |
| ---- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| ★★★  | A Note on Distributed Computing                      | [https://scholar.harvard.edu/files/waldo/files/waldo-94.pdf](https://scholar.harvard.edu/files/waldo/files/waldo-94.pdf)                 | 로컬 vs 원격 호출 차이 |
| ★★☆  | REST: Architectural Styles                           | [https://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm](https://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm)               | REST 원론 |
| ★★☆  | The C10K Problem                                     | [http://www.kegel.com/c10k.html](http://www.kegel.com/c10k.html)                                                                         | 대규모 동시 연결 |
| ★★☆  | QUIC: Multiplexed Streams over UDP                   | [https://www.rfc-editor.org/rfc/rfc9000](https://www.rfc-editor.org/rfc/rfc9000)                                                         | 현대적 전송 프로토콜 |
| ★★☆  | OWASP Top 10                                         | [https://owasp.org/www-project-top-ten/](https://owasp.org/www-project-top-ten/)                                                         | 웹 보안 취약점 |
| ★★☆  | Smashing the Stack for Fun and Profit                | [http://phrack.org/issues/49/14.html](http://phrack.org/issues/49/14.html)                                                               | 버퍼 오버플로우 |

---

# VII. Programming Languages / Concurrency

| 우선순위 | 제목                                         | 링크                                                                                                     | 핵심 주제       |
| ---- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ----------- |
| ★★★  | Communicating Sequential Processes (CSP)   | [https://www.cs.cmu.edu/~crary/654-f07/Hoare78.pdf](https://www.cs.cmu.edu/~crary/654-f07/Hoare78.pdf) | CSP 모델, Go 채널 기반 |
| ★★★  | Actor Model (Hewitt 1973)                  | [https://dl.acm.org/doi/10.1145/1624775.1624804](https://dl.acm.org/doi/10.1145/1624775.1624804)       | Actor Model, 메시지 전달 |
| ★★☆  | Gradual Typing for Functional Languages    | [http://scheme2006.cs.uchicago.edu/13-siek.pdf](http://scheme2006.cs.uchicago.edu/13-siek.pdf)         | 점진적 타이핑 이론 |
| ★★☆  | Uniprocessor Garbage Collection Techniques | [https://www.cs.rice.edu/~javaplt/311/Readings/wilson92uniprocessor.pdf](https://www.cs.rice.edu/~javaplt/311/Readings/wilson92uniprocessor.pdf) | GC 기법 총정리 |
| ★★☆  | A Study of Real-World Data Races in Golang | [https://arxiv.org/abs/2204.00764](https://arxiv.org/abs/2204.00764)                                   | Data Race 분석 |
| ★★☆  | Message Passing Concurrency in Go          | [https://kar.kent.ac.uk/71491](https://kar.kent.ac.uk/71491)                                           | Go 메시지 전달 |
| ★★☆  | Comparative Study via Rosetta Code         | [https://arxiv.org/abs/1409.0252](https://arxiv.org/abs/1409.0252)                                     | PL 비교 연구 |

---

# VIII. Data Science / Python Ecosystem

| 우선순위 | 제목                                         | 링크                                                                                                     | 핵심 주제       |
| ---- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ----------- |
| ★★★  | NumPy: Array Programming                   | [https://www.nature.com/articles/s41586-020-2649-2](https://www.nature.com/articles/s41586-020-2649-2) | NumPy 아키텍처, 벡터화 |
| ★★★  | pandas: A Foundational Python Library      | [https://conference.scipy.org/proceedings/scipy2010/pdfs/mckinney.pdf](https://conference.scipy.org/proceedings/scipy2010/pdfs/mckinney.pdf) | DataFrame 설계 철학 |
| ★★★  | Numba: A LLVM-based Python JIT Compiler    | [https://dl.acm.org/doi/10.1145/2833157.2833162](https://dl.acm.org/doi/10.1145/2833157.2833162)       | Python JIT 컴파일 |
| ★★☆  | Scikit-learn: Machine Learning in Python   | [https://jmlr.org/papers/v12/pedregosa11a.html](https://jmlr.org/papers/v12/pedregosa11a.html)         | API 설계, 파이프라인 |
| ★★☆  | PyTorch: Automatic Differentiation         | [https://openreview.net/pdf?id=BJJsrmfCZ](https://openreview.net/pdf?id=BJJsrmfCZ)                     | Autograd 메커니즘 |
| ★★☆  | TensorFlow: Large-Scale Machine Learning   | [https://www.usenix.org/system/files/conference/osdi16/osdi16-abadi.pdf](https://www.usenix.org/system/files/conference/osdi16/osdi16-abadi.pdf) | 연산 그래프, 분산 학습 |
| ★☆☆  | Parsl: Parallel Python                     | [https://arxiv.org/abs/1905.02158](https://arxiv.org/abs/1905.02158)                                   | Python 병렬처리 |

---

# IX. Testing / Observability

| 우선순위 | 제목                                         | 링크                                                                                                     | 핵심 주제       |
| ---- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ----------- |
| ★★★  | OpenTelemetry Specification                | [https://opentelemetry.io/docs/specs/](https://opentelemetry.io/docs/specs/)                           | Trace/Span/Attribute 표준 |
| ★★☆  | QuickCheck: Random Testing                 | [https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf](https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf) | Property-based Testing |
| ★★☆  | Deterministic Graph-Based Inference for Guardrailing LLMs | [https://rainbird.ai/wp-content/uploads/2025/03/Deterministic-Graph-Based-Inference-for-Guardrailing-Large-Language-Models.pdf](https://rainbird.ai/wp-content/uploads/2025/03/Deterministic-Graph-Based-Inference-for-Guardrailing-Large-Language-Models.pdf) | 가드레일 로직 설계 |
| ★☆☆  | APILogGuard: API Logging and Monitoring    | [https://www.jetir.org/papers/JETIR2504A31.pdf](https://www.jetir.org/papers/JETIR2504A31.pdf)         | API 이벤트 수집/모니터링 |
