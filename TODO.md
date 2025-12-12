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

| 우선순위 | 제목                                                                                       | 링크                                                                                                                                                                                                                                                                             | 핵심 주제                    |
| ---- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| ★★★  | Google File System (GFS)                                                                 | [https://static.googleusercontent.com/media/research.google.com/ko//archive/gfs-sosp2003.pdf](https://static.googleusercontent.com/media/research.google.com/ko//archive/gfs-sosp2003.pdf)                                                                                     | 분산 파일 시스템                |
| ★★★  | Bigtable: A Distributed Storage System for Structured Data                               | [https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf](https://static.googleusercontent.com/media/research.google.com/en//archive/bigtable-osdi06.pdf)                                                                               | 분산 저장소, SSTable          |
| ★★★  | Spanner                                                                                  | [https://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi14.pdf](https://static.googleusercontent.com/media/research.google.com/en//archive/spanner-osdi14.pdf)                                                                                 | 글로벌 분산 DB                |
| ★★★  | The Log: What Every Engineer Should Know                                                 | [https://www.linkedin.com/pulse/log-what-every-software-engineer-should-know-unifying-abstraction-kreps/](https://www.linkedin.com/pulse/log-what-every-software-engineer-should-know-unifying-abstraction-kreps/)                                                             | 로그 기반 아키텍처               |
| ★★★  | The Log-Structured Merge-Tree (LSM-Tree)                                                 | [https://www.cs.umb.edu/~poneil/lsmtree.pdf](https://www.cs.umb.edu/~poneil/lsmtree.pdf)                                                                                                                                                                                       | LSM Tree, 쓰기 최적화         |
| ★★★  | The Design and Implementation of a Log-Structured File System                            | [https://people.eecs.berkeley.edu/~brewer/cs262/LFS.pdf](https://people.eecs.berkeley.edu/~brewer/cs262/LFS.pdf)                                                                                                                                                               | 로그 구조 스토리지               |
| ★★★  | ARIES: A Transaction Recovery Method                                                     | [https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf](https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf)                                                                                                                                                       | WAL, 복구 알고리즘             |
| ★★★  | Dynamo: Amazon’s Highly Available Key-value Store                                        | [https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)                                                                                                                                 | Eventually Consistent KV |
| ★★★  | Calvin: Deterministic Database Transactions at Scale                                     | [https://dl.acm.org/doi/10.1145/2387880.2387895](https://dl.acm.org/doi/10.1145/2387880.2387895)                                                                                                                                                                               | 결정적 분산 트랜잭션              |
| ★★☆  | Dataflow: A Unified Model for Batch and Stream Processing                                | [https://research.google/pubs/dataflow-a-unified-model-for-batch-and-stream-processing/](https://research.google/pubs/dataflow-a-unified-model-for-batch-and-stream-processing/)                                                                                               | 스트림/배치 처리                |
| ★★☆  | Consistency Models Survey                                                                | [https://arxiv.org/abs/1902.03305](https://arxiv.org/abs/1902.03305)                                                                                                                                                                                                           | 분산 일관성 모델                |
| ★★☆  | Kafka: a Distributed Messaging System for Log Processing                                 | [https://www.semanticscholar.org/paper/Kafka-%3A-a-Distributed-Messaging-System-for-Log-Kreps/ea97f112c165e4da1062c30812a41afca4dab628](https://www.semanticscholar.org/paper/Kafka-%3A-a-Distributed-Messaging-System-for-Log-Kreps/ea97f112c165e4da1062c30812a41afca4dab628) | 이벤트 로그, 스트리밍             |
| ★★☆  | Paxos Made Simple                                                                        | [https://lamport.azurewebsites.net/pubs/paxos-simple.pdf](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf)                                                                                                                                                             | 합의 알고리즘                  |
| ★★☆  | Raft: In Search of an Understandable Consensus Algorithm                                 | [https://raft.github.io/raft.pdf](https://raft.github.io/raft.pdf)                                                                                                                                                                                                             | 실무 합의 알고리즘               |
| ★★☆  | Online, Asynchronous Schema Change in F1                                                 | [https://research.google/pubs/pub41376/](https://research.google/pubs/pub41376/)                                                                                                                                                                                               | 온라인 스키마 변경               |
| ★★☆  | Frangipani: A Scalable Distributed File System                                           | [https://pdos.csail.mit.edu/6.824/papers/thekkath-frangipani.pdf](https://pdos.csail.mit.edu/6.824/papers/thekkath-frangipani.pdf)                                                                                                                                             | 분산 락 + FS                |
| ★★☆  | Time, Clocks, and the Ordering of Events in a Distributed System                         | [https://lamport.azurewebsites.net/pubs/time-clocks.pdf](https://lamport.azurewebsites.net/pubs/time-clocks.pdf)                                                                                                                                                               | Lamport Clock            |
| ★★☆  | Granola: Low-Overhead Distributed Transaction Coordination                               | [https://www.usenix.org/conference/atc12/technical-sessions/presentation/cowling](https://www.usenix.org/conference/atc12/technical-sessions/presentation/cowling)                                                                                                             | 2PC 최적화                  |
| ★★☆  | Tango: Distributed Data Structures over a Shared Log                                     | [https://dl.acm.org/doi/10.1145/2517349.2522735](https://dl.acm.org/doi/10.1145/2517349.2522735)                                                                                                                                                                               | 로그 기반 트랜잭션               |
| ★★☆  | No Compromises: Distributed Transactions with Consistency, Availability, and Performance | [https://dl.acm.org/doi/10.1145/2815400.2815407](https://dl.acm.org/doi/10.1145/2815400.2815407)                                                                                                                                                                               | 트랜잭션 트레이드오프              |
| ★★☆  | Building Consistent Transactions with Inconsistent Replication                           | [https://dl.acm.org/doi/10.1145/2815400.2815417](https://dl.acm.org/doi/10.1145/2815400.2815417)                                                                                                                                                                               | 비일관 복제 트랜잭션              |
| ★☆☆  | Odysseus/DFS                                                                             | [https://arxiv.org/abs/1406.0435](https://arxiv.org/abs/1406.0435)                                                                                                                                                                                                             | DB + DFS 통합              |
| ★☆☆  | CALM Theorem                                                                             | [https://arxiv.org/abs/1901.01930](https://arxiv.org/abs/1901.01930)                                                                                                                                                                                                           | 분산 일관성 이론                |
| ★☆☆  | Bitcask: A Log-Structured Hash Table for Fast Key/Value Data                             | [https://riak.com/assets/bitcask-intro.pdf](https://riak.com/assets/bitcask-intro.pdf)                                                                                                                                                                                         | 로그 기반 KV                 |
| ★☆☆  | Readings in Database Systems (Red Book)                                                  | [http://www.redbook.io](http://www.redbook.io)                                                                                                                                                                                                                                 | DB 고전 논문 모음              |

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
| ★☆☆  | The Problem with Threads (Lee, 2006) | https://www2.eecs.berkeley.edu/Pubs/TechRpts/2006/EECS-2006-1.pdf | 스레드의 근본적 문제, 비결정성 |
| ★★☆  | Communicating Sequential Processes (Hoare, 1978) | https://www.cs.cmu.edu/~crary/819-f09/Hoare78.pdf | CSP 모델, Go/asyncio 영향 |
| ★★☆  | A Note on Distributed Computing (Waldo et al., 1994) | https://scholar.harvard.edu/files/waldo/files/waldo-94.pdf | 로컬 vs 원격 호출의 차이 |
| ★★☆  | Uniprocessor Garbage Collection Techniques (Wilson, 1992) | https://www.cs.rice.edu/~javaplt/311/Readings/wilson92uniprocessor.pdf | GC 기법 총정리 |
| ★☆☆  | pandas: a Foundational Python Library (McKinney, 2010) | https://conference.scipy.org/proceedings/scipy2010/pdfs/mckinney.pdf | DataFrame 설계 철학 |
| ★★☆  | Array Programming with NumPy (Harris et al., 2020) | https://www.nature.com/articles/s41586-020-2649-2 | NumPy 아키텍처, 벡터화 |
| ★★☆  | MapReduce: Simplified Data Processing (Dean & Ghemawat, 2004) | https://research.google/pubs/pub62/ | 분산 처리 패턴 |
| ★★★  | Spark: Cluster Computing with Working Sets (Zaharia, 2010) | https://www.usenix.org/legacy/event/hotcloud10/tech/full_papers/Zaharia.pdf | RDD, PySpark 기반 |
| ★☆☆  | Scikit-learn: Machine Learning in Python (Pedregosa, 2011) | https://jmlr.org/papers/v12/pedregosa11a.html | API 설계, 파이프라인 |
| ★★☆  | Automatic Differentiation in PyTorch (Paszke, 2017) | https://openreview.net/pdf?id=BJJsrmfCZ | Autograd 메커니즘 |
| ★★☆  | TensorFlow: Large-Scale Machine Learning (Abadi, 2016) | https://www.usenix.org/system/files/conference/osdi16/osdi16-abadi.pdf | 연산 그래프, 분산 학습 |
| ★★★  | Attention Is All You Need (Vaswani, 2017) | https://arxiv.org/abs/1706.03762 | Transformer, LLM 기반 |
| ★☆☆  | REST: Architectural Styles (Fielding, 2000) | https://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm | REST 원론 |
| ★★☆  | The C10K Problem (Kegel, 2006) | http://www.kegel.com/c10k.html | 대규모 동시 연결 |
| ★★☆  | PEP 3333 – WSGI Specification | https://peps.python.org/pep-3333/ | Python 웹 표준 |
| ★★☆  | QuickCheck: Random Testing (Claessen & Hughes, 2000) | https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf | Property-based testing |
| ★★☆  | Twelve-Factor App (Wiggins, 2011) | https://12factor.net/ | 클라우드 네이티브 원칙 |
| ★★☆  | Dynamo: Amazon's Key-value Store (DeCandia, 2007) | https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf | 분산 DB, eventual consistency |
| ★★★  | Borg, Omega, and Kubernetes (Burns, 2016) | https://queue.acm.org/detail.cfm?id=2898444 | 컨테이너 오케스트레이션 |
| ★★☆  | PEP 484 – Type Hints | https://peps.python.org/pep-0484/ | Python 타입 힌트 표준 |
| ★★☆  | Gradual Typing for Functional Languages (Siek, 2006) | http://scheme2006.cs.uchicago.edu/13-siek.pdf | 점진적 타이핑 이론 |
| ★★☆  | Smashing the Stack for Fun and Profit (Aleph One, 1996) | http://phrack.org/issues/49/14.html | 버퍼 오버플로우 기초 |
| ★★☆  | OWASP Top 10 | https://owasp.org/www-project-top-ten/ | 웹 보안 취약점 |
| ★★★  | Numba: A LLVM-based Python JIT Compiler (Lam, 2015) | https://dl.acm.org/doi/10.1145/2833157.2833162 | JIT 컴파일 |

---

# SDK 관련

| 우선순위 | 제목                                                                                  | 링크                                                                                                                                                                                                                                                             | 핵심 주제                       |
| ---- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| ★★★  | OpenTelemetry Specification                                                         | [https://opentelemetry.io/docs/specs/](https://opentelemetry.io/docs/specs/)                                                                                                                                                                                   | Trace / Span / Attribute 표준 |
| ★★☆  | EDDOps: Evaluation-Driven Dev & Ops of LLM Agents                                   | [https://arxiv.org/html/2411.13768v3](https://arxiv.org/html/2411.13768v3)                                                                                                                                                                                     | LLM 운영, 평가 기반 관측            |
| ★★☆  | Deterministic Graph-Based Inference for Guardrailing LLMs                           | [https://rainbird.ai/wp-content/uploads/2025/03/Deterministic-Graph-Based-Inference-for-Guardrailing-Large-Language-Models.pdf](https://rainbird.ai/wp-content/uploads/2025/03/Deterministic-Graph-Based-Inference-for-Guardrailing-Large-Language-Models.pdf) | 가드레일 로직 설계                  |
| ★☆☆  | APILogGuard: API Logging and Monitoring Framework                                   | [https://www.jetir.org/papers/JETIR2504A31.pdf](https://www.jetir.org/papers/JETIR2504A31.pdf)                                                                                                                                                                 | API 이벤트 수집/모니터링             |
| ★☆☆  | OWASP Top 10 for APIs                                                               | [https://owasp.org/www-project-api-security/](https://owasp.org/www-project-api-security/)                                                                                                                                                                     | API/SDK 보안 기본 원칙            |
