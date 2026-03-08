# Spark: Cluster Computing with Working Sets

## 출처
- **저자**: Matei Zaharia, Mosharaf Chowdhury, Michael J. Franklin, Scott Shenker, Ion Stoica (UC Berkeley)
- **발표**: 2nd USENIX Workshop on Hot Topics in Cloud Computing (HotCloud), 2010
- **링크**: https://www.usenix.org/legacy/event/hotcloud10/tech/full_papers/Zaharia.pdf

---

## AI 요약

### 문제 제기

논문은 MapReduce/Dryad 계열 시스템이 **비순환 데이터 플로우(acyclic data flow) 모델**에 갇혀 있다는 점을 문제로 삼는다. 저자들은 이 구조가 근본적으로 맞지 않는 두 워크로드를 명시한다.

> *"most of these systems are built around an acyclic data flow model that is not suitable for other popular applications"* — §Abstract

구체적으로:
- **반복 알고리즘(Iterative jobs)**: Logistic Regression, Gradient Descent 같은 ML 알고리즘은 매 iteration마다 같은 데이터를 반복 처리한다. MapReduce는 iteration마다 독립적인 Job으로 실행되므로 **매번 디스크에서 데이터를 다시 읽는다** (§1).
- **인터랙티브 분석(Interactive analysis)**: Pig/Hive 같은 SQL 인터페이스로 동일 데이터셋에 반복 쿼리를 날릴 때, **각 쿼리가 별도의 MapReduce Job으로 실행되어 수십 초의 레이턴시**가 발생한다 (§1).

---

### 핵심 추상화: RDD

논문의 메인 기여는 **Resilient Distributed Dataset (RDD)** 이라는 새 추상화다.

> *"An RDD is a read-only collection of objects partitioned across a set of machines that can be rebuilt if a partition is lost."* — §Abstract

RDD는 네 가지 방법으로 생성된다 (§2.1):
1. HDFS 같은 공유 파일시스템의 파일로부터
2. Driver 프로그램의 Scala 컬렉션을 병렬화(parallelize)해서
3. 기존 RDD에 `flatMap` 같은 transformation을 적용해서
4. 기존 RDD의 persistence를 변경해서 (`cache` 또는 `save`)

중요한 설계 포인트: **RDD는 기본적으로 lazy하고 ephemeral**하다. 파티션은 parallel operation에서 실제로 필요할 때 materialization되며, 사용 후 메모리에서 제거된다. `cache()` 액션을 명시적으로 호출해야만 메모리에 유지된다.

또한 `cache()`는 **hint에 불과**하다:

> *"We note that our cache action is only a hint: if there is not enough memory in the cluster to cache all partitions of a dataset, Spark will recompute them when they are used."* — §2.1

이 설계는 가상 메모리(virtual memory)의 철학과 유사하다고 논문은 설명한다.

---

### Fault Tolerance: Lineage

RDD의 fault tolerance는 데이터 복제가 아닌 **lineage** 로 달성한다.

> *"RDDs achieve fault tolerance through a notion of lineage: if a partition of an RDD is lost, the RDD has enough information about how it was derived from other RDDs to be able to rebuild just that partition."* — §1

구현 레벨에서는, 각 RDD 객체가 **parent를 가리키는 포인터와 변환 정보**를 체인 형태로 유지한다 (§4). 예를 들어:

```
HdfsTextFile → FilteredDataset → CachedDataset → MappedDataset
```

노드 장애 시 유실된 파티션만 lineage를 따라 재계산되며, **다른 노드에서 병렬로 재구성**할 수 있다. DSM(Distributed Shared Memory) 계열 시스템들이 checkpointing으로 fault tolerance를 달성하는 것과 대비된다 (§6).

---

### 공유 변수

RDD 외에 두 가지 제한된 공유 변수 타입을 제공한다 (§2.3):

- **Broadcast variables**: 대용량 read-only 데이터(예: lookup table)를 모든 워커에 한 번만 전송. ALS 실험에서 브로드캐스트 없이는 ratings matrix R을 매 iteration마다 재전송하는 비용이 지배적이었음 (§5).
- **Accumulators**: 워커는 add만 가능, driver만 read 가능. associative operation이 보장되므로 fault-tolerant 구현이 단순해짐.

---

### 구현

Spark는 **Mesos** 위에 구축되었다 (§4). Mesos는 여러 병렬 애플리케이션이 클러스터를 fine-grained하게 공유할 수 있게 해주는 "cluster OS"다. 이를 통해 Spark는 Hadoop, MPI 등 기존 프레임워크와 클러스터를 공유하고 데이터를 주고받을 수 있다.

