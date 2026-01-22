# **Erasure Coding in Windows Azure Storage**

## 출처

* **링크**: [https://www.usenix.org/conference/atc12/technical-sessions/presentation/huang](https://www.usenix.org/conference/atc12/technical-sessions/presentation/huang) ([USENIX][1])
* **PDF(논문)**: [https://www.usenix.org/system/files/conference/atc12/atc12-final181_0.pdf](https://www.usenix.org/system/files/conference/atc12/atc12-final181_0.pdf) ([USENIX][2])

---

## AI 요약

**Windows Azure Storage (WAS)**는 클라우드 규모의 스토리지 시스템으로, 고객 데이터를 무제한으로 저장하고 어디서나 접근 가능하도록 한다. WAS는 **저장 비용**을 절감하고 **데이터 내구성(耐久性)**을 확보하기 위해 **에러 수정 코드(erasure coding)** 를 도입했다. ([USENIX][1])

논문의 핵심 기여는 **Local Reconstruction Codes (LRC)** 라는 **새로운 계열의 코드**를 제안한 점이다. 기존 전통적인 Reed-Solomon 등은 한 데이터 조각이 오프라인 상태일 때 **수많은 조각을 읽어야 하는 높은 비용**이 있었다. LRC는 **읽어야 하는 조각 수를 줄임으로써**,

* **대역폭과 I/O 비용을 크게 줄이고**,
* **낮은 재구성 지연 (reconstruction latency)** 을 유지하면서,
* 여전히 **낮은 저장 오버헤드** (storage overhead) 를 제공한다. ([USENIX][1])

논문은 LRC 코드의 **구조/수학적 성질**, **Azure Storage에서의 실용적 사용법**, 그리고 **성능/운영상의 이점**을 상세히 설명한다. ([USENIX][2])

---

## 왜 에러 코딩을 WAS에 도입했는가

Azure는 원래 데이터를 **세 개 복제(replication)** 하는 방식으로 내구성을 확보했다. 그러나 이 방식은 저장 공간을 **3배**나 차지한다. 예를 들어 EB(엑사바이트) 규모의 데이터가 쌓이면 운영 비용 및 전력/데이터센터 공간 비용이 커진다. ([USENIX][2])

이를 해결하기 위해 WAS는 다음 전략을 채택했다:

1. **활성 영역(active extents)**: 먼저 모든 데이터를 3중 복제 방식으로 빠르게 쓰고,
2. **영구 sealed extents**: 일정 크기(예: 1 GB)로 확정되면,
3. **배경에서 에러 코딩(EC)** 을 수행하고,
4. **원래의 3중 복제본을 삭제**한다. ([USENIX][2])

이런 *lazy erasure coding* 접근은 쓰기 성능에 영향을 최소화하면서도 저장 비용을 절반 이상 줄여준다. ([Phys.org][3])

---

## LRC (Local Reconstruction Codes)의 핵심 설계

### 1) 전통 Reed-Solomon의 문제

전통적인 Reed-Solomon EC에서는 *k* 개의 데이터 블록과 *m* 개의 패리티 블록을 만든다.
하지만 하나의 블록만 사라져도 다수의 블록을 읽어서 재구성해야 한다.
예: *k=12, m=4* 라면 **12개의 블록 전체를 읽어야** 데이터를 되살린다. ([stephenholiday.com][4])

---

### 2) Local Reconstruction Codes (LRC)이 하는 일

LRC는 **global parity + local parity** 를 조합한다.
구조적으로, 블록 그룹을 작은 서브그룹으로 나누고, 각 서브그룹마다 **local parity** 를 둔다.

예시:

* 12개의 데이터 블록을 두 그룹(6+6)으로 나누고,
* 두 그룹 각각에 local parity를 추가,
* 전체에 대해 두 개의 global parity를 생성한다. ([stephenholiday.com][4])

이 구조의 장점은:

✔ **단일 블록 장애(single failure)** 발생 시
→ 해당 그룹의 local parity만 이용하여 **6개 블록만 읽어 재구성 가능**

✔ 전체 redundancy 수준은 유지
→ 여전히 여러 블록 장애(tolerate up to certain multi-failure) 가능 ([stephenholiday.com][4])

이처럼 LRC는 **읽기 비용을 절반 이하로 줄이고**,
부분 장애에서 빠른 재구성이 가능한 코드를 만든다. ([storagemojo.com][5])

---

## WAS에서의 운영/성능 최적화

### 처리되는 상황

1. **데이터 조각 lost 또는 오프라인**
2. **스토리지 노드 “hot” (부하가 많아 응답 느림)**

이 때 WAS는:

* **동적 재구성** (enough fragments 읽어 데이터 조립),
* 또는 **캐시/리플리케이션**을 열심히 활용해 성능을 지킨다. ([USENIX][2])

특히 LRC는 이러한 **degraded read** 상황에서
✔ 네트워크 대역폭
✔ I/O 수
✔ 재구성 지연
모두 기존 코드 대비 **낮춘다는 점**이 핵심이다. ([stephenholiday.com][4])

또한, WAS는 **핫 노드가 생겼을 때 로드 밸런싱/캐싱**을 적극 수행한다. ([USENIX][2])

---

## 비용과 이득

| 항목           | 복제 3개    | LRC 기반 EC            |
| ------------ | -------- | -------------------- |
| 저장 오버헤드      | ×3       | 약 ×1.3~×1.5          |
| 단일 장애 복원 I/O | N blocks | N/2 blocks (typical) |
| 네트워크/대역폭 비용  | 높음       | 낮음                   |
| 재구성 지연       | 느림       | 빠름                   |

이로 인해 전체 저장 비용이 **50% 이상 절감**된다. ([Phys.org][3])

---

## 내가 얻은 인사이트

### ✔ “Lazy”가 실용적이다

WAS는 데이터를 처음에 **3중 복제**로 빠르게 쓰고, 나중에 **배경에서 EC로 전환**한다. 이 전략은

* 쓰기 처리 지연을 줄이고,
* 대규모 데이터센터에서의 *운영 비용*을 동시에 줄인다. ([USENIX][2])

---

### ✔ LRC의 핵심은 *locality*

전통 EC는 **완전 global** 기반이라 장애 시 오버헤드가 크다.
LRC는 **local subgroup parity + global parity** 를 융합해,
**단일 장애 상황에서 로컬 파리티만으로 재구성**할 수 있게 한다. ([stephenholiday.com][4])

---

### ✔ 오류/장애의 현실

클라우드에서는 재부팅, OS 업그레이드 등 *일시적 오프라인*이 계속 발생한다.
이렇게 *짧은 장애*에서도 빠른 복구를 제공하는 것이
단순한 “내구성 = 복원”보다 **고객 SLA 만족에 중요**하다. ([USENIX][2])

---

### ✔ 비용 vs 성능의 합리적 트레이드오프

Triple replication보다 비용을 훨씬 낮추면서도 **대부분의 단일 장애에 대해 빠른 대응**을 할 수 있는 구조는

* 클라우드 서비스 제공자 측에서
* *현실적인 비용/내구성/성능 균형* 을 제공한다는 점이 중요하다. ([Phys.org][3])
