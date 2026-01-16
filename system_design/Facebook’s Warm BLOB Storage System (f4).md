# Facebook’s Warm BLOB Storage System (f4)

## 출처

* **링크**: [https://www.usenix.org/conference/osdi14/technical-sessions/presentation/muralidhar](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/muralidhar) ([USENIX][1])
* **학회**: USENIX OSDI 2014
* **저자**: Subramanian Muralidhar, Wyatt Lloyd, Sabyasachi Roy, Cory Hill 등 ([USENIX][1])

---

## AI 요약

**f4**는 Facebook이 사진/비디오 같은 **BLOB(Binary Large Object)** 데이터를 효율적으로 저장·서비스하기 위해 만든 *워밍 스토리지 계층(System)*이다. 기존 저장소(Haystack)가 **자주 접근되는 ‘hot’ BLOB**에 잘 맞지만, 시간이 지나면서 접근 빈도가 낮아지는 **‘warm’ BLOB**을 처리하기엔 과도한 비용/공간을 쓰고 있었다. 이를 해결하기 위해 f4를 도입했다. ([the morning paper][2])

---

## 문제 배경 (왜 f4가 필요했나)

### ① BLOB 특성

* BLOB: 이미지, 비디오, 문서 같은 **immutable binary 데이터** ([Yumpu][3])
* 생성 후 **수정 없이 여러 번 읽히고, 가끔 삭제됨** ([Yumpu][3])

### ② 기존 시스템 한계 – Haystack

* Haystack은 **hot BLOB 처리 최적화**를 위해 설계됨 ([the morning paper][2])
* 세 번 복제 + RAID  => **효과적 복제 계수(effective replication factor)** 약 **3.6x** ([the morning paper][2])
* 문제: **warm BLOB까지 동일한 복제 + 고성능 설계**로 인해 공간 낭비 큼 ([the morning paper][2])

### ③ 데이터 온도(Temperature)

* 요청 빈도와 객체 나이 사이에 강한 상관관계가 있음
  *신규 BLOB은 많이, 오래된 BLOB은 훨씬 적게 읽힘* ([USENIX][4])

→ 즉, hot vs warm 이 *정량적으로 구분 가능*했고, 이를 스토리지 레벨에서 분리했다.

---

## 핵심 설계: f4 Warm BLOB Storage

### 1) 목적 정의

* **warm BLOB 전용 저장소**를 구축
  → 낮은 요청률, 긴 수명, 여전히 빠른 접근 요구 ([the morning paper][2])

### 2) 낮은 복제 계수

* f4는 **erasure coding 기반 저장**으로 효율 개선

  * Reed-Solomon(10,4) + 광역 환경에선 XOR 코딩 사용 ([the morning paper][2])
    → *복제 계수* 약 **2.8x → 2.1x** 까지 낮춤 ([the morning paper][2])

### 3) 시스템 구조

* BLOB은 **볼륨 단위**로 묶어서 저장
* 각 볼륨은 데이터, 인덱스, 저널 파일 포함 ([The Register][5])
* 인덱스 파일은 메모리 기반 구조를 디스크에 반영한 것임 ([The Register][5])

### 4) 내결함성 보장

* **디스크/호스트/랙/데이터센터 장애까지 대응** 가능한 구조

  * 데이터센터 내: rack/host 장애 대비
  * 데이터센터 간: XOR 코딩 복제 ([The Register][5])

### 5) 온도 기반 계층 이동

* 생성 직후엔 Haystack에 저장
* 시간이 지날수록 요청 감소 → **warm 스토리지(f4)로 이동** ([the morning paper][2])

---

## 평가 및 결과

* **생산 환경 운영 데이터**

  * 논문 발표 당시, f4는 **65PB 이상 논리 데이터** 저장 중 ([the morning paper][2])
* **저장 공간 절약 효과**

  * 저장 공간 53PB 절약 (복제 계수 감소) ([the morning paper][2])
* **성능 영향**

  * 요청 지연 증가폭은 크지 않음 (예: 14ms → 17ms) ([the morning paper][2])
  * 낮은 요청률 대응에 충분한 처리량 제공

---

## 실무적 인사이트

### 온도 기반 계층 분리 전략

* **데이터 접근 패턴 분석**을 기반으로 저장소를 계층화 → 비용/처리량 최적화 가능

### 복제 vs 코드

* **전통 복제(replication)**는 단순하지만 비효율적
* **erasure coding**은 대규모 BLOB 저장에서 공간과 비용 절약 실질적

### trade-offs

* f4는 **cold storage(아카이브)**보다 접근 지연이 짧아야 하기 때문에
  → 빠른 복구/읽기를 포기하지 않음
* 대신, **추가 계산 부담 / 복구 재구성 비용**이 존재

### 의미

* 소셜 플랫폼처럼 **극단적 스케일 + 접근 패턴 분포가 뚜렷**한 경우
  → 계층화된 저장소 아키텍처가 매우 효과적

---

## 키워드 정리

* **Blob**: Binary Large Object (이미지/비디오 같은 불변 바이너리) ([Yumpu][3])
* **Warm storage**: hot보다 요청이 적지만 cold보다 접근 빠른 계층 ([the morning paper][2])
* **Effective replication factor**: 논리 데이터 대비 물리 저장량 비율 ([the morning paper][2])
* **Erasure coding**: 데이터 + 계산된 패리티를 이용해 공간 효율적 내구성 확보 ([the morning paper][2])

---

## 한 줄 요약

> **f4는 Facebook이 BLOB 접근량 감소에 따라 스토리지 구조를 계층화하고, erasure coding을 활용해 저장 비용을 낮춘 warm-tier 저장소 시스템이다.** ([the morning paper][2])