언어는 **Scala**를 선택했으며, Scala 인터프리터를 수정해 interactive use를 지원한다. 핵심 수정 사항 두 가지 (§4):
1. 인터프리터가 정의하는 클래스를 공유 파일시스템에 출력 → 워커가 custom classloader로 로딩
2. 각 라인의 singleton object가 이전 라인의 singleton을 직접 참조하도록 변경 → 클로저 직렬화 시 현재 상태가 정확히 캡처되도록 보장

---

### 실험 결과

세 가지 실험 (§5, 모두 EC2 환경):

**1. Logistic Regression** (29 GB dataset, 20 × m1.xlarge, 4 cores each)
- Hadoop: iteration당 **127초**
- Spark 첫 번째 iteration: **174초** (Scala overhead로 오히려 느림)
- Spark 이후 iterations: iteration당 **6초** (캐시된 데이터 재사용)
- 최대 **10x 빠름**

노드 크래시 테스트: 10-iteration 실행 중 노드 1대 장애 시 평균 **50초(21%) 지연**. HDFS 블록 크기(128MB)가 커서 블록 수가 노드당 12개뿐이었고 복구 시 코어를 충분히 활용 못 한 것이 원인.

**2. Alternating Least Squares (ALS)** (5000 movies, 15000 users, 30-node EC2)
- Broadcast variable로 ratings matrix R을 캐시 → **2.8x 성능 향상**
- Naive 브로드캐스트(HDFS/NFS)는 노드 수에 비례해 브로드캐스트 시간이 선형 증가 → application-level multicast 구현

**3. Interactive query** (39 GB Wikipedia dump, 15 × m1.xlarge)
- 첫 번째 쿼리: ~35초 (Hadoop과 유사)
- 이후 쿼리: **0.5~1초** (전체 데이터 스캔 포함)

---

### 한계 및 Future Work

논문 자체에서 명시한 한계와 계획 (§7):
1. RDD와 추상화의 특성을 formal하게 정의할 것
2. storage cost와 reconstruction cost를 개발자가 trade-off 할 수 있도록 RDD 추상화 강화
3. **shuffle 연산** 추가 (group-by, join 지원) — 현재 미구현
4. Spark interpreter 위에 SQL, R shell 같은 고수준 인터페이스 제공

---

## 내가 얻은 인사이트

### 1. "Prototype"이라고 명시한 논문이 생태계를 뒤집었다

논문은 §1에서 *"our implementation of Spark is still a prototype"* 이라고 직접 밝힌다. 그럼에도 HotCloud에 제출된 건, 완성된 시스템이 아니라 **추상화 아이디어 자체**가 논문의 기여이기 때문이다. 구현 완성도보다 "이 추상화로 무엇이 가능한가"를 먼저 증명한 전략이다.

아키텍처 결정에서도 마찬가지다. PoC 수준의 구현으로 핵심 가설(인메모리 재사용이 10x 차이를 만든다)을 검증하고, 그게 증명되면 본격적으로 투자하는 방식이 유효하다.

### 2. 제약(read-only)이 곧 fault tolerance의 근거가 된다

RDD가 **immutable**이기 때문에 lineage 추적이 단순해진다. 가변 상태(mutable state)를 허용했다면 DSM처럼 복잡한 일관성 프로토콜이 필요했을 것이다. 논문이 §6에서 Munin 같은 DSM 시스템과 비교하며 이 차이를 명시한다. 분산 서비스에서 상태를 불변으로 만들수록 장애 복구 로직이 단순해진다는 원칙은 Kafka의 append-only log, Event Sourcing 패턴에서도 동일하게 나타난다.

### 3. cache()가 hint라는 설계 결정의 의미

메모리가 부족하면 **자동으로 재계산으로 fallback**한다. "성능 저하는 허용하되, 프로그램이 멈추지는 않는다"는 설계 철학이다. 논문은 이를 가상 메모리에 비유한다. 마이크로서비스에서 캐시를 설계할 때도 같은 원칙 — 캐시 미스가 오류가 아니라 성능 저하로 이어지도록 설계해야 한다.

### 4. 첫 iteration이 Hadoop보다 느렸다 — 숨기지 않은 데이터

Spark의 첫 iteration이 174초로 Hadoop(127초)보다 **느렸다**. 논문은 이를 숨기지 않고 그대로 보고한다. Scala/JVM warm-up overhead가 원인이다. 단일 실행 Job이라면 Hadoop이 더 빠를 수 있다. "항상 Spark가 Hadoop보다 빠르다"는 주장은 틀렸고, **반복 처리 워크로드에 한정된 이야기**다. 기술 선택 시 워크로드 특성을 먼저 정의하는 것이 중요하다는 교훈이다.