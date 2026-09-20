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

---

# X. 인프라 실무 / 운영 / 트러블슈팅 (실무 스터디)

## X-1. 리눅스 / OS / 시스템 기초

| 제목                                                          | 핵심 주제                          |
| ----------------------------------------------------------- | ------------------------------ |
| 리눅스의 inode는 무엇이며, 거기에 저장되지 않는 정보는 무엇인지        | inode 구조, 메타데이터 범위           |
| inode full 발생 시 대처방법                                     | inode 고갈 진단·복구                 |
| 스토리지 사용률은 낮은데 no space left on device 오류 원인          | inode 고갈 / 삭제된 열린 파일 / 예약 블록 |
| 키보드에 A를 누르면 화면에 A가 찍히는 과정                          | 입력 → 인터럽트 → 커널 → 디스플레이 경로  |
| linux single mode 진입 방법 및 사용 가능한 명령어 정리              | 부팅 단계, 복구 모드 명령어            |
| kernel panic 원인 및 대처 방안                                  | 패닉 트리거, 분석·복구                |
| 정규 표현식에 대한 기본적인 이해                                  | regex 문법, grep/sed/awk 활용     |
| 시스템 리소스 상세 파악 (top, free -h, df, du, cpuinfo)          | 메트릭 상세 해석                     |
| 각 OS·버전별 default log 위치 파악 및 추출 (awk/grep)            | 로그 경로, 시간대·문자열 추출         |
| APP 로그 분석 (package 방식 / 특정 solution별 위치·형식)          | 애플리케이션 로그 위치·포맷 분석       |

## X-2. 네트워크 / DNS / 프로토콜

| 제목                                                          | 핵심 주제                          |
| ----------------------------------------------------------- | ------------------------------ |
| DNS가 udp/53이 아닌 tcp/53을 쓰는 이유 (resolv.conf, 인증서 갱신) | DNS 전송 계층, 동작 방식            |
| DNS 계층구조와 각 record(A, CNAME, PTR, SOA 등) 이해           | DNS 레코드 타입, 위임 구조          |
| CoreDNS가 클러스터 내부 DNS를 처리하는 방식                       | CoreDNS, 서비스 디스커버리          |
| IPSec / SSL VPN 방식 주요 차이점 (암호화·운영 방식)               | VPN 아키텍처 비교                  |
| SSL 인증서 동작 방식, 적용 방식                                  | TLS 핸드셰이크, 인증서 체인          |
| L4 / L7 로드밸런서 차이점과 적합한 케이스                         | LB 계층별 동작·선택 기준           |
| MTU 설정이 잘못됐을 때 증상과 확인 방법                          | MTU/MSS, 단편화 진단              |
| NAT / PAT 차이점과 클라우드 환경에서의 동작 방식                  | 주소 변환, 클라우드 게이트웨이        |
| VLAN과 서브넷의 차이점, 함께 쓰는 이유                          | L2 분리 vs L3 분리               |
| tcpdump 등을 이용한 data 흐름 파악                              | 패킷 캡처·분석                     |
| 웹서버 접속 불가 트러블슈팅 순서 + 재발 방지 쉘 스크립트 작성       | 계층별 진단, 자동화 스크립트         |

## X-3. 컨테이너 / 쿠버네티스 / 가상화

| 제목                                                          | 핵심 주제                          |
| ----------------------------------------------------------- | ------------------------------ |
| 컨테이너 런타임 내부 구조: CLI 한 줄이 Linux Kernel까지 닿는 과정   | runtime, namespace/cgroup (✅ Inside Docker) |
| docker, podman, containerd 차이점                             | 컨테이너 런타임 비교               |
| DockerFile의 동작 및 가상화 환경 실행                           | 이미지 빌드, 레이어 캐시            |
| 하이퍼바이저 type1/2와 XEN, KVM 상세 비교                       | 가상화 아키텍처 비교               |
| cpu/mem/disk 가상화 이해 (GVA>GPA>HPA, vCPU/pCPU 매핑)         | 메모리 변환, 자원 제어 설정         |
| 메모리·CPU 사용량 max가 실제 host와 다른 상황                    | 게스트/호스트 메트릭 괴리           |
| 쿠버네티스 환경에서 PVC가 pending 상태일 때 확인할 부분           | PVC/PV 바인딩, StorageClass     |
| NetworkPolicy 동작 원리와 Pod 간 트래픽 제어 방법                | CNI, 네트워크 정책               |
| Ingress와 Service 차이점, Ingress Controller 동작 방식          | k8s 트래픽 노출 계층             |
| GitHub Actions Runner Controller (ARC)                       | 셀프호스티드 러너 오토스케일       |
| XCP-NG 기본 컴포넌트와 아키텍처                                 | XCP-NG / Xen 기반 가상화        |

