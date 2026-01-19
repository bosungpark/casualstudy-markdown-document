# **Don’t Settle for Eventual: Scalable Causal Consistency**

## 출처

* **링크**: “Don’t Settle for Eventual: Scalable Causal Consistency for Wide-Area Storage with COPS”, SOSP’11
* **PDF (온라인 공개)** – SOSP 디지털 라이브러리 및 기타 아카이브에서도 확인 가능 ([Parallel Data Lab][1])

---

## AI 요약

**핵심 문제**
글로벌 분산 저장소(geo-replicated) 시스템은 **높은 가용성, 낮은 지연, 파티션 허용성**을 유지하면서도 **사용자에게 일관된 데이터 뷰**를 제공해야 한다. 전통적으로는 **강한 일관성(strong/linearizability)**이 사용자 혼란을 최소화하지만, 네트워크 파티션이 빈번한 환경에서는 **가용성 희생**을 초래한다 (CAP theorem). **결과적 일관성(eventual)**은 가용성과 확장성은 높지만, 애플리케이션에서는 **사용자 경험의 일관성 부족** 문제가 잦다. ([Parallel Data Lab][1])

**해결책: Causal+ Consistency 모델**
논문은 **인과적 일관성(causal consistency)**을 기반으로 한 **causal+ (causal plus) 일관성** 모델을 제안한다. 이 모델은:

* 인과관계가 있는 작업은 **원인 → 결과 순서**로 보장한다.
* **충돌(conflict) 발생 시 수렴(convergent) 처리**를 보장함으로써, 단순 causal consistency보다 강한 의미를 가진다.
* 동시에 **가용성(availability)**과 **낮은 지연(latency)**을 유지한다. ([cs.yale.edu][2])

**시스템: COPS (Clusters of Order-Preserving Servers)**
COPS는 causal+ consistency를 제공하는 **키-값 저장소**로 설계되었다. 핵심 아이디어는 다음과 같다:

* **메타데이터로 인과적 종속성(dependencies)**를 추적하여, 종속 관계가 충족되었을 때만 쓰기(commit)를 허용한다.
* 각 데이터센터는 전체 키 공간의 복제본(full replication)을 갖고, 모든 로컬 연산은 **락 없이** 처리된다.
* 확장성을 위해 **키별(partition) 병렬 처리**를 활용한다. ([Parallel Data Lab][1])

**get-transaction (COPS-GT)**
논문에서는 단일 키뿐 아니라 **여러 키를 일관된 시점에 읽는 트랜잭션**도 지원한다. 이를 통해 복수 키에 대한 causal snapshot을 보장하며, 이는 **locking이나 blocking 없이** 구현된다. ([Parallel Data Lab][1])

**성능 평가**

* 낮은 지연: 대부분의 get/put 작업이 **1ms 이하** 응답 시간.
* 확장성: 서버 수 증가에도 throughput이 안정적으로 증가.
* COPS와 COPS-GT 간의 성능 차이가 거의 없음. ([Parallel Data Lab][1])

---

## 내가 얻은 인사이트

### ✔ 인과적 일관성이 갖는 실용적 가치

단순 **eventual consistency**는 “언젠가는 일관된 상태”라는 약속만 하고, 클라이언트 경험은 **일관되지 않을 수 있음**. 반면 **causal+**는 애플리케이션 관점에서 **원인과 결과 간 순서 보존**을 보장하므로 SNS, 협업도구 등에서 **자연스러운 사용자 경험**을 제공한다. ([C's Shelter][3])

### ✔ 성능과 일관성의 균형

COPS는 **일관성 강화**를 위해 로그나 전역 순서를 강제하는 대신, **종속성 체크(dependency check)**를 통해 causal+ 일관성을 보장한다. 따라서 **strong consistency 수준은 아니지만**, 실제 애플리케이션에서 충분히 높은 일관성 보장을 하면서도 **확장성과 낮은 지연**을 유지한다. ([cs.yale.edu][2])

### ✔ 실무적 적용 인사이트

* causal+는 eventual consistency보다 **예측 가능하고 직관적인 상태**를 약속하여 복잡한 애플리케이션 로직을 줄여준다.
* global scale replication에서 **lock-free multi-key read**를 지원하는 get transactions가 유용하다.
* 메타데이터를 통한 dependency tracking이라는 **핵심 설계 패턴**은 다른 분산 시스템에도 적용 가능하다. ([mwhittaker.github.io][4])
