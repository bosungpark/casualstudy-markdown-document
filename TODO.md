# I. AI / MLOps / LLM Safety

| 우선순위 | 제목                                                           | 링크                                                                                                       | 핵심 주제                    |
| ---- | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- | ------------------------ |
| ★★★  | TFX: A TensorFlow-Based Production Machine Learning Platform | [https://www.tensorflow.org/tfx](https://www.tensorflow.org/tfx)                                         | MLOps 파이프라인              |
| ★★☆  | EDDOps: Evaluation-Driven Dev & Ops of LLM Agents            | [https://arxiv.org/html/2411.13768v3](https://arxiv.org/html/2411.13768v3)                               | LLM 에이전트 운영              |
| ★★☆  | Llama Guard                                                  | [https://arxiv.org/pdf/2312.06674](https://arxiv.org/pdf/2312.06674)                                     | LLM 입출력 보호               |
| ★★☆  | SoK: Evaluating Jailbreak Guardrails                         | [https://arxiv.org/abs/2506.10597](https://arxiv.org/abs/2506.10597)                                     | LLM Jailbreak 평가         |
| ★☆☆  | Need for Guardrails in High-Risk Contexts                    | [https://www.nature.com/articles/s41598-025-09138-0](https://www.nature.com/articles/s41598-025-09138-0) | 고위험 LLM                  |
| ★☆☆  | Beyond Linear Probes                                         | [https://arxiv.org/abs/2509.26238](https://arxiv.org/abs/2509.26238)                                     | 동적 안전 모니터링               |
| ★☆☆  | Lightweight Hallucination Detection                          | [https://aclanthology.org/2025.acl-srw.44.pdf](https://aclanthology.org/2025.acl-srw.44.pdf)             | 경량 환각 탐지                 |
| ★☆☆  | Small Model Dynamic Hallucination Detection                  | [https://arxiv.org/abs/2511.05854](https://arxiv.org/abs/2511.05854)                                     | 소형 모델 기반 환각 교정           |
| ★☆☆  | GuardReasoner                                                | [https://arxiv.org/abs/2501.18492](https://arxiv.org/abs/2501.18492)                                     | 추론 기반 가드                 |
| ★☆☆  | MoJE                                                         | [https://arxiv.org/abs/2409.17699](https://arxiv.org/abs/2409.17699)                                     | Jailbreak Expert Mixture |
| ★☆☆  | LLM-based Software Control-flow Monitoring                   | [https://arxiv.org/abs/2511.10876](https://arxiv.org/abs/2511.10876)                                     | LLM 기반 모니터링              |
| ★★★  | Hidden Technical Debt in Machine Learning Systems                     | [https://papers.neurips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf](https://papers.neurips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf) | ML 시스템 설계·유지보수 관점 (MLOps 필수) . ([NeurIPS Papers][1]) |
| ★★☆  | Model Cards for Model Reporting                                       | [https://arxiv.org/pdf/1810.03993.pdf](https://arxiv.org/pdf/1810.03993.pdf)                                                                                                             | 모델 문서화·투명성(배포 전/후 평가·컴플라이언스) . ([arXiv][2])          |
| ★★☆  | On the Dangers of Stochastic Parrots: Can Language Models Be Too Big? | [https://dl.acm.org/doi/10.1145/3442188.3445922](https://dl.acm.org/doi/10.1145/3442188.3445922) (PDF 링크 포함). ([ACM Digital Library][3])                                                 | LLM 윤리·데이터·환경비용·안전성 고찰                               |

[1]: https://papers.neurips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf?utm_source=chatgpt.com "Hidden Technical Debt in Machine Learning Systems"
[2]: https://arxiv.org/pdf/1810.03993?utm_source=chatgpt.com "Model Cards for Model Reporting"
[3]: https://dl.acm.org/doi/10.1145/3442188.3445922?utm_source=chatgpt.com "On the Dangers of Stochastic Parrots"


---

# II. Architecture (System Design / Large-Scale Systems)

| 우선순위 | 제목                                   | 링크                                                                                                                                                                                                 | 핵심 주제           |
| ---- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| ★★★  | The Tail at Scale                    | [https://research.google/pubs/the-tail-at-scale/](https://research.google/pubs/the-tail-at-scale/)                                                                                                 | 대규모 시스템 Latency |
| ★★★  | Dapper: Distributed Systems Tracing  | [https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/)     | Observability   |
| ★★☆  | Chubby                               | [https://static.googleusercontent.com/media/research.google.com/en//archive/chubby-osdi06.pdf](https://static.googleusercontent.com/media/research.google.com/en//archive/chubby-osdi06.pdf)       | 분산 락            |
| ★★☆  | ZooKeeper                            | [https://www.usenix.org/legacy/event/usenix10/tech/full_papers/Hunt.pdf](https://www.usenix.org/legacy/event/usenix10/tech/full_papers/Hunt.pdf)                                                   | 분산 코디네이션        |
| ★☆☆  | MapReduce                            | [https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf](https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf) | 분산 데이터 처리       |
| ★☆☆  | The Datacenter as a Computer         | [https://www.morganclaypool.com/doi/abs/10.2200/S00293ED1V01Y200905CAC006](https://www.morganclaypool.com/doi/abs/10.2200/S00293ED1V01Y200905CAC006)                                               | 대규모 시스템 구조      |
| ★☆☆  | Google Cluster Data (Borg Precursor) | [https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/](https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/)                               | 클러스터 스케줄링       |
| ★★☆  | Kafka: a Distributed Messaging System for Log Processing | [https://www.semanticscholar.org/paper/Kafka-%3A-a-Distributed-Messaging-System-for-Log-Kreps/ea97f112c165e4da1062c30812a41afca4dab628](https://www.semanticscholar.org/paper/Kafka-%3A-a-Distributed-Messaging-System-for-Log-Kreps/ea97f112c165e4da1062c30812a41afca4dab628) (PDF/원문 다수). ([notes.stephenholiday.com][1]) | 로그 기반 데이터 파이프라인·이벤트 스트리밍 아키텍처                   |
| ★★☆  | Viewstamped Replication Revisited                        | [https://pmg.csail.mit.edu/papers/vr-revisited.pdf](https://pmg.csail.mit.edu/papers/vr-revisited.pdf)                                                                                                                                                                                                                      | 합의·복제(실무적 복구·가용성 설계) . ([pmg.csail.mit.edu][2]) |

[1]: https://notes.stephenholiday.com/Kafka.pdf?utm_source=chatgpt.com "Kafka: a Distributed Messaging System for Log Processing"
[2]: https://pmg.csail.mit.edu/papers/vr-revisited.pdf?utm_source=chatgpt.com "Viewstamped Replication Revisited"


---

# III. Database (Storage / Consistency / Transactions)

| 우선순위 | 제목                                       | 링크                                                                                                                                                                                                                 | 핵심 주제       |
| ---- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------- |
| ★★★  | Google File System (GFS)                 | [https://static.googleusercontent.com/media/research.google.com/ko//archive/gfs-sosp2003.pdf](https://static.googleusercontent.com/media/research.google.com/ko//archive/gfs-sosp2003.pdf)                         | 분산 파일 시스템   |
| ★★★  | Bigtable                                 | [https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf](https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf)                   | 분산 저장소      |
| ★★★  | Spanner                                  | [https://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi14.pdf](https://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi14.pdf)                     | 글로벌 DB      |
| ★★★  | The Log: What Every Engineer Should Know | [https://www.linkedin.com/pulse/log-what-every-software-engineer-should-know-unifying-abstraction-kreps/](https://www.linkedin.com/pulse/log-what-every-software-engineer-should-know-unifying-abstraction-kreps/) | 로그 기반 아키텍처  |
| ★★☆  | Dataflow                                 | [https://research.google/pubs/dataflow-a-unified-model-for-batch-and-stream-processing/](https://research.google/pubs/dataflow-a-unified-model-for-batch-and-stream-processing/)                                   | 스트림/배치      |
| ★★☆  | Consistency Models Survey                | [https://arxiv.org/abs/1902.03305](https://arxiv.org/abs/1902.03305)                                                                                                                                               | 분산 일관성 모델   |
| ★★☆  | Dynamo                                   | [https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)                                                                     | 고가용성 NoSQL  |
| ★☆☆  | Odysseus/DFS                             | [https://arxiv.org/abs/1406.0435](https://arxiv.org/abs/1406.0435)                                                                                                                                                 | DB + DFS 통합 |
| ★☆☆  | CALM Theorem                             | [https://arxiv.org/abs/1901.01930](https://arxiv.org/abs/1901.01930)                                                                                                                                               | 분산 일관성 이론   |
| ★★☆  | Kafka: a Distributed Messaging System for Log Processing | [https://www.semanticscholar.org/paper/Kafka-%3A-a-Distributed-Messaging-System-for-Log-Kreps/ea97f112c165e4da1062c30812a41afca4dab628](https://www.semanticscholar.org/paper/Kafka-%3A-a-Distributed-Messaging-System-for-Log-Kreps/ea97f112c165e4da1062c30812a41afca4dab628). ([notes.stephenholiday.com][1]) | 이벤트 로그 기반 아키텍처, 스트리밍 ETL |

---

# IV. Infra / Distributed Systems

| 우선순위 | 제목                                  | 링크                                                                                                                                                       | 핵심 주제     |
| ---- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| ★★★  | Paxos Made Simple                   | [https://lamport.azurewebsites.net/pubs/paxos-simple.pdf](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf)                                       | 합의        |
| ★★★  | Raft: Understandable Consensus      | [https://raft.github.io/raft.pdf](https://raft.github.io/raft.pdf)                                                                                       | 합의        |
| ★★☆  | Consistent Hashing and Random Trees | [https://people.csail.mit.edu/karger/Papers/web.pdf](https://people.csail.mit.edu/karger/Papers/web.pdf)                                                 | 캐싱/일관 해싱  |
| ★★☆  | ZooKeeper                           | [https://www.usenix.org/legacy/event/usenix10/tech/full_papers/Hunt.pdf](https://www.usenix.org/legacy/event/usenix10/tech/full_papers/Hunt.pdf)         | 코디네이션     |
| ★☆☆  | Web Caching with Consistent Hashing | [https://www.cs.cmu.edu/~srini/15-744/S02/readings/K%2B99.html](https://www.cs.cmu.edu/~srini/15-744/S02/readings/K%2B99.html)                           | 캐싱        |
| ★☆☆  | DHT Communications Survey           | [https://arxiv.org/abs/2109.10787](https://arxiv.org/abs/2109.10787)                                                                                     | DHT       |
| ★★★  | CAP Theorem (Gilbert & Lynch)       | [https://users.ece.cmu.edu/~adrian/731-sp04/readings/Gilbert_Lynch_2002.pdf](https://users.ece.cmu.edu/~adrian/731-sp04/readings/Gilbert_Lynch_2002.pdf) | 분산 한계     |
| ★★☆  | Fallacies of Distributed Computing  | [https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing](https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing)                     | 분산 시스템 오해 |
| ★★☆  | Viewstamped Replication Revisited               | [https://pmg.csail.mit.edu/papers/vr-revisited.pdf](https://pmg.csail.mit.edu/papers/vr-revisited.pdf)                                                                                   | 합의·복제 알고리즘(실무적 가용성) . ([pmg.csail.mit.edu][1])    |
| ★★☆  | Hidden Technical Debt in ML Systems (시스템 관점 보강) | [https://papers.neurips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf](https://papers.neurips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf) | ML/서비스 운영에서의 기술부채와 인프라 영향 . ([NeurIPS Papers][2]) |

[1]: https://pmg.csail.mit.edu/papers/vr-revisited.pdf?utm_source=chatgpt.com "Viewstamped Replication Revisited"
[2]: https://papers.neurips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf?utm_source=chatgpt.com "Hidden Technical Debt in Machine Learning Systems"

---

# V. Network / Protocol

| 우선순위 | 제목                                                   | 링크                                                                                                                                       | 핵심 주제       |
| ---- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| ★★★  | End-to-End Arguments in System Design                | [https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf](https://web.mit.edu/Saltzer/www/publications/endtoend/endtoend.pdf) | E2E 설계      |
| ★★☆  | The Design Philosophy of DARPA Internet Protocols    | [https://www.rfc-editor.org/rfc/rfc1958](https://www.rfc-editor.org/rfc/rfc1958)                                                         | TCP/IP 철학   |
| ★★☆  | TCP Congestion Avoidance and Control (Jacobson 1988) | [https://ee.lbl.gov/papers/congavoid.pdf](https://ee.lbl.gov/papers/congavoid.pdf)                                                       | 혼잡 제어       |
| ★★☆  | SCTP: A New Transport Protocol                       | [https://www.rfc-editor.org/rfc/rfc4960](https://www.rfc-editor.org/rfc/rfc4960)                                                         | 멀티스트림/멀티홈   |
| ★☆☆  | QUIC: Multiplexed Streams over UDP                   | [https://www.rfc-editor.org/rfc/rfc9000](https://www.rfc-editor.org/rfc/rfc9000)                                                         | 현대적 전송 프로토콜 |

---

# VI. Programming Languages / Concurrency

| 우선순위 | 제목                                         | 링크                                                                                                     | 핵심 주제       |
| ---- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------ | ----------- |
| ★★☆  | A Study of Real-World Data Races in Golang | [https://arxiv.org/abs/2204.00764](https://arxiv.org/abs/2204.00764)                                   | Data Race   |
| ★★☆  | Messaging Passing Concurrency in Go        | [https://kar.kent.ac.uk/71491](https://kar.kent.ac.uk/71491)                                           | 메시지 전달      |
| ★★☆  | Comparative Study via Rosetta Code         | [https://arxiv.org/abs/1409.0252](https://arxiv.org/abs/1409.0252)                                     | PL 비교       |
| ★☆☆  | Parsl: Parallel Python                     | [https://arxiv.org/abs/1905.02158](https://arxiv.org/abs/1905.02158)                                   | Python 병렬처리 |
| ★★★  | Communicating Sequential Processes (CSP)   | [https://www.cs.cmu.edu/~crary/654-f07/Hoare78.pdf](https://www.cs.cmu.edu/~crary/654-f07/Hoare78.pdf) | Go 채널 기반    |
| ★★★  | Actor Model (Hewitt 1973)                  | [https://dl.acm.org/doi/10.1145/1624775.1624804](https://dl.acm.org/doi/10.1145/1624775.1624804)       | Actor Model |
| ★★☆  | The Go Memory Model                        | [https://go.dev/ref/mem](https://go.dev/ref/mem)                                                       | Go 메모리 모델   |

---

# SDK 관련

| 우선순위 | 제목                                                                                  | 링크                                                                                                                                                                                                                                                             | 핵심 주제                       |
| ---- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| ★★★  | OpenTelemetry Specification                                                         | [https://opentelemetry.io/docs/specs/](https://opentelemetry.io/docs/specs/)                                                                                                                                                                                   | Trace / Span / Attribute 표준 |
| ★★☆  | EDDOps: Evaluation-Driven Dev & Ops of LLM Agents                                   | [https://arxiv.org/html/2411.13768v3](https://arxiv.org/html/2411.13768v3)                                                                                                                                                                                     | LLM 운영, 평가 기반 관측            |
| ★★☆  | Deterministic Graph-Based Inference for Guardrailing LLMs                           | [https://rainbird.ai/wp-content/uploads/2025/03/Deterministic-Graph-Based-Inference-for-Guardrailing-Large-Language-Models.pdf](https://rainbird.ai/wp-content/uploads/2025/03/Deterministic-Graph-Based-Inference-for-Guardrailing-Large-Language-Models.pdf) | 가드레일 로직 설계                  |
| ★★☆  | Towards Privacy-Preserving Social-Media SDKs (USENIX Security)                      | [https://www.usenix.org/system/files/usenixsecurity24-lu-haoran.pdf](https://www.usenix.org/system/files/usenixsecurity24-lu-haoran.pdf)                                                                                                                       | SDK 설계 시 데이터 최소화            |
| ★☆☆  | APILogGuard: API Logging and Monitoring Framework                                   | [https://www.jetir.org/papers/JETIR2504A31.pdf](https://www.jetir.org/papers/JETIR2504A31.pdf)                                                                                                                                                                 | API 이벤트 수집/모니터링             |
| ★☆☆  | OWASP Top 10 for APIs                                                               | [https://owasp.org/www-project-api-security/](https://owasp.org/www-project-api-security/)                                                                                                                                                                     | API/SDK 보안 기본 원칙            |