## X-4. 클라우드 / 아키텍처 / 메시징

| 제목                                                          | 핵심 주제                          |
| ----------------------------------------------------------- | ------------------------------ |
| AWS 이용 B2C 웹사이트 설계 (VM기반 / Container기반)             | 비용·HA·CICD·모니터링·로깅·보안   |
| AWS 테스트 계정 내 VPC 3-tier 구축 (ACM,EC2,SG,ASG,L7 LB,S3)   | 3-tier 아키텍처 실습             |
| public cloud 선택 시 고려사항과 검증 방법                       | 클라우드 선정 기준               |
| HCI, public cloud, private cloud 차이점                       | 인프라 모델 비교                 |
| 온프레미스 → 퍼블릭 클라우드 마이그레이션 시 네트워크 설계         | 하이브리드 연결, 주소 설계        |
| rabbitmq, kafka, redis 비교                                   | 메시징·스트리밍·캐시 비교         |

## X-5. 스토리지 / 디스크 운영

| 제목                                                          | 핵심 주제                          |
| ----------------------------------------------------------- | ------------------------------ |
| 오브젝트 / 블록 / 파일 스토리지 차이점과 사용 케이스              | 스토리지 유형 선택               |
| 운영 중 서버 디스크가 100% 찼을 때 점검 순서                     | 디스크 풀 진단 절차             |
| 스토리지 서버에 마운트된 디스크가 접근되지 않을 때 조치           | 마운트 장애 복구               |
| 스토리지 장애 발생 시 데이터 무결성 검증 방법                    | 체크섬, 정합성 검사            |

---

# XI. Operating Systems (OS 기초 → 커널 내부)

> **커리큘럼 원칙**: 주교재는 무료 공개된 **OSTEP (Operating Systems: Three Easy Pieces)**. 세 덩어리(가상화 → 동시성 → 영속성) 순서를 그대로 따라가고, 각 단계 끝에서 Linux 실물 문서/커널 문서로 "교과서 개념 ↔ 실제 구현"을 대조한다. 한 문서에 한 챕터만 정리한다.
>
> **권장 순서**: XI-1 → XI-2 → XI-3 → XI-4 → XI-5 → XI-6

## XI-1. 1단계: CPU 가상화 (프로세스 / 스케줄링) — 가장 쉬운 진입점

| 우선순위 | 제목                                              | 링크                                                                                                   | 핵심 주제                        |
| ---- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ---------------------------- |
| ★★★  | OSTEP Ch.6 Mechanism: Limited Direct Execution  | [cpu-mechanisms.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-mechanisms.pdf)                       | 유저/커널 모드, 트랩, 컨텍스트 스위치       |
| ★★★  | OSTEP Ch.7 Scheduling: Introduction             | [cpu-sched.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-sched.pdf)                                 | FIFO/SJF/STCF, turnaround vs response |
| ★★☆  | OSTEP Ch.8 Multi-Level Feedback Queue           | [cpu-sched-mlfq.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-sched-mlfq.pdf)                       | MLFQ, 우선순위 부스팅, 게이밍 방지       |
| ★★☆  | OSTEP Ch.9 Proportional Share (Lottery/Stride)  | [cpu-sched-lottery.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-sched-lottery.pdf)                 | 비례 지분 스케줄링, CFS의 뿌리          |
| ★★☆  | OSTEP Ch.10 Multiprocessor Scheduling           | [cpu-sched-multi.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-sched-multi.pdf)                     | 캐시 어피니티, 로드 밸런싱             |
| ★★★  | Linux CFS Scheduler Design                      | [sched-design-CFS](https://docs.kernel.org/scheduler/sched-design-CFS.html)                           | vruntime, 레드블랙 트리 (교과서 ↔ 실물) |
| ★★☆  | Linux EEVDF Scheduler                           | [sched-eevdf](https://docs.kernel.org/scheduler/sched-eevdf.html)                                     | 6.6부터 CFS를 대체한 최신 스케줄러       |

## XI-2. 2단계: 메모리 가상화 (주소 공간 / 페이징)

| 우선순위 | 제목                                          | 링크                                                                                                   | 핵심 주제                    |
| ---- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------ |
| ★★★  | OSTEP Ch.13 The Abstraction: Address Spaces | [vm-intro.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-intro.pdf)                                   | 주소 공간, 가상 주소의 의미         |
| ★★☆  | OSTEP Ch.14 Interlude: Memory API           | [vm-api.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-api.pdf)                                       | malloc/free, 흔한 메모리 버그   |
| ★★★  | OSTEP Ch.15 Mechanism: Address Translation  | [vm-mechanism.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-mechanism.pdf)                           | 하드웨어 기반 주소 변환, base/bound |
| ★★☆  | OSTEP Ch.16 Segmentation                    | [vm-segmentation.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-segmentation.pdf)                     | 세그멘테이션, 외부 단편화           |
| ★★☆  | OSTEP Ch.17 Free-Space Management           | [vm-freespace.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-freespace.pdf)                           | 할당기 내부, 단편화 전략           |
| ★★★  | OSTEP Ch.18 Paging: Introduction            | [vm-paging.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-paging.pdf)                                 | 페이지 테이블, PTE 구조          |
| ★★★  | OSTEP Ch.19 Paging: Faster Translations(TLB)| [vm-tlbs.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-tlbs.pdf)                                     | TLB 히트/미스, 공간 지역성        |
| ★★☆  | OSTEP Ch.20 Paging: Smaller Tables          | [vm-smalltables.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-smalltables.pdf)                       | 멀티레벨 페이지 테이블            |
| ★★★  | OSTEP Ch.21-22 Swapping & Policies          | [vm-beyondphys.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/vm-beyondphys.pdf)                         | 스왑, LRU/클럭, 스래싱          |
| ★★☆  | What Every Programmer Should Know About Memory | [cpumemory.pdf](https://people.freebsd.org/~lstewart/articles/cpumemory.pdf)                       | 캐시 계층, NUMA (Drepper 고전)  |
| ★☆☆  | Understanding the Linux Virtual Memory Manager | [understand.pdf](https://www.kernel.org/doc/gorman/pdf/understand.pdf)                             | Linux VM 실제 구현 (Gorman)   |

## XI-3. 3단계: 동시성 (스레드 / 락 / 조건변수)

| 우선순위 | 제목                                               | 링크                                                                                                   | 핵심 주제                     |
| ---- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------- | ------------------------- |
| ★★★  | OSTEP Ch.26 Concurrency: An Introduction         | [threads-intro.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-intro.pdf)                         | 스레드, 경쟁 조건, 임계 영역         |
| ★★☆  | OSTEP Ch.27 Interlude: Thread API                | [threads-api.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-api.pdf)                             | pthread 생성/조인/락 API       |
| ★★★  | OSTEP Ch.28 Locks                                | [threads-locks.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-locks.pdf)                         | 스핀락, test-and-set, 공정성    |
| ★★☆  | OSTEP Ch.29 Lock-based Concurrent Data Structures| [threads-locks-usage.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-locks-usage.pdf)             | 동시성 자료구조, 락 세분화           |
| ★★★  | OSTEP Ch.30 Condition Variables                  | [threads-cv.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-cv.pdf)                               | 생산자-소비자, wait/signal 규칙   |
| ★★☆  | OSTEP Ch.31 Semaphores                           | [threads-sema.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-sema.pdf)                           | 세마포어, reader-writer 락     |
| ★★★  | OSTEP Ch.32 Common Concurrency Problems          | [threads-bugs.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-bugs.pdf)                           | 데드락 4조건, atomicity 버그     |
| ★★☆  | OSTEP Ch.33 Event-based Concurrency              | [threads-events.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/threads-events.pdf)                       | 이벤트 루프, select/epoll 모델   |
| ★★☆  | Futexes Are Tricky                               | [futex.pdf](https://www.akkadia.org/drepper/futex.pdf)                                                | Linux 락의 실제 구현 (Drepper)  |

## XI-4. 4단계: 영속성 (I/O / 파일시스템)

| 우선순위 | 제목                                              | 링크                                                                                                   | 핵심 주제                   |
| ---- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------- |
| ★★★  | OSTEP Ch.36 I/O Devices                         | [file-devices.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/file-devices.pdf)                           | 폴링 vs 인터럽트, DMA, 디바이스 드라이버 |
| ★★☆  | OSTEP Ch.37 Hard Disk Drives                    | [file-disks.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/file-disks.pdf)                               | 탐색/회전 지연, 디스크 스케줄링      |
| ★★☆  | OSTEP Ch.38 RAID                                | [file-raid.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/file-raid.pdf)                                 | RAID 레벨별 성능·신뢰성 트레이드오프  |
| ★★★  | OSTEP Ch.39 Interlude: Files and Directories    | [file-intro.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/file-intro.pdf)                               | inode, 하드/심볼릭 링크, fsync |
| ★★★  | OSTEP Ch.40 File System Implementation          | [file-implementation.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/file-implementation.pdf)             | vsfs, 슈퍼블록/비트맵/inode 테이블 |
| ★★☆  | OSTEP Ch.41 Locality and The Fast File System   | [file-ffs.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/file-ffs.pdf)                                   | 실린더 그룹, 디스크 지역성         |
| ★★★  | OSTEP Ch.42 Crash Consistency: FSCK & Journaling| [file-journaling.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/file-journaling.pdf)                     | 저널링, WAL, ordered mode   |
| ★★☆  | OSTEP Ch.43 Log-structured File System          | [file-lfs.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/file-lfs.pdf)                                   | LFS, 세그먼트 클리닝 (LSM의 조상) |
| ★★☆  | OSTEP Ch.44 Flash-based SSDs                    | [file-ssd.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/file-ssd.pdf)                                   | FTL, 웨어 레벨링, 쓰기 증폭      |
| ★☆☆  | OSTEP Ch.45 Data Integrity and Protection       | [file-integrity.pdf](https://pages.cs.wisc.edu/~remzi/OSTEP/file-integrity.pdf)                       | 체크섬, silent corruption   |

## XI-5. 5단계: 커널 실물 / 시스템 콜 경계

| 우선순위 | 제목                                  | 링크                                                                                                   | 핵심 주제                        |
| ---- | ----------------------------------- | ---------------------------------------------------------------------------------------------------- | ---------------------------- |
| ★★★  | The UNIX Time-Sharing System        | [unix.pdf](https://dsf.berkeley.edu/cs262/unix.pdf)                                                   | Ritchie & Thompson 원전, UNIX 설계 철학 |
| ★★★  | xv6: a simple, Unix-like OS (book)  | [book-riscv-rev4.pdf](https://pdos.csail.mit.edu/6.828/2024/xv6/book-riscv-rev4.pdf)                  | 실제로 읽히는 6천 줄짜리 커널 전체         |
| ★★☆  | xv6 source code                     | [mit-pdos/xv6-public](https://github.com/mit-pdos/xv6-public)                                         | OSTEP 예제의 원본 코드 읽기           |
| ★★☆  | syscalls(2) — Linux 시스템 콜 목록        | [syscalls.2](https://man7.org/linux/man-pages/man2/syscalls.2.html)                                   | 유저-커널 경계에 실제로 뭐가 있는지         |
| ★★☆  | The Linux Kernel Documentation      | [docs.kernel.org](https://docs.kernel.org/)                                                           | 커널 서브시스템 공식 문서 진입점           |

## XI-6. 6단계: 인프라 실무와 연결 (컨테이너 = OS 기능의 조합)

| 우선순위 | 제목                        | 링크                                                                                       | 핵심 주제                          |
| ---- | ------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------ |
| ★★★  | namespaces(7)             | [namespaces.7](https://man7.org/linux/man-pages/man7/namespaces.7.html)                   | PID/NET/MNT 네임스페이스 = 컨테이너 격리 |
| ★★★  | Control Group v2          | [cgroup-v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)                            | CPU/메모리 제한, OOM, 파드 리소스의 실체  |
| ★★☆  | BPF Documentation         | [docs.kernel.org/bpf](https://docs.kernel.org/bpf/index.html)                              | eBPF 기반 커널 관측·네트워킹           |
| ★★☆  | capabilities(7)           | [capabilities.7](https://man7.org/linux/man-pages/man7/capabilities.7.html)                | root 권한 분해, 컨테이너 보안 설정       |
